"""
DaVinci PAI (Published Automation Interface) Bridge
=====================================================
Invokes Groovy scripts inside DVP's PAI runtime for parameter-level
read/write operations. Requires Option WF license.

The PAI runs inside DVP's process and has full access to the in-memory
AUTOSAR model — much finer-grained than CLI import/export.

Architecture:
  Claude → MCP server → PAIBridge → DaVinciCFG.exe --script <groovy>
                                   → parse stdout JSON result
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional


class PAIError(Exception):
    """Raised when a PAI Groovy script fails."""
    def __init__(self, message: str, script: str = "", stderr: str = ""):
        super().__init__(message)
        self.script = script
        self.stderr = stderr


class PAIBridge:
    """Interface to DaVinci Configurator PAI via Groovy scripts."""

    SCRIPT_TIMEOUT = 60  # seconds per script execution

    def __init__(self, dvp_exe: str, project_path: str, script_dir: str):
        self.dvp_exe = dvp_exe
        self.project_path = project_path
        self.script_dir = Path(script_dir)

    def get_parameter(self, param_path: str) -> str:
        """
        Read a single AUTOSAR parameter value by its full path.

        Args:
            param_path: Full AUTOSAR path, e.g.
                /AUTOSAR/NvM/NvMBlockDescriptor_Odo/NvMNvBlockLength

        Returns:
            Parameter value as string.
        """
        result = self._run_template("get_parameter.groovy", {
            "PARAM_PATH": param_path
        })
        return result.get("value", "")

    def set_parameter(self, param_path: str, value: str) -> dict:
        """
        Write a single AUTOSAR parameter value.

        After setting, runs a mini-validation on the affected container
        to catch immediate errors.

        Args:
            param_path: Full AUTOSAR parameter path.
            value: Value to set (string representation).

        Returns:
            Dict with status, previous value, new value, validation result.
        """
        result = self._run_template("set_parameter.groovy", {
            "PARAM_PATH": param_path,
            "VALUE": value
        })
        return result

    def batch_set(self, parameters: Dict[str, str]) -> dict:
        """
        Set multiple parameters in a single DVP session.

        This avoids the 15-30s DVP startup cost per parameter change.
        All parameters are set, then a single validation is run.

        Args:
            parameters: Dict mapping parameter_path → value.

        Returns:
            Dict with status, count of params set, validation errors.
        """
        # Serialize params as JSON for the Groovy script to parse
        params_json = json.dumps(parameters)
        result = self._run_template("batch_set.groovy", {
            "PARAMS_JSON": params_json
        })
        return result

    def query_blocks(self, module: str = "NvM") -> List[dict]:
        """
        Query all block definitions for a given module.

        Args:
            module: Module name (NvM, Fee, Ea).

        Returns:
            List of block descriptors with name, id, size, type, etc.
        """
        result = self._run_template("query_blocks.groovy", {
            "MODULE": module
        })
        return result.get("blocks", [])

    def run_script(self, script_name: str, args: Optional[Dict[str, str]] = None) -> dict:
        """
        Execute a named Groovy workflow script.

        Args:
            script_name: Filename of the Groovy script (in script_dir).
            args: Key-value arguments passed as template substitutions.

        Returns:
            Parsed JSON output from the script.
        """
        script_path = self.script_dir / script_name
        if not script_path.exists():
            raise PAIError(f"Script not found: {script_path}", script=script_name)

        template_text = script_path.read_text(encoding="utf-8")

        if args:
            template = Template(template_text)
            script_text = template.safe_substitute(args)
        else:
            script_text = template_text

        return self._execute_groovy(script_text)

    def _run_template(self, template_name: str, substitutions: Dict[str, str]) -> dict:
        """Load a Groovy template, substitute variables, and execute."""
        template_path = self.script_dir / template_name
        if not template_path.exists():
            raise PAIError(
                f"Groovy template not found: {template_path}",
                script=template_name
            )

        template_text = template_path.read_text(encoding="utf-8")
        template = Template(template_text)
        script_text = template.safe_substitute(substitutions)

        return self._execute_groovy(script_text)

    def _execute_groovy(self, script_text: str) -> dict:
        """
        Execute a Groovy script inside DVP's PAI runtime.

        The script is written to a temp file, passed to DVP via --script,
        and its stdout is parsed as JSON.
        """
        # Write script to temp file (DVP requires a file path)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".groovy", delete=False, encoding="utf-8"
        ) as f:
            f.write(script_text)
            script_file = f.name

        try:
            result = subprocess.run(
                [
                    self.dvp_exe,
                    "--project", self.project_path,
                    "--script", script_file
                ],
                capture_output=True,
                text=True,
                timeout=self.SCRIPT_TIMEOUT
            )

            if result.returncode != 0:
                raise PAIError(
                    f"PAI script failed (exit {result.returncode}): {result.stderr}",
                    script=script_text[:200],
                    stderr=result.stderr
                )

            # Parse JSON output from script stdout
            stdout = result.stdout.strip()
            if not stdout:
                return {"status": "ok", "output": ""}

            # Scripts write JSON to stdout; skip any non-JSON preamble
            json_start = stdout.find("{")
            json_end = stdout.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(stdout[json_start:json_end])

            # Try parsing as JSON array
            arr_start = stdout.find("[")
            arr_end = stdout.rfind("]") + 1
            if arr_start >= 0 and arr_end > arr_start:
                return {"result": json.loads(stdout[arr_start:arr_end])}

            return {"status": "ok", "output": stdout}

        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"PAI script timed out after {self.SCRIPT_TIMEOUT}s"
            )
        except json.JSONDecodeError as e:
            raise PAIError(
                f"PAI script returned invalid JSON: {e}",
                script=script_text[:200]
            )
        finally:
            # Clean up temp script file
            try:
                os.unlink(script_file)
            except OSError:
                pass
