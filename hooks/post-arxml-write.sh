#!/bin/bash
# hooks/post-arxml-write.sh
# PostToolUse hook: runs quick schema check after ARXML file modifications.
#
# Catches issues introduced during editing (malformed patches, etc.)
#
# Hook configuration in .claude/hooks.json:
# {
#   "hooks": [{
#     "event": "PostToolUse",
#     "pattern": "*.arxml",
#     "command": "bash hooks/post-arxml-write.sh"
#   }]
# }

set -euo pipefail

FILE="${1:-}"

if [[ -z "$FILE" || "$FILE" != *.arxml || ! -f "$FILE" ]]; then
    exit 0
fi

# Quick well-formedness check
python3 -c "
from lxml import etree
try:
    etree.parse('$FILE')
    print('OK: $FILE is well-formed XML')
except etree.XMLSyntaxError as e:
    print(f'WARNING: $FILE has XML errors: {e}')
    # Don't block — the validation-fixer will catch this
" 2>&1
