#!/bin/bash
# hooks/session-end.sh
# SessionEnd hook: writes session progress to CLAUDE.md for cross-session persistence.
#
# This ensures the next Claude Code session picks up where this one left off.
#
# Hook configuration in .claude/hooks.json:
# {
#   "hooks": [{
#     "event": "SessionEnd",
#     "command": "bash hooks/session-end.sh"
#   }]
# }

set -euo pipefail

TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
CLAUDE_MD="CLAUDE.md"

# Count configured blocks (if analysis exists)
BLOCK_COUNT="N/A"
if [[ -f "build/analysis.json" ]]; then
    BLOCK_COUNT=$(python3 -c "
import json
try:
    data = json.load(open('build/analysis.json'))
    print(len(data.get('blocks', [])))
except:
    print('N/A')
" 2>/dev/null || echo "N/A")
fi

# Check if ARXML config files exist
ARXML_STATUS="not generated"
if [[ -f "project/config/NvM_Config.arxml" ]]; then
    ARXML_STATUS="generated"
fi

# Check last validation result
VALIDATION_STATUS="not run"
if [[ -f "build/reports/validation_report.xml" ]]; then
    VALIDATION_STATUS=$(python3 -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('build/reports/validation_report.xml')
    errors = [e for e in tree.iter() if 'ERROR' in (e.text or '').upper() or e.findtext('Severity','') == 'ERROR']
    print(f'{len(errors)} errors')
except:
    print('report exists, parse failed')
" 2>/dev/null || echo "unknown")
fi

# Append session delta to CLAUDE.md
cat >> "$CLAUDE_MD" << EOF

### Session $TIMESTAMP
- Blocks in analysis: $BLOCK_COUNT
- ARXML status: $ARXML_STATUS
- Last validation: $VALIDATION_STATUS
EOF

echo "Session delta written to $CLAUDE_MD"
