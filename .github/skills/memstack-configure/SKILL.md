---
name: memstack-configure
description: Use when requirements are gathered and user wants to execute memory stack configuration against DaVinci Configurator
---

# Memory Stack Configuration — Rigid Process

This is a RIGID skill. Follow exactly. No shortcuts. No rationalization.

## Preconditions
- [ ] `memstack_input.json` exists and is valid
- [ ] `memory_hw_spec.json` exists and is valid
- [ ] DaVinci MCP server is responding (call `davinci_open_project`)
- [ ] Git working tree is clean (`git status --porcelain` returns empty)

DO NOT PROCEED if any precondition fails. Tell the user what is missing.

---

## Step 1: Input Analysis
- [ ] Run: `python scripts/analyze_input.py memstack_input.json memory_hw_spec.json -o build/analysis.json`
- Verify: `test -f build/analysis.json && python3 -c "import json; d=json.load(open('build/analysis.json')); assert len(d['blocks']) > 0"`
- Present budget summary to user:
  - Total blocks, total RAM bytes, total NV bytes, utilization %
  - ASIL-flagged blocks (if any)
- STOP: "Analysis complete. [budget summary]. Confirm analysis is correct and proceed?"

DO NOT PROCEED to Step 2 until user confirms.

---

## Step 2: ARXML Generation
- [ ] Run: `python scripts/render_arxml.py build/analysis.json -o project/config/`
- [ ] Run pre-validation on ALL generated files:
  ```bash
  python scripts/validate_arxml.py project/config/Fls_Config.arxml
  python scripts/validate_arxml.py project/config/Fee_Config.arxml
  python scripts/validate_arxml.py project/config/MemIf_Config.arxml
  python scripts/validate_arxml.py project/config/NvM_Config.arxml
  ```
- Verify: every `validate_arxml.py` call exits 0
- If pre-validation fails: fix the template issue, re-render, re-validate
- DO NOT PROCEED to DVP import until pre-validation passes for ALL files
- STOP: "Pre-validation passed. All ARXML files are well-formed. Proceed to DVP import?"

DO NOT PROCEED to Step 3 until user confirms.

---

## Step 3: DVP Import + Validation Loop
- [ ] `git add -A && git commit -m "pre-dvp-import: generated memstack ARXML"`
- [ ] Call MCP: `davinci_import_arxml` with all generated files (bottom-up order)
- [ ] Call MCP: `davinci_validate`
- If 0 errors → proceed to Step 4
- If errors:
  - Group errors by root container path (e.g., all NvM/NvMBlockDescriptor_X errors together)
  - For each error group, dispatch a subagent with:
    - Only this error group's details (≤500 tokens of context)
    - Only the relevant module skill (e.g., `memstack-nvm` for NvM errors, `memstack-fee` for Fee errors)
    - The `arxml-validation-fix` skill
    - Task: "Generate ARXML patches for these specific errors"
  - Collect patches from all subagents
  - Apply all patches to project/config/ ARXML files
  - Re-run `davinci_import_arxml` and `davinci_validate`
  - Repeat up to **5 iterations maximum**
  - If errors persist after 5 iterations → STOP, present remaining errors to user
- Verify: `davinci_validate` returns 0 errors
- [ ] `git add -A && git commit -m "post-validation: 0 errors, iteration N"`

---

## Step 4: ASIL Safety Review
⛔ **MANDATORY HUMAN GATE — NEVER AUTO-PROCEED**

- [ ] Invoke `memstack-verification` skill — run the ASIL-specific checks
- Present structured review table to user (one row per ASIL >= B block):

  | Block Name | ASIL | Redundant | CRC | CRC Type | Immediate | Status |
  |---|---|---|---|---|---|---|
  | ... | ... | ... | ... | ... | ... | ... |

- STOP: "Safety review complete. [table above]. Do you approve code generation? (MANDATORY — cannot proceed without explicit approval)"

DO NOT PROCEED under any circumstances without explicit user approval.
DO NOT call any MCP tools after presenting the review until approval received.

---

## Step 5: Code Generation
- [ ] `git add -A && git commit -m "pre-generation: approved memstack config"`
- [ ] Call MCP: `davinci_generate`
- Verify: generation returns a file list containing at least 1 `.c` file

---

## Step 6: Build Verification
- [ ] Dispatch build-verifier agent to compile generated code
- [ ] Run MISRA-C check if cppcheck/MISRA tool is available
- Present build result to user (pass/fail, warning count, MISRA violations if any)

---

## Step 7: Completion
- [ ] Invoke `memstack-verification` skill — run the full post-completion checklist (all 9+ items)
- [ ] Write session summary to `AGENTS.md` under `## Session Log`:
  - Blocks configured (count + names)
  - Validation iterations needed
  - Errors fixed automatically vs. escalated
  - Code generation status
  - Build verification result
- [ ] Write detailed report to `docs/plans/YYYY-MM-DD-memstack-config.md`
- STOP: "Configuration complete. [summary]"
