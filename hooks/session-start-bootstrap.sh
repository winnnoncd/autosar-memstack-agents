#!/bin/bash
# hooks/session-start-bootstrap.sh
# sessionStart hook: injects AUTOSAR skill-checking context at session start.
# Copilot CLI: outputs {"additionalContext": "..."} JSON to stdout.

set -euo pipefail

BOOTSTRAP_TEXT="This project has AUTOSAR memory stack configuration skills. \
Before answering ANY question about NvM, Fee, Ea, MemIf, Fls, Eep, ARXML, \
DaVinci, or memory stack configuration: invoke the relevant skill. \
If the user wants to configure the memory stack, invoke memstack-requirements first. \
Never jump directly to memstack-configure without first running memstack-requirements. \
If there is even a 1% chance a memory stack skill applies, invoke it."

# Detect runtime: Copilot CLI sets COPILOT_CLI env var
if [ -n "${COPILOT_CLI:-}" ]; then
  printf '{"additionalContext": "%s"}\n' "$BOOTSTRAP_TEXT"
else
  # Generic fallback: print to stderr so it shows as context info
  echo "$BOOTSTRAP_TEXT" >&2
fi
