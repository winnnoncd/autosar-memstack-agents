#!/bin/bash
# hooks/post-generate.sh
# postToolUse hook for Copilot CLI: compile smoke test after DVP code generation.
#
# Copilot CLI passes JSON via stdin:
#   {"timestamp": ..., "cwd": "...", "toolName": "...", "toolArgs": "{...}"}
#
# Only acts when toolName is davinci_generate; exits 0 otherwise.

set -euo pipefail

INPUT=$(cat)

# Check toolName — only run for davinci_generate
TOOL_NAME=$(python3 << 'PYEOF'
import json, sys

raw = sys.stdin.read()
try:
    data = json.loads(raw)
    print(data.get('toolName', ''))
except Exception:
    print('')
PYEOF
<<< "$INPUT" 2>/dev/null || echo "")

if [[ "$TOOL_NAME" != "davinci_generate" ]]; then
    exit 0
fi

GEN_DIR="generated"
LOG_DIR="build/reports"
mkdir -p "$LOG_DIR"

if [[ ! -d "$GEN_DIR" ]]; then
    echo "INFO: No generated/ directory found, skipping compile check"
    exit 0
fi

C_FILES=$(find "$GEN_DIR" -name "*.c" 2>/dev/null | wc -l)
H_FILES=$(find "$GEN_DIR" -name "*.h" 2>/dev/null | wc -l)

if [[ "$C_FILES" -eq 0 ]]; then
    echo "INFO: No .c files found in $GEN_DIR, skipping compile check"
    exit 0
fi

echo "Post-generate check: found $C_FILES .c files, $H_FILES .h files"

ERRORS=0
ERROR_LOG="$LOG_DIR/post_generate_errors.log"
> "$ERROR_LOG"

for src in $(find "$GEN_DIR" -name "*.c"); do
    if command -v gcc &>/dev/null; then
        if ! gcc -fsyntax-only -x c \
            -I "$GEN_DIR" \
            -I "$GEN_DIR/include" \
            "$src" 2>>"$ERROR_LOG"; then
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

if [[ "$ERRORS" -gt 0 ]]; then
    echo "WARNING: $ERRORS generated files have syntax errors. See $ERROR_LOG"
else
    echo "OK: All $C_FILES generated .c files pass syntax check"
fi
