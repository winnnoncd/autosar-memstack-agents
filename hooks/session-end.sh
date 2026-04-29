#!/bin/bash
# hooks/session-end.sh
# sessionEnd hook for Copilot CLI: writes session progress to AGENTS.md.
#
# Copilot CLI passes JSON via stdin on session end.
# Appends a session log entry so the next session picks up context.

set -euo pipefail

# Drain stdin (Copilot CLI passes session JSON — content not needed here)
INPUT=$(cat) || true

TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
AGENTS_MD="AGENTS.md"

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

# Append session delta to AGENTS.md
cat >> "$AGENTS_MD" << EOF

### Session $TIMESTAMP
- Blocks in analysis: $BLOCK_COUNT
- ARXML status: $ARXML_STATUS
- Last validation: $VALIDATION_STATUS
EOF

echo "Session delta written to $AGENTS_MD"
