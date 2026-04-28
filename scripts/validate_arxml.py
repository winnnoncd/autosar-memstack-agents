#!/usr/bin/env python3
"""
validate_arxml.py — Pre-validate ARXML files before DaVinci import.

Catches common issues that would cause DVP import failures:
  - XML syntax errors
  - Duplicate SHORT-NAMEs in same parent
  - Missing DEST attributes on DEFINITION-REFs
  - Non-absolute VALUE-REF paths
  - Invalid numerical values

Usage:
    python scripts/validate_arxml.py <file.arxml> [file2.arxml ...]

Exit codes:
    0 — all files valid
    1 — validation errors found
"""

import sys
from pathlib import Path

try:
    from lxml import etree
except ImportError:
    print("ERROR: lxml not installed. Run: pip install lxml", file=sys.stderr)
    sys.exit(2)


NS = "http://autosar.org/schema/r4.0"


def validate_arxml(filepath: str) -> list[str]:
    """Validate a single ARXML file. Returns list of error messages."""
    errors = []
    path = Path(filepath)

    if not path.exists():
        return [f"File not found: {filepath}"]

    # 1. Parse XML
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as e:
        return [f"XML syntax error: {e}"]

    root = tree.getroot()

    # 2. Check no duplicate SHORT-NAMEs among sibling elements
    # In AUTOSAR, SHORT-NAME uniqueness is required among children of the same parent container
    for parent in root.iter():
        names = []
        for child in parent:
            # Look for SHORT-NAME as a grandchild (child of each sibling element)
            for grandchild in child:
                tag = grandchild.tag
                if tag == f"{{{NS}}}SHORT-NAME" or tag == "SHORT-NAME":
                    if grandchild.text:
                        names.append(grandchild.text)
                    break  # Only first SHORT-NAME per element
        seen = set()
        for name in names:
            if name in seen:
                errors.append(f"Duplicate SHORT-NAME '{name}'")
            seen.add(name)

    # 3. Check DEFINITION-REFs have DEST attribute
    for defref in root.iter(f"{{{NS}}}DEFINITION-REF"):
        if "DEST" not in defref.attrib:
            errors.append(f"DEFINITION-REF missing DEST attribute: {defref.text}")

    # 4. Check VALUE-REFs are absolute paths
    for valref in root.iter(f"{{{NS}}}VALUE-REF"):
        path_text = (valref.text or "").strip()
        if path_text and not path_text.startswith("/"):
            errors.append(f"VALUE-REF not absolute path: {path_text}")

    # 5. Check numerical values are valid
    for value_elem in root.iter(f"{{{NS}}}VALUE"):
        parent_tag = value_elem.getparent().tag if value_elem.getparent() is not None else ""
        if "NUMERICAL" in parent_tag or "BOOLEAN" in parent_tag:
            text = (value_elem.text or "").strip()
            if text and not _is_valid_numerical(text):
                errors.append(f"Invalid numerical value: '{text}'")

    return errors


def _is_valid_numerical(text: str) -> bool:
    """Check if value is a valid integer, float, hex, or boolean."""
    if text.lower() in ("true", "false", "0", "1"):
        return True
    try:
        if text.startswith("0x") or text.startswith("0X"):
            int(text, 16)
        else:
            float(text)
        return True
    except ValueError:
        return False


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file.arxml> [file2.arxml ...]", file=sys.stderr)
        sys.exit(2)

    all_valid = True

    for filepath in sys.argv[1:]:
        errors = validate_arxml(filepath)
        if errors:
            all_valid = False
            print(f"FAIL: {filepath}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"OK: {filepath}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
