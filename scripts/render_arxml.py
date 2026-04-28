#!/usr/bin/env python3
"""
render_arxml.py — Render ARXML configuration files from Jinja2 templates.

Usage:
    python scripts/render_arxml.py build/analysis.json -o project/config/

Renders bottom-up: Fls → Fee → MemIf → NvM
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("ERROR: jinja2 not installed. Run: pip install jinja2", file=sys.stderr)
    sys.exit(2)


# Rendering order: bottom-up for reference resolution
MODULES = [
    ("Fls", "Fls_Config.arxml.j2"),
    ("Fee", "Fee_Config.arxml.j2"),
    ("MemIf", "MemIf_Config.arxml.j2"),
    ("NvM", "NvM_Config.arxml.j2"),
]


def render_all(analysis: dict, template_dir: str, output_dir: str) -> list[str]:
    """
    Render all ARXML templates with analysis data.

    Returns list of generated file paths.
    """
    env = Environment(
        loader=FileSystemLoader(template_dir),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated = []

    for module_name, template_name in MODULES:
        # Skip Ea/Eep templates if using Fee/Fls (and vice versa)
        if module_name == "Fls" and analysis["memory_type"] != "FEE":
            template_name = "Eep_Config.arxml.j2"
            module_name = "Eep"
        if module_name == "Fee" and analysis["memory_type"] != "FEE":
            template_name = "Ea_Config.arxml.j2"
            module_name = "Ea"

        try:
            template = env.get_template(template_name)
        except Exception as e:
            print(f"WARNING: Template {template_name} not found, skipping: {e}")
            continue

        rendered = template.render(**analysis)

        out_file = output_path / f"{module_name}_Config.arxml"
        out_file.write_text(rendered, encoding="utf-8")
        generated.append(str(out_file))
        print(f"Generated: {out_file}")

    return generated


def main():
    parser = argparse.ArgumentParser(description="Render ARXML from templates")
    parser.add_argument("analysis_file", help="Path to build/analysis.json")
    parser.add_argument("-t", "--templates", default="templates/",
                        help="Template directory (default: templates/)")
    parser.add_argument("-o", "--output", default="project/config/",
                        help="Output directory (default: project/config/)")
    args = parser.parse_args()

    analysis = json.loads(Path(args.analysis_file).read_text())
    generated = render_all(analysis, args.templates, args.output)

    print(f"\n{len(generated)} ARXML files generated in {args.output}")
    print("Run 'python scripts/validate_arxml.py project/config/*.arxml' to pre-validate.")


if __name__ == "__main__":
    main()
