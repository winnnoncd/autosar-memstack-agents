#!/bin/bash
# hooks/pre-arxml-write.sh
# preToolUse hook for Copilot CLI: validates ARXML files before writing.
#
# Copilot CLI passes JSON via stdin:
#   {"timestamp": ..., "cwd": "...", "toolName": "...", "toolArgs": "{...}"}
#
# Outputs {"permissionDecision": "deny", "message": "..."} to block malformed ARXML.
# Outputs nothing to allow.

set -euo pipefail

INPUT=$(cat)

# Extract file_path from toolArgs (toolArgs is a JSON-encoded string within the outer JSON)
FILE_PATH=$(python3 << 'PYEOF'
import json, sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

args = data.get('toolArgs', '{}')
if isinstance(args, str):
    try:
        args = json.loads(args)
    except Exception:
        args = {}

path = (args.get('file_path') or args.get('path') or args.get('target_file') or '').strip()
print(path)
PYEOF
<<< "$INPUT" 2>/dev/null || echo "")

# Only validate .arxml files
if [[ -z "$FILE_PATH" || "$FILE_PATH" != *.arxml ]]; then
    exit 0
fi

# Skip if file doesn't exist yet (new file being created)
if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Run Python pre-validation — capture output and exit code
VALIDATION_OUTPUT=$(python3 << PYEOF 2>&1 || true
import sys
from lxml import etree

filepath = '$FILE_PATH'
errors = []

try:
    tree = etree.parse(filepath)
except etree.XMLSyntaxError as e:
    print(f'XML syntax error: {e}')
    sys.exit(1)

root = tree.getroot()

# Check no duplicate SHORT-NAMEs within same parent
for parent in root.iter():
    names = []
    for child in parent:
        tag = child.tag
        if tag.endswith('}SHORT-NAME') or tag == 'SHORT-NAME':
            if child.text:
                names.append(child.text)
    seen = set()
    for name in names:
        if name in seen:
            errors.append(f'Duplicate SHORT-NAME: {name}')
        seen.add(name)

# Check DEFINITION-REFs have DEST attribute
ns = 'http://autosar.org/schema/r4.0'
for defref in root.iter(f'{{{ns}}}DEFINITION-REF'):
    if 'DEST' not in defref.attrib:
        errors.append(f'DEFINITION-REF missing DEST: {defref.text}')

if errors:
    for e in errors:
        print(e)
    sys.exit(1)
PYEOF
)

# Check exit code of the subshell
if [[ $? -ne 0 ]] || echo "$VALIDATION_OUTPUT" | grep -qE "^(XML syntax error|Duplicate SHORT-NAME|DEFINITION-REF missing)"; then
    SAFE_MSG=$(echo "$VALIDATION_OUTPUT" | head -3 | tr '\n' ' ' | sed 's/"/\\"/g')
    printf '{"permissionDecision": "deny", "message": "ARXML pre-validation failed for %s: %s"}\n' \
        "$FILE_PATH" "$SAFE_MSG"
fi

# Allow by exiting 0 with no output
exit 0
