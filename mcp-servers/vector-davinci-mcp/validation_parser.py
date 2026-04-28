"""
DaVinci Validation Report Parser
==================================
Parses DVP validation reports (XML and HTML formats) into structured
ValidationError objects for the fixer agent.

DVP generates validation reports in two formats:
  - XML: structured, preferred (--report <path>.xml)
  - HTML: visual, fallback (--report <path>.html)

The XML schema is not officially documented by Vector, so this parser
handles known patterns and degrades gracefully on unknown structures.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List
from html.parser import HTMLParser


@dataclass
class ValidationError:
    """Structured validation error from DaVinci report."""
    module: str = ""
    rule_id: str = ""
    severity: str = ""
    message: str = ""
    param_path: str = ""
    fix_hint: str = ""
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# XML Report Parser
# ---------------------------------------------------------------------------

def parse_validation_report_xml(report_path: str) -> List[ValidationError]:
    """
    Parse DVP validation report in XML format.

    Handles multiple known XML structures from different DVP versions.
    Falls back to text extraction if structure is unrecognized.
    """
    errors = []
    path = Path(report_path)

    if not path.exists():
        return errors

    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
    except ET.ParseError:
        # Malformed XML — try line-by-line text extraction
        return _parse_report_text_fallback(path.read_text(encoding="utf-8", errors="replace"))

    # Strategy 1: Look for <ValidationEntry> elements (MICROSAR Gen 6+)
    for entry in root.iter():
        tag = _strip_ns(entry.tag)
        if tag in ("ValidationEntry", "Entry", "Result", "Issue"):
            error = _parse_xml_entry(entry)
            if error:
                errors.append(error)

    # Strategy 2: If no entries found, try table-like structure
    if not errors:
        for row in root.iter():
            tag = _strip_ns(row.tag)
            if tag in ("Row", "tr", "record"):
                error = _parse_xml_row(row)
                if error:
                    errors.append(error)

    # Strategy 3: Fallback to full text extraction
    if not errors:
        all_text = ET.tostring(root, encoding="unicode", method="text")
        errors = _parse_report_text_fallback(all_text)

    return errors


def _strip_ns(tag: str) -> str:
    """Remove XML namespace prefix from tag name."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_xml_entry(entry: ET.Element) -> ValidationError | None:
    """Parse a single <ValidationEntry>-style element."""
    def find_text(names: List[str]) -> str:
        for name in names:
            # Search both with and without namespace
            for child in entry:
                if _strip_ns(child.tag) == name:
                    return (child.text or "").strip()
            # Direct findtext
            result = entry.findtext(name, "")
            if result:
                return result.strip()
        return ""

    module = find_text(["Module", "ModuleName", "Component", "Source"])
    severity = find_text(["Severity", "Level", "Type", "Kind"])
    message = find_text(["Message", "Description", "Text", "Detail"])
    rule_id = find_text(["RuleId", "Rule", "ErrorCode", "Code", "Id"])
    param_path = find_text(["ParameterPath", "Path", "Parameter", "Location"])
    fix_hint = find_text(["FixSuggestion", "Hint", "Fix", "Resolution", "Suggestion"])

    if not message and not rule_id:
        return None

    # Normalize severity
    severity = _normalize_severity(severity)

    return ValidationError(
        module=module,
        rule_id=rule_id,
        severity=severity,
        message=message,
        param_path=param_path,
        fix_hint=fix_hint,
    )


def _parse_xml_row(row: ET.Element) -> ValidationError | None:
    """Parse a table row element (some DVP versions use table layout)."""
    cells = [child for child in row if _strip_ns(child.tag) in ("Cell", "td", "field")]
    if len(cells) < 3:
        return None

    texts = [(c.text or "").strip() for c in cells]

    # Heuristic: first cell = severity or module, second = message
    severity = ""
    module = ""
    message = ""

    for t in texts:
        if t.upper() in ("ERROR", "WARNING", "INFO"):
            severity = t.upper()
        elif not module and len(t) < 30:
            module = t
        elif not message:
            message = t

    if not message:
        return None

    return ValidationError(
        module=module,
        severity=severity or "WARNING",
        message=message,
    )


# ---------------------------------------------------------------------------
# HTML Report Parser
# ---------------------------------------------------------------------------

class _DVPHTMLParser(HTMLParser):
    """Simple HTML parser to extract validation entries from DVP HTML reports."""

    def __init__(self):
        super().__init__()
        self.errors: List[ValidationError] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_row: List[str] = []
        self._current_cell_text = ""
        self._header_row = True

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._current_row = []
        elif tag in ("td", "th") and self._in_row:
            self._in_cell = True
            self._current_cell_text = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            self._current_row.append(self._current_cell_text.strip())
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if self._header_row:
                self._header_row = False
            elif len(self._current_row) >= 3:
                self._process_row(self._current_row)
        elif tag == "table":
            self._in_table = False
            self._header_row = True

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell_text += data

    def _process_row(self, row: List[str]):
        """Convert an HTML table row into a ValidationError."""
        # Common DVP HTML layouts:
        # [Severity, Module, RuleId, Message, Path] or
        # [Module, Severity, Message] or
        # [RuleId, Severity, Module, Message, Hint]

        severity = ""
        module = ""
        rule_id = ""
        message = ""
        param_path = ""

        for cell in row:
            upper = cell.upper()
            if upper in ("ERROR", "WARNING", "INFO") and not severity:
                severity = upper
            elif re.match(r"ECUC_\w+_\d+", cell) and not rule_id:
                rule_id = cell
            elif len(cell) < 20 and not module and upper not in ("ERROR", "WARNING", "INFO"):
                module = cell
            elif len(cell) > 20 and not message:
                message = cell
            elif "/" in cell and not param_path:
                param_path = cell

        if message:
            self.errors.append(ValidationError(
                module=module,
                rule_id=rule_id,
                severity=severity or "WARNING",
                message=message,
                param_path=param_path,
            ))


def parse_validation_report_html(report_path: str) -> List[ValidationError]:
    """Parse DVP validation report in HTML format."""
    path = Path(report_path)
    if not path.exists():
        return []

    html_content = path.read_text(encoding="utf-8", errors="replace")
    parser = _DVPHTMLParser()
    parser.feed(html_content)
    return parser.errors


# ---------------------------------------------------------------------------
# Text Fallback Parser
# ---------------------------------------------------------------------------

# Regex patterns for common DVP error output formats
_PATTERNS = [
    # ECUC_NvM_00123 [ERROR] Module: NvM - message text
    re.compile(
        r"(?P<rule>ECUC_\w+_\d+)\s*\[(?P<severity>\w+)\]\s*"
        r"(?:Module:\s*(?P<module>\w+)\s*-\s*)?(?P<message>.+)"
    ),
    # [ERROR] [NvM] message text
    re.compile(
        r"\[(?P<severity>ERROR|WARNING|INFO)\]\s*"
        r"\[(?P<module>\w+)\]\s*(?P<message>.+)"
    ),
    # ERROR: NvM: message text
    re.compile(
        r"(?P<severity>ERROR|WARNING|INFO):\s*"
        r"(?:(?P<module>\w+):\s*)?(?P<message>.+)"
    ),
]


def _parse_report_text_fallback(text: str) -> List[ValidationError]:
    """Parse validation errors from unstructured text output."""
    errors = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        for pattern in _PATTERNS:
            m = pattern.match(line)
            if m:
                groups = m.groupdict()
                errors.append(ValidationError(
                    module=groups.get("module", ""),
                    rule_id=groups.get("rule", ""),
                    severity=_normalize_severity(groups.get("severity", "")),
                    message=groups.get("message", line),
                ))
                break

    return errors


def _normalize_severity(severity: str) -> str:
    """Normalize severity string to ERROR/WARNING/INFO."""
    s = severity.upper().strip()
    if s in ("ERROR", "ERR", "CRITICAL", "FATAL"):
        return "ERROR"
    elif s in ("WARNING", "WARN", "CAUTION"):
        return "WARNING"
    elif s in ("INFO", "INFORMATION", "NOTE", "HINT"):
        return "INFO"
    return s or "WARNING"
