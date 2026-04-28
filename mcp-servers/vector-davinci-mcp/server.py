"""
Vector DaVinci Configurator MCP Server
=======================================
Bridges Claude Code to DaVinci Configurator Classic via CLI and PAI.
Transport: stdio (local process, DVP runs on same machine).

Tools exposed:
  davinci_open_project       Open/switch .dpa project
  davinci_import_arxml       Import ARXML fragments into project
  davinci_validate           Run validation, return structured errors
  davinci_generate           Trigger BSW/RTE code generation
  davinci_export_arxml       Export current config as ARXML
  davinci_get_parameter      Read single param via PAI (requires WF)
  davinci_set_parameter      Write single param via PAI (requires WF)
  davinci_batch_set          Batch-write multiple params via PAI
  davinci_run_script         Execute a PAI Groovy workflow script
"""

import asyncio
import json
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from cli_wrapper import DaVinciCLI, ValidationError
from pai_bridge import PAIBridge
from validation_parser import parse_validation_report_html

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
DVP_EXE = os.environ.get("DVP_EXE", "DaVinciCFG.exe")
DVP_PROJECT = os.environ.get("DVP_PROJECT", "")
DVP_REPORT_DIR = os.environ.get("DVP_REPORT_DIR", "./build/reports")
DVP_PAI_SCRIPTS = os.environ.get("DVP_PAI_SCRIPTS", "./groovy_templates")

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
server = Server("vector-davinci-mcp")
cli = DaVinciCLI(dvp_exe=DVP_EXE, project_path=DVP_PROJECT, report_dir=DVP_REPORT_DIR)
pai = PAIBridge(dvp_exe=DVP_EXE, project_path=DVP_PROJECT, script_dir=DVP_PAI_SCRIPTS)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
TOOLS = [
    Tool(
        name="davinci_open_project",
        description="Open a DaVinci Configurator project (.dpa file).",
        inputSchema={
            "type": "object",
            "properties": {
                "dpa_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the .dpa project file."
                }
            },
            "required": ["dpa_path"]
        }
    ),
    Tool(
        name="davinci_import_arxml",
        description=(
            "Import one or more ARXML files into the open DaVinci project. "
            "Files are imported in the order provided."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "arxml_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ARXML file paths to import."
                }
            },
            "required": ["arxml_paths"]
        }
    ),
    Tool(
        name="davinci_validate",
        description=(
            "Run the DaVinci validation engine on the current project. "
            "Returns a structured list of validation errors with module, "
            "rule ID, severity, message, parameter path, and fix hint."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "modules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: validate only these modules (e.g. ['NvM', 'Fee']). Empty = all."
                }
            }
        }
    ),
    Tool(
        name="davinci_generate",
        description=(
            "Trigger BSW/RTE code generation for the current project. "
            "Returns generation log and list of generated files."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "modules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: generate only these modules. Empty = all."
                }
            }
        }
    ),
    Tool(
        name="davinci_export_arxml",
        description="Export the current project configuration as ARXML to a specified path.",
        inputSchema={
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "File path for the exported ARXML."
                }
            },
            "required": ["output_path"]
        }
    ),
    Tool(
        name="davinci_get_parameter",
        description=(
            "Read a single AUTOSAR parameter value by path via PAI. "
            "Requires Option WF license."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "param_path": {
                    "type": "string",
                    "description": (
                        "Full AUTOSAR parameter path, e.g. "
                        "/AUTOSAR/NvM/NvMBlockDescriptor_VehicleSpeed/NvMNvBlockLength"
                    )
                }
            },
            "required": ["param_path"]
        }
    ),
    Tool(
        name="davinci_set_parameter",
        description=(
            "Write a single AUTOSAR parameter value by path via PAI. "
            "Runs a mini-validation after setting. Requires Option WF license."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "param_path": {
                    "type": "string",
                    "description": "Full AUTOSAR parameter path."
                },
                "value": {
                    "type": "string",
                    "description": "Value to set (string representation)."
                }
            },
            "required": ["param_path", "value"]
        }
    ),
    Tool(
        name="davinci_batch_set",
        description=(
            "Set multiple AUTOSAR parameters in a single DVP session. "
            "More efficient than repeated davinci_set_parameter calls. "
            "Requires Option WF license."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "parameters": {
                    "type": "object",
                    "description": "Map of parameter_path → value.",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["parameters"]
        }
    ),
    Tool(
        name="davinci_run_script",
        description=(
            "Execute a named PAI Groovy workflow script inside DVP. "
            "Requires Option WF license."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "script_name": {
                    "type": "string",
                    "description": "Name of Groovy script file (without path, looked up in PAI scripts dir)."
                },
                "args": {
                    "type": "object",
                    "description": "Key-value arguments passed to the script.",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["script_name"]
        }
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool calls to CLI or PAI bridge."""
    try:
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except FileNotFoundError as e:
        return [TextContent(type="text", text=json.dumps({
            "error": "DVP executable not found",
            "detail": str(e),
            "hint": "Check DVP_EXE environment variable in .mcp.json"
        }))]
    except TimeoutError as e:
        return [TextContent(type="text", text=json.dumps({
            "error": "DVP operation timed out",
            "detail": str(e),
            "hint": "DVP may be loading a large project. Increase timeout or use PAI persistent session."
        }))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "error": type(e).__name__,
            "detail": str(e)
        }))]


async def _dispatch(name: str, args: dict[str, Any]) -> dict:
    """Route tool call to the appropriate backend."""

    if name == "davinci_open_project":
        dpa_path = args["dpa_path"]
        cli.project_path = dpa_path
        pai.project_path = dpa_path
        result = await asyncio.to_thread(cli.open_project, dpa_path)
        return {"status": "ok", "project": dpa_path, "detail": result}

    elif name == "davinci_import_arxml":
        paths = args["arxml_paths"]
        result = await asyncio.to_thread(cli.import_arxml, paths)
        return {"status": "ok", "imported": paths, "detail": result}

    elif name == "davinci_validate":
        modules = args.get("modules", [])
        errors = await asyncio.to_thread(cli.validate, modules)
        return {
            "status": "ok" if not errors else "validation_errors",
            "error_count": len(errors),
            "errors": [e.to_dict() for e in errors]
        }

    elif name == "davinci_generate":
        modules = args.get("modules", [])
        result = await asyncio.to_thread(cli.generate, modules)
        return result

    elif name == "davinci_export_arxml":
        output_path = args["output_path"]
        result = await asyncio.to_thread(cli.export_arxml, output_path)
        return {"status": "ok", "output": output_path, "detail": result}

    elif name == "davinci_get_parameter":
        value = await asyncio.to_thread(pai.get_parameter, args["param_path"])
        return {"param_path": args["param_path"], "value": value}

    elif name == "davinci_set_parameter":
        result = await asyncio.to_thread(
            pai.set_parameter, args["param_path"], args["value"]
        )
        return result

    elif name == "davinci_batch_set":
        result = await asyncio.to_thread(pai.batch_set, args["parameters"])
        return result

    elif name == "davinci_run_script":
        result = await asyncio.to_thread(
            pai.run_script, args["script_name"], args.get("args", {})
        )
        return result

    else:
        return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
