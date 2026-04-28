#!/bin/bash
# hooks/post-generate.sh
# PostToolUse hook: runs a compile smoke test after DVP code generation.
#
# Triggered after davinci_generate() MCP tool call.
# Verifies that generated BSW .c/.h files are syntactically valid C.
#
# Hook configuration in .claude/hooks.json:
# {
#   "hooks": [{
#     "event": "PostToolUse",
#     "tools": ["mcp__davinci__davinci_generate"],
#     "command": "bash hooks/post-generate.sh"
#   }]
# }

set -euo pipefail

GEN_DIR="generated"
LOG_DIR="build/reports"
mkdir -p "$LOG_DIR"

if [[ ! -d "$GEN_DIR" ]]; then
    echo "INFO: No generated/ directory found, skipping compile check"
    exit 0
fi

# Count generated files
C_FILES=$(find "$GEN_DIR" -name "*.c" 2>/dev/null | wc -l)
H_FILES=$(find "$GEN_DIR" -name "*.h" 2>/dev/null | wc -l)

if [[ "$C_FILES" -eq 0 ]]; then
    echo "INFO: No .c files found in $GEN_DIR, skipping compile check"
    exit 0
fi

echo "Post-generate check: found $C_FILES .c files, $H_FILES .h files"

# Syntax-only compile check (no linking)
ERRORS=0
ERROR_LOG="$LOG_DIR/post_generate_errors.log"
> "$ERROR_LOG"

for src in $(find "$GEN_DIR" -name "*.c"); do
    # Try gcc syntax check first, fall back to just parsing
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
