"""
DaVinci Configurator CLI Wrapper
=================================
Wraps DaVinciCFG.exe command-line interface for headless operation.

Supported operations:
  - open_project:  Load a .dpa project
  - import_arxml:  Import ARXML configuration fragments
  - validate:      Run validation engine, parse report
  - generate:      Trigger BSW/RTE code generation
  - export_arxml:  Export project configuration as ARXML
"""

import os
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from validation_parser import parse_validation_report_xml, parse_validation_report_html


@dataclass
class ValidationError:
    """Structured validation error from DaVinci report."""
    module: str = ""
    rule_id: str = ""
    severity: str = ""        # ERROR, WARNING, INFO
    message: str = ""
    param_path: str = ""      # AUTOSAR parameter path (if available)
    fix_hint: str = ""        # DVP's suggested fix (if available)
    category: str = ""        # AUTO_FIX, PARAM_ADJUST, MISSING_REF, STRUCTURAL, ESCALATE

    def to_dict(self) -> dict:
        return asdict(self)


class DaVinciCLIError(Exception):
    """Raised when DVP CLI returns an unexpected error."""
    def __init__(self, message: str, returncode: int = -1, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class DaVinciCLI:
    """Interface to DaVinci Configurator Classic command-line."""

    # Timeouts in seconds
    OPEN_TIMEOUT = 60
    IMPORT_TIMEOUT = 120
    VALIDATE_TIMEOUT = 180
    GENERATE_TIMEOUT = 600
    EXPORT_TIMEOUT = 120

    def __init__(self, dvp_exe: str, project_path: str, report_dir: str = "./build/reports"):
        self.dvp_exe = dvp_exe
        self.project_path = project_path
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

        if not Path(dvp_exe).exists() and not self._is_on_path(dvp_exe):
            raise FileNotFoundError(
                f"DaVinciCFG.exe not found at '{dvp_exe}'. "
                f"Set DVP_EXE in .mcp.json to the correct path."
            )

    @staticmethod
    def _is_on_path(exe: str) -> bool:
        """Check if executable is on system PATH."""
        from shutil import which
        return which(exe) is not None

    def _run(self, args: List[str], timeout: int) -> subprocess.CompletedProcess:
        """Execute DVP CLI command with timeout and error handling."""
        cmd = [self.dvp_exe] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(self.project_path) or "."
            )
            return result
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"DaVinci CLI timed out after {timeout}s. "
                f"Command: {' '.join(cmd)}"
            )
        except FileNotFoundError:
            raise FileNotFoundError(
                f"DaVinciCFG.exe not found: {self.dvp_exe}"
            )

    def open_project(self, dpa_path: Optional[str] = None) -> str:
        """Open a .dpa project file."""
        path = dpa_path or self.project_path
        if not Path(path).exists():
            raise FileNotFoundError(f"Project file not found: {path}")

        result = self._run(
            ["--project", str(path)],
            timeout=self.OPEN_TIMEOUT
        )

        if result.returncode != 0:
            raise DaVinciCLIError(
                f"Failed to open project: {result.stderr}",
                returncode=result.returncode,
                stderr=result.stderr
            )

        self.project_path = str(path)
        return result.stdout

    def import_arxml(self, arxml_paths: List[str]) -> str:
        """
        Import ARXML configuration fragments into the open project.

        Args:
            arxml_paths: List of ARXML file paths to import.
                         Imported in order (bottom-up for reference resolution).
        Returns:
            DVP stdout output.
        Raises:
            FileNotFoundError: If any ARXML file doesn't exist.
            DaVinciCLIError: If import fails.
        """
        # Validate all files exist before calling DVP
        for p in arxml_paths:
            if not Path(p).exists():
                raise FileNotFoundError(f"ARXML file not found: {p}")

        result = self._run(
            ["--project", self.project_path, "--import"] + arxml_paths,
            timeout=self.IMPORT_TIMEOUT
        )

        if result.returncode not in (0,):
            raise DaVinciCLIError(
                f"ARXML import failed: {result.stderr}",
                returncode=result.returncode,
                stderr=result.stderr
            )

        return result.stdout

    def validate(self, modules: Optional[List[str]] = None) -> List[ValidationError]:
        """
        Run DVP validation engine and return structured errors.

        Args:
            modules: Optional list of module names to validate.
                     Empty list = validate all modules.
        Returns:
            List of ValidationError objects, sorted by severity (ERROR first).
        """
        report_xml = str(self.report_dir / "validation_report.xml")
        report_html = str(self.report_dir / "validation_report.html")

        args = [
            "--project", self.project_path,
            "--validate",
            "--report", report_xml
        ]

        result = self._run(args, timeout=self.VALIDATE_TIMEOUT)

        # DVP returns 0 = clean, 1 = validation errors found, other = crash
        if result.returncode not in (0, 1):
            raise DaVinciCLIError(
                f"DVP validation crashed: {result.stderr}",
                returncode=result.returncode,
                stderr=result.stderr
            )

        # Parse the validation report
        errors = []
        if Path(report_xml).exists():
            errors = parse_validation_report_xml(report_xml)
        elif Path(report_html).exists():
            errors = parse_validation_report_html(report_html)
        else:
            # Fallback: parse stdout for error patterns
            errors = self._parse_stdout_errors(result.stdout)

        # Filter by module if specified
        if modules:
            module_set = {m.lower() for m in modules}
            errors = [e for e in errors if e.module.lower() in module_set]

        # Sort: ERROR > WARNING > INFO
        severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        errors.sort(key=lambda e: severity_order.get(e.severity, 99))

        # Categorize errors for the fixer agent
        for e in errors:
            e.category = self._categorize_error(e)

        return errors

    def generate(self, modules: Optional[List[str]] = None) -> dict:
        """
        Trigger BSW/RTE code generation.

        Args:
            modules: Optional list of modules to generate. Empty = all.
        Returns:
            Dict with returncode, stdout, stderr, and generated file list.
        """
        args = ["--project", self.project_path, "--generate"]

        result = self._run(args, timeout=self.GENERATE_TIMEOUT)

        # Collect generated files from output directory
        gen_dir = Path(self.project_path).parent / "generated"
        generated_files = []
        if gen_dir.exists():
            generated_files = [
                str(f.relative_to(gen_dir))
                for f in gen_dir.rglob("*")
                if f.is_file() and f.suffix in (".c", ".h")
            ]

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "generated_files": generated_files,
            "generated_count": len(generated_files)
        }

    def export_arxml(self, output_path: str) -> str:
        """Export current project configuration as ARXML."""
        result = self._run(
            ["--project", self.project_path, "--export", output_path],
            timeout=self.EXPORT_TIMEOUT
        )

        if result.returncode != 0:
            raise DaVinciCLIError(
                f"ARXML export failed: {result.stderr}",
                returncode=result.returncode,
                stderr=result.stderr
            )

        return result.stdout

    @staticmethod
    def _parse_stdout_errors(stdout: str) -> List[ValidationError]:
        """Fallback parser for DVP stdout when no XML/HTML report is available."""
        errors = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            severity = ""
            if "ERROR" in line.upper():
                severity = "ERROR"
            elif "WARNING" in line.upper():
                severity = "WARNING"
            elif "INFO" in line.upper():
                severity = "INFO"

            if severity:
                # Try to extract module name (usually first word or in brackets)
                module = ""
                if "[" in line and "]" in line:
                    module = line[line.index("[") + 1:line.index("]")]

                errors.append(ValidationError(
                    module=module,
                    severity=severity,
                    message=line,
                ))

        return errors

    @staticmethod
    def _categorize_error(error: ValidationError) -> str:
        """
        Categorize a validation error for the fixer agent.

        Categories:
            AUTO_FIX:     Can be fixed automatically without domain judgment
            PARAM_ADJUST: Parameter value needs adjustment (range, type)
            MISSING_REF:  Cross-module reference is missing or broken
            STRUCTURAL:   Missing container or sub-container
            ESCALATE:     Requires human judgment (ASIL, OEM deviation)
        """
        msg = error.message.lower()
        rule = error.rule_id.lower()

        # Missing references
        if "unresolved reference" in msg or "undefined" in msg or "missing reference" in msg:
            return "MISSING_REF"

        # Duplicate names
        if "duplicate" in msg:
            return "AUTO_FIX"

        # Value out of range
        if "out of range" in msg or "invalid value" in msg:
            return "PARAM_ADJUST"

        # Missing container
        if "missing container" in msg or "required container" in msg:
            return "STRUCTURAL"

        # Size mismatch
        if "size" in msg and ("mismatch" in msg or "too small" in msg or "does not match" in msg):
            return "PARAM_ADJUST"

        # CRC-related
        if "crc" in msg:
            return "PARAM_ADJUST"

        # ASIL-related → always escalate
        if "asil" in msg or "safety" in msg:
            return "ESCALATE"

        # Default: try auto-fix
        return "AUTO_FIX"
