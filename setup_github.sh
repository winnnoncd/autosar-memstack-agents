#!/bin/bash
# setup_github.sh — Initialize git repo and push to GitHub
#
# Usage:
#   ./setup_github.sh <github-username>
#
# Prerequisites:
#   - git configured with your credentials
#   - gh CLI installed (or create repo manually on github.com)

set -euo pipefail

USERNAME="${1:-}"

if [[ -z "$USERNAME" ]]; then
    echo "Usage: $0 <github-username>"
    echo "Example: $0 myuser"
    exit 1
fi

REPO_NAME="autosar-memstack-agents"

echo "=== Initializing git repository ==="
git init
git add -A
git commit -m "feat: AUTOSAR memory stack auto-configuration harness

Complete Claude Code harness for automatic configuration of the
AUTOSAR Classic Memory Stack (NvM, MemIf, Fee/Ea, Fls/Eep)
using Vector DaVinci Configurator.

Components:
- MCP server: DaVinci CLI + PAI bridge (9 tools)
- Skills: 9 domain knowledge files (NvM, Fee, Ea, MemIf, Fls/Eep, ARXML)
- Agents: 5 specialized workers (analyze, generate, validate, review, build)
- Hooks: 4 lifecycle hooks (pre/post ARXML write, post-generate, session-end)
- Templates: 6 Jinja2 ARXML templates (NvM, Fee, Ea, MemIf, Fls, Eep)
- Tests: 61 passing tests (unit + integration)

Architecture follows the harness paradigm: model reasons, harness governs.
Human approval gate for all ASIL safety decisions."

echo ""
echo "=== Creating GitHub repository ==="

if command -v gh &>/dev/null; then
    gh repo create "$REPO_NAME" \
        --public \
        --description "Claude Code harness for automatic AUTOSAR Classic Memory Stack configuration with DaVinci Configurator" \
        --source=. \
        --push
    echo ""
    echo "Done! Repository: https://github.com/$USERNAME/$REPO_NAME"
else
    echo "gh CLI not found. Create the repo manually, then run:"
    echo ""
    echo "  git remote add origin https://github.com/$USERNAME/$REPO_NAME.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi
