#!/bin/bash
# hooks/pre-arxml-write.sh
# PreToolUse hook: validates ARXML files before writing to project directory.
#
# Prevents malformed ARXML from reaching DaVinci import.
# Catches: XML syntax errors, duplicate SHORT-NAMEs, missing DEST attributes.
#
# Hook configuration in .claude/hooks.json:
# {
#   "hooks": [{
#     "event": "PreToolUse",
#     "pattern": "*.arxml",
#     "command": "bash hooks/pre-arxml-write.sh"
#   }]
# }

set -euo pipefail

FILE="${1:-}"

if [[ -z "$FILE" ]]; then
    exit 0
fi

# Only validate ARXML files
if [[ "$FILE" != *.arxml ]]; then
    exit 0
fi

# Skip if file doesn't exist yet (being created)
if [[ ! -f "$FILE" ]]; then
    exit 0
fi

# Run Python pre-validation
python3 -c "
import sys
from lxml import etree

filepath = '$FILE'
errors = []

try:
    tree = etree.parse(filepath)
except etree.XMLSyntaxError as e:
    print(f'BLOCK: Malformed ARXML: {e}', file=sys.stderr)
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
        print(f'BLOCK: {e}', file=sys.stderr)
    sys.exit(1)

print(f'OK: {filepath} passed pre-validation')
" 2>&1

exit $?
