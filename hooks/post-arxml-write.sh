#!/bin/bash
# hooks/post-arxml-write.sh
# postToolUse hook for Copilot CLI: well-formedness check after ARXML modification.
#
# Copilot CLI passes JSON via stdin:
#   {"timestamp": ..., "cwd": "...", "toolName": "...", "toolArgs": "{...}"}
#
# Non-blocking: reports warnings but does not deny.

set -euo pipefail

INPUT=$(cat)

# Extract file_path from toolArgs
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

if [[ -z "$FILE_PATH" || "$FILE_PATH" != *.arxml || ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Quick well-formedness check — non-blocking, warnings only
python3 << PYEOF 2>&1 || true
from lxml import etree
try:
    etree.parse('$FILE_PATH')
    print('OK: $FILE_PATH is well-formed XML')
except etree.XMLSyntaxError as e:
    print(f'WARNING: $FILE_PATH has XML errors after write: {e}')
PYEOF

exit 0
