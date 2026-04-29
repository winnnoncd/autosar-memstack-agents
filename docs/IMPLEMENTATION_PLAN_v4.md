# Implementation Plan: AUTOSAR Memory Stack Auto-Configuration Harness
## GitHub Copilot CLI (Phase 1) · GitLab Duo Migration (Phase 2)
*Version 4 — April 2026*

> **For agentic workers:** This plan is structured so that each task can be
> dispatched to a subagent with isolated context. Each task has file paths,
> verification steps, and clear completion criteria. Use the
> subagent-driven-development pattern: one subagent per task, two-stage review
> (spec compliance, then code quality) after each.

---

## 0. Context

### 0.1 What Exists

The repo `autosar-memstack-agents` has 51 files, 61 passing tests:

| Layer | Files | Status |
|-------|-------|--------|
| MCP server (`mcp-servers/vector-davinci-mcp/`) | 6 Python + 4 Groovy | Working, tested |
| Skills (`skills/*.md`) | 9 Markdown | Content correct, wrong format |
| Agents (`agents/*.md`) | 5 Markdown | Content correct, wrong format |
| Hooks (`hooks/*.sh` + `.claude/hooks.json`) | 4 scripts + 1 config | Working scripts, wrong config |
| Templates (`templates/*.j2`) | 6 Jinja2 | Working, tested |
| Scripts (`scripts/*.py`) | 3 Python | Working, 61 tests pass |
| Tests (`tests/`) | 2 test files | 61 tests, all passing |

### 0.2 What Is Wrong

The repo is structured for Claude Code. It needs restructuring for Copilot CLI with
three categories of changes:

**Structural (file layout):** Skills must be in `.github/skills/<name>/SKILL.md`
directories. Agents must be `.agent.md` files. Hooks must be in `.github/hooks/`
with `version: 1` JSON schema. `CLAUDE.md` must become `AGENTS.md`.

**Behavioral (Superpowers review findings):** Skills tell the agent WHAT to know
but not HOW to work. There are no process skills that enforce workflow discipline.
No brainstorming/requirements-gathering step. No verification-before-completion
checklist. No sessionStart context injection. Skill descriptions contain workflow
summaries instead of triggering conditions only.

**Missing skills:** Need 4 new process skills to enforce disciplined workflow:
`using-memstack-skills` (bootstrap), `memstack-requirements` (brainstorm),
rewritten `memstack-configure` (rigid process), `memstack-verification` (completion).

### 0.3 Design Principles

1. **Skills are the knowledge layer.** AUTOSAR domain knowledge in SKILL.md files
   conforming to the Agent Skills open standard. Platform-agnostic.
2. **Process skills enforce discipline.** Rigid process skills with checklists and
   stop conditions. The agent follows them exactly, no rationalization.
3. **MCP is the tool layer.** DaVinci MCP server works on any platform supporting MCP.
4. **Platform glue is thin.** Agent definitions, hook configs, instruction files are
   per-platform adapters referencing portable skills and MCP tools.
5. **Superpowers-compatible.** Plan files use checkbox format. Process skills use
   the rigid/flexible distinction. Subagent dispatch for independent tasks.
6. **Verify before claiming done.** Every task has explicit verification steps.

### 0.4 Skill Taxonomy

After this plan is implemented, the repo will have 13 skills in two categories:

**Process skills (rigid — follow exactly):**

| Skill | Triggers on | Purpose |
|-------|-------------|---------|
| `using-memstack-skills` | Every session start (via sessionStart hook) | Bootstrap: tells agent to check domain skills before any AUTOSAR response |
| `memstack-requirements` | "configure memory stack", "add NvM blocks", "set up NvM" | Brainstorming: gathers block requirements through structured questions before any generation |
| `memstack-configure` | After requirements are gathered | Rigid step-by-step workflow with checkboxes, verification gates, human approval stops |
| `memstack-verification` | Before claiming configuration is complete | Post-completion checklist: block count match, cross-references, ASIL compliance, budget fit |

**Knowledge skills (flexible — adapt to context):**

| Skill | Triggers on | Purpose |
|-------|-------------|---------|
| `memstack-nvm` | NvM, NVRAM, NvBlock, block configuration | NvM parameter rules, ID assignment, CRC, priorities |
| `memstack-fee` | Fee, flash EEPROM emulation, sector layout | Fee sector layout, block sizing, wear leveling |
| `memstack-ea` | Ea, EEPROM abstraction, external EEPROM | Ea block mapping for EEPROM variant |
| `memstack-memif` | MemIf, memory abstraction, device routing | MemIf device routing rules |
| `memstack-fls-eep` | Fls, Eep, flash driver, EEPROM driver, MCAL | Fls/Eep MCAL driver parameters |
| `arxml-generation` | ARXML, ECUC, configuration file, XML generation | AUTOSAR R4.x ARXML authoring rules |
| `arxml-validation-fix` | validation error, DVP error, fix, ECUC error | Error-to-fix pattern catalog (5 categories) |
| `davinci-cli-reference` | DaVinci, DVP, CLI, PAI, Groovy, headless | DaVinci CLI/PAI command reference |
| `memstack-configure` | (merged: this skill is both process AND knowledge) | — |

---

## Phase 1 — GitHub Copilot CLI

### Timeline: 5 weeks (25 working days)

```
Phase 1.0: Platform Spike .............. Days 1–3    (3 days)
Phase 1.1: Repo Restructure ........... Days 4–7    (4 days)
Phase 1.2: New Process Skills ......... Days 8–12   (5 days)
Phase 1.3: MCP + Hook Integration ..... Days 13–16  (4 days)
Phase 1.4: Agent Conversion ........... Days 17–20  (4 days)
Phase 1.5: End-to-End Validation ...... Days 21–25  (5 days)
```

---

### Phase 1.0 — Platform Spike (Days 1–3)

#### Purpose

Verify Copilot CLI primitives before committing to full migration.

#### File Map

```
.github/
  skills/spike-test/SKILL.md          ← create (throwaway)
  hooks/spike.json                     ← create (throwaway)
  agents/spike-agent.agent.md          ← create (throwaway)
.mcp.json                              ← create (minimal echo server)
mcp-servers/echo-server/server.py      ← create (throwaway)
docs/spike-copilot-cli.md              ← deliverable
```

#### Tasks

- [ ] **Task 1: Skill discovery spike**
  - Create `.github/skills/spike-test/SKILL.md` with description "Use when asked about AUTOSAR test spike"
  - Start Copilot CLI session in repo directory
  - Ask: "Tell me about the AUTOSAR test spike"
  - Verify: skill content appears in agent response
  - Test: `/spike-test` slash command loads the skill
  - Record result in `docs/spike-copilot-cli.md`

- [ ] **Task 2: MCP server spike**
  - Create `mcp-servers/echo-server/server.py` — minimal stdio MCP server, one `echo` tool
  - Register in `.mcp.json`
  - Start Copilot CLI session
  - Ask: "Call the echo tool with message 'hello'"
  - Verify: tool appears in tool list AND call succeeds
  - Record result in `docs/spike-copilot-cli.md`

- [ ] **Task 3: Hook spike**
  - Create `.github/hooks/spike.json`:
    ```json
    {
      "version": 1,
      "hooks": {
        "preToolUse": [{
          "type": "command",
          "bash": "echo '{\"permissionDecision\": \"allow\"}'"
        }],
        "sessionStart": [{
          "type": "command",
          "bash": "echo '{\"additionalContext\": \"SPIKE: sessionStart hook fired\"}'"
        }]
      }
    }
    ```
  - Start Copilot CLI, trigger a tool use
  - Verify: `preToolUse` hook fires (check by modifying to log to file)
  - Test blocking: change `preToolUse` to return `{"permissionDecision": "deny", "message": "Blocked by spike"}`
  - Verify: tool call is denied with message shown
  - Test `sessionStart` → `additionalContext` injection: verify the spike text appears in session context
  - Record result in `docs/spike-copilot-cli.md`

- [ ] **Task 4: Agent delegation spike**
  - Create `.github/agents/spike-agent.agent.md`:
    ```yaml
    ---
    name: spike-agent
    description: Use when asked to run a spike test for agent delegation
    ---
    You are a test agent. Respond with "SPIKE AGENT ACTIVE" and list the tools available to you.
    ```
  - Ask Copilot: "Run the spike test for agent delegation"
  - Verify: subagent spawns with isolated context
  - Test: does subagent have access to MCP tools?
  - Record result in `docs/spike-copilot-cli.md`

- [ ] **Task 5: Write spike report**
  - Compile all results into `docs/spike-copilot-cli.md`
  - Document: what works, what doesn't, JSON input format for hooks, tool name format for MCP, any quirks
  - If `sessionStart` + `additionalContext` works → note this for bootstrap skill injection
  - If subagents lack MCP access → note fallback strategy

#### Acceptance Criteria

| # | Criterion | Pass/Fail |
|---|-----------|-----------|
| S0.1 | Skill auto-activates on matching prompt | |
| S0.2 | Skill loads via `/skill-name` slash command | |
| S0.3 | MCP server starts via stdio, tool listed | |
| S0.4 | MCP tool call returns result in conversation | |
| S0.5 | `preToolUse` hook fires on tool invocation | |
| S0.6 | Hook with `permissionDecision: deny` blocks tool call | |
| S0.7 | `sessionStart` hook injects `additionalContext` | |
| S0.8 | Custom agent spawns as subagent | |
| S0.9 | Spike report documents all findings | |

#### Decision Gate

- S0.1 + S0.3 + S0.5 all fail → **STOP**. Fall back to thick MCP server strategy.
- S0.7 fails → bootstrap skill must be loaded via `AGENTS.md` instead of hook injection. Adapt Phase 1.2 accordingly.
- S0.8 fails → agents become advisory-only (main session calls MCP directly). Adapt Phase 1.4 accordingly.
- Any single spike fails → document workaround before proceeding.

---

### Phase 1.1 — Repo Restructure (Days 4–7)

#### Purpose

Migrate file layout to Copilot CLI conventions. Rewrite all skill descriptions
to contain triggering conditions only (no workflow summaries). Add sessionStart
hook for bootstrap context injection.

#### File Map

```
MOVE/RENAME:
  skills/memstack-nvm.md        → .github/skills/memstack-nvm/SKILL.md
  skills/memstack-fee.md        → .github/skills/memstack-fee/SKILL.md
  skills/memstack-ea.md         → .github/skills/memstack-ea/SKILL.md
  skills/memstack-memif.md      → .github/skills/memstack-memif/SKILL.md
  skills/memstack-fls-eep.md    → .github/skills/memstack-fls-eep/SKILL.md
  skills/arxml-generation.md    → .github/skills/arxml-generation/SKILL.md
  skills/arxml-validation-fix.md → .github/skills/arxml-validation-fix/SKILL.md
  skills/davinci-cli-reference.md → .github/skills/davinci-cli-reference/SKILL.md
  skills/memstack-configure.md   → .github/skills/memstack-configure/SKILL.md
  CLAUDE.md                      → AGENTS.md
  .claude/hooks.json             → DELETE (replaced by .github/hooks/)

CREATE:
  .github/hooks/memstack.json            ← Copilot hook config (version: 1)
  hooks/session-start-bootstrap.sh       ← sessionStart hook script

DELETE:
  .claude/                               ← entire directory
  skills/                                ← emptied (moved to .github/skills/)
```

#### Tasks

- [ ] **Task 1: Restructure skill directories**
  - For each of the 9 skills: create `.github/skills/<name>/` directory, move skill content to `SKILL.md`
  - Remove Claude-specific frontmatter fields from each SKILL.md: `agent`, `context`, `allowed-tools`
  - Keep only: `name`, `description`
  - If skill has referenced resource files (like error_catalog.md), move them to a `references/` subdirectory inside the skill directory
  - Files: all 9 skills
  - Verify: `find .github/skills -name SKILL.md | wc -l` = 9
  - Verify: `grep -r "^agent:\|^context:\|^allowed-tools:" .github/skills/` returns empty

- [ ] **Task 2: Rewrite skill descriptions (triggering conditions only)**
  - Current BAD example (memstack-configure): `"Automatically configure the AUTOSAR Classic memory stack (NvM, MemIf, Fee/Ea, Fls/Eep) from NvBlock descriptors and hardware memory spec. Generates ARXML, imports into DaVinci Configurator, validates, auto-fixes, and triggers code generation."`
  - Correct GOOD example: `"Use when configuring the full AUTOSAR memory stack, when user has NvBlock descriptors and hardware memory spec ready for NvM, MemIf, Fee, Ea, Fls, or Eep module setup"`
  - Rewrite ALL 9 skill descriptions to contain only triggering conditions
  - Never summarize the workflow steps in the description
  - Files: all 9 `.github/skills/*/SKILL.md` files
  - Verify: no description contains verbs like "generates", "imports", "validates", "triggers"

- [ ] **Task 3: Rename instruction file**
  - Rename `CLAUDE.md` → `AGENTS.md`
  - In content: replace any "Claude Code" references with "Copilot CLI"
  - Replace "Claude" agent references with generic "agent" references
  - Keep all AUTOSAR conventions, module generation order, memory stack rules
  - Files: `AGENTS.md`
  - Verify: `test -f AGENTS.md && ! test -f CLAUDE.md`

- [ ] **Task 4: Migrate hooks config**
  - Create `.github/hooks/memstack.json` in Copilot CLI format:
    ```json
    {
      "version": 1,
      "hooks": {
        "sessionStart": [{
          "type": "command",
          "bash": "bash hooks/session-start-bootstrap.sh"
        }],
        "preToolUse": [{
          "type": "command",
          "bash": "bash hooks/pre-arxml-write.sh"
        }],
        "postToolUse": [{
          "type": "command",
          "bash": "bash hooks/post-arxml-write.sh"
        }],
        "sessionEnd": [{
          "type": "command",
          "bash": "bash hooks/session-end.sh"
        }]
      }
    }
    ```
  - Adapt hook scripts to read JSON from stdin (Copilot CLI passes `{"toolName": "...", "toolArgs": "..."}`)
  - The pre-arxml-write hook must: parse stdin JSON → extract toolArgs → check if operation targets `.arxml` files → run Python pre-validation if so → return `{"permissionDecision": "deny"}` to block or do nothing to allow
  - Files: `.github/hooks/memstack.json`, `hooks/pre-arxml-write.sh`, `hooks/post-arxml-write.sh`
  - Verify: `python -m json.tool .github/hooks/memstack.json` succeeds
  - Verify: hook scripts accept JSON on stdin without error

- [ ] **Task 5: Create sessionStart bootstrap hook**
  - Create `hooks/session-start-bootstrap.sh`:
    ```bash
    #!/bin/bash
    # Detect runtime
    if [ -n "$COPILOT_CLI" ]; then
      FORMAT="copilot"
    else
      FORMAT="generic"
    fi

    BOOTSTRAP_TEXT="This project has AUTOSAR memory stack configuration skills. \
    Before answering ANY question about NvM, Fee, Ea, MemIf, Fls, Eep, ARXML, \
    DaVinci, or memory stack configuration: invoke the relevant skill. \
    If the user wants to configure the memory stack, invoke memstack-requirements first. \
    If there is even a 1% chance a memory stack skill applies, invoke it."

    if [ "$FORMAT" = "copilot" ]; then
      echo "{\"additionalContext\": \"$BOOTSTRAP_TEXT\"}"
    else
      echo "$BOOTSTRAP_TEXT" >&2
    fi
    ```
  - Files: `hooks/session-start-bootstrap.sh`
  - Verify: `echo '{}' | bash hooks/session-start-bootstrap.sh` outputs valid JSON with `additionalContext`

- [ ] **Task 6: Clean up and verify**
  - Delete `.claude/` directory entirely
  - Delete empty `skills/` directory (content moved to `.github/skills/`)
  - Verify `.mcp.json` is still valid (may need spike findings for any Copilot-specific format)
  - Update `.gitignore` — remove `.claude/` reference
  - Run `pytest tests/ -v` — all 61 tests must still pass
  - Files: `.claude/`, `skills/`, `.gitignore`
  - Verify: `! test -d .claude && ! test -d skills`
  - Verify: `pytest tests/ -v` → 0 failures

- [ ] **Task 7: Update README**
  - Replace Claude Code setup instructions with Copilot CLI instructions
  - Update prerequisites: "GitHub Copilot CLI (GA February 2026)" instead of "Claude Code v2.1+"
  - Document: `copilot` launch, `/skill-name` commands, MCP server setup
  - Files: `README.md`
  - Verify: no mention of "Claude Code" in README (except historical attribution)

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A1.1 | 9 skills at `.github/skills/<name>/SKILL.md` | `find .github/skills -name SKILL.md \| wc -l` = 9 |
| A1.2 | No Claude-specific frontmatter in any SKILL.md | `grep -r "^agent:\|^context:\|^allowed-tools:" .github/skills/` empty |
| A1.3 | No workflow summaries in skill descriptions | No description contains "generates", "imports", "validates", "triggers" |
| A1.4 | `AGENTS.md` exists, `CLAUDE.md` gone | `test -f AGENTS.md && ! test -f CLAUDE.md` |
| A1.5 | Hook config valid at `.github/hooks/memstack.json` | `python -m json.tool` succeeds |
| A1.6 | SessionStart bootstrap hook outputs valid JSON | `echo '{}' \| bash hooks/session-start-bootstrap.sh \| python -m json.tool` |
| A1.7 | Hook scripts accept JSON stdin | All hook scripts run without parse errors on Copilot's JSON format |
| A1.8 | No `.claude/` directory remains | `! test -d .claude` |
| A1.9 | No `skills/` directory remains | `! test -d skills` |
| A1.10 | All 61 tests still pass | `pytest tests/ -v` → 0 failures |
| A1.11 | README references Copilot CLI, not Claude Code | `grep -c "Claude Code" README.md` = 0 (except attribution) |

---

### Phase 1.2 — New Process Skills (Days 8–12)

#### Purpose

Create the 4 process skills that enforce workflow discipline. These are RIGID
skills — the agent must follow them exactly, no adaptation, no rationalization.

#### File Map

```
CREATE:
  .github/skills/using-memstack-skills/SKILL.md     ← bootstrap process skill
  .github/skills/memstack-requirements/SKILL.md      ← brainstorming equivalent
  .github/skills/memstack-verification/SKILL.md      ← completion checklist

REWRITE:
  .github/skills/memstack-configure/SKILL.md         ← rigid process with checkboxes
```

#### Tasks

- [ ] **Task 1: Create `using-memstack-skills` bootstrap skill**
  - This skill is loaded at session start via the sessionStart hook's `additionalContext`
  - It tells the agent: before ANY response to an AUTOSAR question, check if a domain skill applies
  - Must include the "red flags" table from Superpowers (rationalization patterns)
  - Must include skill priority order: process skills first, then knowledge skills
  - Must include: "If the user wants to configure the memory stack, invoke `memstack-requirements` FIRST, never jump to `memstack-configure`"
  - File: `.github/skills/using-memstack-skills/SKILL.md`
  - Frontmatter:
    ```yaml
    ---
    name: using-memstack-skills
    description: Use at session start or when uncertain which AUTOSAR memory stack skill applies
    ---
    ```
  - Verify: skill content includes red-flags table, skill priority order, and "invoke memstack-requirements first" rule

- [ ] **Task 2: Create `memstack-requirements` brainstorming skill**
  - This skill activates BEFORE any configuration work begins
  - It gathers requirements through structured questions, one at a time
  - Questions must cover: block names, sizes, types (NATIVE/REDUNDANT/DATASET), ASIL levels, write policies, priorities, CRC preferences, hardware target (flash vs EEPROM), sector geometry
  - Must produce a validated `memstack_input.json` + `memory_hw_spec.json` as output
  - Must validate output against JSON schemas in `schemas/`
  - Must present computed budget summary (RAM, NV, utilization %) for user confirmation before proceeding
  - Must flag ASIL >= B blocks explicitly and confirm the user intends redundancy + CRC
  - Ends with: "Requirements gathered. Invoke `memstack-configure` to proceed with configuration."
  - File: `.github/skills/memstack-requirements/SKILL.md`
  - Frontmatter:
    ```yaml
    ---
    name: memstack-requirements
    description: Use when user wants to configure, set up, or add blocks to the AUTOSAR memory stack and requirements have not yet been gathered
    ---
    ```
  - Verify: skill includes structured question flow, JSON output format, budget confirmation step, ASIL flagging

- [ ] **Task 3: Rewrite `memstack-configure` as rigid process skill**
  - This is the master workflow skill, activated AFTER requirements are gathered
  - Structure as a rigid checklist with checkboxes, verification commands, and stop conditions
  - Each step must have:
    - Checkbox (`- [ ]`)
    - Clear action description
    - File paths affected
    - Verification command (bash command that returns 0 on success)
    - "Do not proceed until" constraint
  - Must use subagent dispatch pattern for independent tasks (generate Fls, generate Fee, etc.)
  - Must have explicit STOP gates:
    - STOP after input analysis: "Confirm analysis.json is correct?"
    - STOP after ARXML generation: "Pre-validation passed. Proceed to DVP import?"
    - STOP after safety review: "ASIL review complete. Approve code generation? (MANDATORY)"
    - STOP after build verification: "Build passed. Configuration complete."
  - Must produce a plan file at `docs/plans/YYYY-MM-DD-memstack-config.md` in Superpowers-compatible format
  - File: `.github/skills/memstack-configure/SKILL.md`
  - Frontmatter:
    ```yaml
    ---
    name: memstack-configure
    description: Use when requirements are gathered and user wants to execute memory stack configuration against DaVinci Configurator
    ---
    ```
  - Structure:
    ```markdown
    # Memory Stack Configuration — Rigid Process

    This is a RIGID skill. Follow exactly. No shortcuts. No rationalization.

    ## Preconditions
    - [ ] `memstack_input.json` exists and is valid
    - [ ] `memory_hw_spec.json` exists and is valid
    - [ ] DaVinci MCP server is responding (call `davinci_open_project`)
    - [ ] Git working tree is clean (`git status --porcelain` is empty)
    DO NOT PROCEED if any precondition fails. Tell the user what is missing.

    ## Step 1: Input Analysis
    - [ ] Run: `python scripts/analyze_input.py memstack_input.json memory_hw_spec.json -o build/analysis.json`
    - Verify: `test -f build/analysis.json && python -c "import json; d=json.load(open('build/analysis.json')); assert len(d['blocks']) > 0"`
    - Present budget summary to user
    - STOP: "Analysis complete. [budget summary]. Proceed?"

    ## Step 2: ARXML Generation
    - [ ] Run: `python scripts/render_arxml.py build/analysis.json -o project/config/`
    - [ ] Run: `python scripts/validate_arxml.py project/config/*.arxml`
    - Verify: validate_arxml.py exits 0 for ALL files
    - If pre-validation fails: fix the template issue, re-render, re-validate
    - DO NOT PROCEED to DVP import until pre-validation passes

    ## Step 3: DVP Import + Validation Loop
    - [ ] `git add -A && git commit -m "pre-dvp-import: generated memstack ARXML"`
    - [ ] Call MCP: `davinci_import_arxml` with all generated files
    - [ ] Call MCP: `davinci_validate`
    - If 0 errors → proceed to Step 4
    - If errors:
      - Group errors by root container path
      - For each error group, dispatch a subagent with:
        - The error group details
        - The relevant module skill (e.g., memstack-nvm for NvM errors)
        - The arxml-validation-fix skill
        - Task: generate ARXML patches for this error group
      - Apply patches from all subagents
      - Re-import and re-validate
      - Max 5 iterations. If errors persist → STOP, present to user
    - Verify: `davinci_validate` returns 0 errors
    - `git add -A && git commit -m "post-validation: 0 errors"`

    ## Step 4: ASIL Safety Review
    ⛔ MANDATORY HUMAN GATE — NEVER AUTO-PROCEED
    - [ ] Invoke `memstack-verification` skill for ASIL checks
    - Present structured review table to user
    - STOP: "Safety review complete. [table]. Do you approve code generation?"
    - DO NOT PROCEED without explicit user approval

    ## Step 5: Code Generation
    - [ ] `git add -A && git commit -m "pre-generation: approved config"`
    - [ ] Call MCP: `davinci_generate`
    - Verify: generation returns file list with ≥1 .c file

    ## Step 6: Build Verification
    - [ ] Compile generated code (make or gcc syntax check)
    - [ ] Run MISRA-C check if available
    - Present results to user

    ## Step 7: Completion
    - [ ] Invoke `memstack-verification` skill for final checklist
    - [ ] Write session summary to AGENTS.md
    - [ ] Write detailed report to `docs/plans/YYYY-MM-DD-memstack-config.md`
    - STOP: "Configuration complete. [summary]"
    ```
  - Verify: skill has ≥7 checkboxes, ≥4 STOP gates, verification commands on every step

- [ ] **Task 4: Create `memstack-verification` completion skill**
  - This skill runs BEFORE the agent claims configuration is complete
  - It is a checklist that must be worked through item by item
  - Checks:
    - Block count: number of blocks in generated ARXML matches `memstack_input.json`
    - Cross-references: every NvM block has a matching Fee/Ea block reference that resolves
    - ASIL compliance: every ASIL ≥ B block has REDUNDANT + CRC + CalcRamBlockCrc
    - Fee block sizing: every FeeBlockSize ≥ NvMBlockLength + header + CRC, page-aligned
    - Fee sector capacity: total block size fits in available sectors
    - NV budget: total NV usage ≤ available NV with ≥20% margin
    - Immediate write: every priority-0 block has FeeImmediateData = TRUE
    - MemIf routing: MemIfDevice references correct lower layer (Fee or Ea)
    - Fee-to-Fls reference: FeeFlsReference points to existing Fls config
  - Each check must have a verification command (Python one-liner or script call)
  - File: `.github/skills/memstack-verification/SKILL.md`
  - Frontmatter:
    ```yaml
    ---
    name: memstack-verification
    description: Use before claiming memory stack configuration is complete, and during ASIL safety review
    ---
    ```
  - Verify: skill has ≥9 checklist items, each with a verification command

- [ ] **Task 5: Test process skills on Copilot CLI**
  - Start Copilot CLI session in repo
  - Verify: sessionStart hook injects bootstrap context
  - Ask: "I want to configure NvM for my project"
  - Expected: agent invokes `memstack-requirements`, NOT `memstack-configure`
  - Provide answers to all questions
  - Expected: agent produces `memstack_input.json` and `memory_hw_spec.json`
  - Say: "Go ahead and configure"
  - Expected: agent invokes `memstack-configure`, follows rigid checklist
  - Expected: agent STOPs at each gate and waits for user input
  - Verify: agent does NOT skip any checklist step

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A2.1 | `using-memstack-skills` exists with red-flags table and skill priority | File exists, content includes rationalization patterns |
| A2.2 | `memstack-requirements` asks structured questions one at a time | Manual test: agent asks about block name before block size |
| A2.3 | `memstack-requirements` produces valid `memstack_input.json` | Output validates against `schemas/nvm_input_schema.json` |
| A2.4 | `memstack-requirements` flags ASIL blocks for confirmation | Manual test: agent explicitly asks "This is ASIL-D, confirm redundancy?" |
| A2.5 | `memstack-configure` has ≥7 checkboxes with verification commands | `grep -c "\- \[ \]" .github/skills/memstack-configure/SKILL.md` ≥ 7 |
| A2.6 | `memstack-configure` has ≥4 explicit STOP gates | `grep -c "STOP" .github/skills/memstack-configure/SKILL.md` ≥ 4 |
| A2.7 | `memstack-configure` uses subagent dispatch for error fixing | Skill text references "dispatch a subagent" for per-error-group fixing |
| A2.8 | `memstack-verification` has ≥9 checklist items with verification commands | Count checklist items |
| A2.9 | Agent invokes `memstack-requirements` BEFORE `memstack-configure` | Manual test: "configure NvM" triggers requirements first |
| A2.10 | Agent follows rigid checklist and STOPs at gates | Manual test: agent does not skip steps |
| A2.11 | Skill count is now 13 (9 existing + 4 new) | `find .github/skills -name SKILL.md \| wc -l` = 13 |
| A2.12 | All 61 existing tests still pass | `pytest tests/ -v` → 0 failures |

---

### Phase 1.3 — MCP + Hook Integration (Days 13–16)

#### Purpose

Connect DaVinci MCP server to Copilot CLI. Verify all MCP tools work.
Verify hooks enforce ARXML pre-validation and session bootstrap.

#### File Map

```
MODIFY:
  hooks/pre-arxml-write.sh       ← adapt for Copilot CLI JSON stdin
  hooks/post-arxml-write.sh      ← adapt for Copilot CLI JSON stdin
  hooks/session-end.sh           ← write to AGENTS.md instead of CLAUDE.md

NO CHANGE:
  mcp-servers/vector-davinci-mcp/*  ← server code is platform-agnostic
  .mcp.json                          ← verify compatibility (may need minor edits)
```

#### Tasks

- [ ] **Task 1: Verify MCP server registration**
  - Start Copilot CLI session
  - Check: all 9 DaVinci MCP tools appear in tool list
  - If `.mcp.json` format differs for Copilot: adapt based on spike findings
  - Files: `.mcp.json`
  - Verify: Copilot CLI session lists `davinci_validate`, `davinci_import_arxml`, `davinci_generate`, etc.

- [ ] **Task 2: Test core MCP tools against real DVP**
  - `davinci_open_project` → opens sample `.dpa`, returns success
  - `davinci_import_arxml` → imports a test ARXML, exit 0
  - `davinci_validate` → returns structured error list with ≥1 error
  - `davinci_generate` → triggers generation, returns ≥1 generated .c file
  - `davinci_export_arxml` → exports to specified path
  - Files: no changes, testing only
  - Verify: each tool call succeeds and returns expected result type

- [ ] **Task 3: Test PAI tools (if WF license available)**
  - `davinci_get_parameter` → reads NvMBlockLength for a known block
  - `davinci_set_parameter` → writes value, returns previous + new value
  - `davinci_batch_set` → sets 5 params in one session
  - Files: no changes, testing only
  - Verify: PAI tools return structured JSON results

- [ ] **Task 4: Adapt hook scripts for Copilot CLI JSON stdin**
  - Copilot CLI passes JSON to hooks via stdin:
    ```json
    {"timestamp": 1704614400000, "cwd": "/path", "toolName": "edit", "toolArgs": "{\"file_path\": \"project/config/NvM_Config.arxml\", ...}"}
    ```
  - Modify `hooks/pre-arxml-write.sh`:
    1. Read JSON from stdin: `INPUT=$(cat)`
    2. Extract tool name: `TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName')`
    3. Extract file path from toolArgs (parse nested JSON)
    4. If file ends in `.arxml` → run `python scripts/validate_arxml.py`
    5. If validation fails → output `{"permissionDecision": "deny", "message": "ARXML pre-validation failed: ..."}`
    6. If validation passes or not an ARXML file → output nothing (allows)
  - Similarly adapt `hooks/post-arxml-write.sh`
  - Modify `hooks/session-end.sh` to write to `AGENTS.md` instead of `CLAUDE.md`
  - Files: `hooks/pre-arxml-write.sh`, `hooks/post-arxml-write.sh`, `hooks/session-end.sh`
  - Verify: `echo '{"toolName":"edit","toolArgs":"{\"file_path\":\"test.arxml\"}"}' | bash hooks/pre-arxml-write.sh` does not error

- [ ] **Task 5: Test hook enforcement on Copilot CLI**
  - Create a malformed ARXML file (unclosed tag)
  - Ask Copilot to edit it or import it
  - Verify: `preToolUse` hook detects malformation, blocks the operation
  - Create a valid ARXML file
  - Ask Copilot to edit it
  - Verify: hook passes, operation proceeds
  - Files: no changes, testing only
  - Verify: malformed ARXML blocked, valid ARXML allowed

- [ ] **Task 6: Test sessionStart bootstrap injection**
  - Start new Copilot CLI session
  - Ask an AUTOSAR question WITHOUT mentioning any skill by name
  - Verify: agent invokes a domain skill before responding (proves bootstrap injection worked)
  - Files: no changes, testing only
  - Verify: agent behavior shows skill was loaded

- [ ] **Task 7: Test session-end persistence**
  - Complete a short workflow (analyze input, generate ARXML)
  - End Copilot CLI session
  - Check `AGENTS.md` for new session log entry
  - Files: no changes, testing only
  - Verify: `tail -10 AGENTS.md` shows session timestamp and block count

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A3.1 | All 9 MCP tools listed in Copilot CLI session | Tool list includes all `davinci_*` tools |
| A3.2 | `davinci_validate` returns structured errors from real .dpa | ≥1 error with module + severity + message |
| A3.3 | `davinci_import_arxml` imports valid ARXML, exit 0 | No error in response |
| A3.4 | `davinci_generate` returns generated file list | ≥1 .c file |
| A3.5 | `preToolUse` hook blocks malformed ARXML | Tool call denied with error message |
| A3.6 | `preToolUse` hook allows valid ARXML | Tool call proceeds |
| A3.7 | SessionStart bootstrap injects skill-checking context | Agent invokes skill on first AUTOSAR question |
| A3.8 | Session-end hook writes to `AGENTS.md` | New session entry appended |
| A3.9 | Hook scripts handle Copilot CLI JSON stdin without errors | No parse errors in any hook |

**Quality criteria:**

| # | Metric | Target |
|---|--------|--------|
| Q3.1 | MCP round-trip time (validate) | < 60s |
| Q3.2 | Validation error parsing accuracy | 100% of ERROR entries captured |
| Q3.3 | Hook false positive rate | 0% (never blocks valid ARXML) |

---

### Phase 1.4 — Agent Conversion (Days 17–20)

#### Purpose

Convert 5 agent definitions from Claude Code format to Copilot CLI `.agent.md`
format. Restructure validation-fixer to use subagent-per-error-group dispatch.

#### File Map

```
CREATE:
  .github/agents/input-analyzer.agent.md
  .github/agents/arxml-generator.agent.md
  .github/agents/validation-fixer.agent.md    ← major rewrite for subagent dispatch
  .github/agents/safety-reviewer.agent.md
  .github/agents/build-verifier.agent.md

DELETE:
  agents/input-analyzer.md
  agents/arxml-generator.md
  agents/validation-fixer.md
  agents/safety-reviewer.md
  agents/build-verifier.md
```

#### Tasks

- [ ] **Task 1: Convert agent frontmatter for all 5 agents**
  - For each agent, convert from Claude Code format to Copilot CLI `.agent.md`:
    - Remove: `agent:`, `context: fork`, `allowed-tools:`, `skills:`
    - Add: `tools:` list with specific tool names (based on spike findings)
    - Change description to triggering-conditions-only format
  - File: `.github/agents/*.agent.md`
  - Verify: `grep -r "^agent:\|^context:\|^allowed-tools:" .github/agents/` empty

- [ ] **Task 2: Rewrite validation-fixer for subagent dispatch pattern**
  - Current: monolithic loop that loads all errors and all skills into one context
  - Target: parent agent that dispatches subagents per error group
  - Structure:
    ```
    Parent (validation-fixer):
      1. Receive error list from davinci_validate
      2. Group errors by root container path (e.g., all NvM errors together)
      3. For each error group:
         - Dispatch subagent with:
           - Only this error group's details (~500 tokens)
           - Only the relevant module skill (e.g., memstack-nvm)
           - The arxml-validation-fix skill
           - Task: "Generate ARXML patches for these errors"
         - Subagent returns: list of patches (file path + old content + new content)
      4. Apply all patches from all subagents
      5. Re-import and re-validate
      6. Repeat up to 5 iterations
    ```
  - This keeps parent context lean: error summary + subagent results only
  - File: `.github/agents/validation-fixer.agent.md`
  - Verify: agent body references "dispatch subagent" for per-group fixing

- [ ] **Task 3: Verify safety-reviewer never auto-proceeds**
  - The safety-reviewer agent body must contain explicit instructions:
    "Present the ASIL review table to the user. DO NOT proceed. DO NOT call any MCP tools after presenting the review. Wait for explicit user approval."
  - File: `.github/agents/safety-reviewer.agent.md`
  - Verify: `grep -c "DO NOT proceed\|NEVER auto" .github/agents/safety-reviewer.agent.md` ≥ 2

- [ ] **Task 4: Test agent delegation on Copilot CLI**
  - Test input-analyzer: "Analyze my memstack_input.json" → subagent spawns
  - Test validation-fixer: "Fix these DVP validation errors: [error list]" → subagent spawns
  - Test safety-reviewer: "Review ASIL compliance for my memory stack config" → subagent spawns, presents table, WAITS
  - Test build-verifier: "Verify the generated BSW code compiles" → subagent spawns
  - Verify: each agent spawns as subagent with isolated context
  - If subagents lack MCP access (discovered in spike): document workaround and adapt

- [ ] **Task 5: Test subagent MCP tool access**
  - From validation-fixer subagent: call `davinci_validate`
  - Verify: MCP tool is accessible from subagent context
  - If not accessible: fall back to main session calling MCP, subagents advisory only

- [ ] **Task 6: Clean up old agent directory**
  - Delete `agents/` directory (content moved to `.github/agents/`)
  - Verify: `! test -d agents`

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A4.1 | 5 agents at `.github/agents/*.agent.md` | `ls .github/agents/*.agent.md \| wc -l` = 5 |
| A4.2 | No Claude-specific frontmatter | `grep -r "^agent:\|^context:" .github/agents/` empty |
| A4.3 | validation-fixer uses subagent dispatch pattern | Body references per-group subagent dispatch |
| A4.4 | safety-reviewer has explicit "DO NOT proceed" instructions | ≥2 stop directives in body |
| A4.5 | Agent delegation works on Copilot CLI | ≥3 agents spawn as subagents in testing |
| A4.6 | Subagent MCP access confirmed (or workaround documented) | `davinci_validate` callable from subagent |
| A4.7 | Old `agents/` directory removed | `! test -d agents` |
| A4.8 | All 61 tests still pass | `pytest tests/ -v` → 0 failures |

---

### Phase 1.5 — End-to-End Validation (Days 21–25)

#### Purpose

Run the full interactive workflow on Copilot CLI with a real user and DaVinci
project. This validates the entire system: skills → agents → hooks → MCP → templates.

#### Tasks

- [ ] **Task 1: Full workflow test — requirements gathering (Fee variant)**
  - Engineer starts Copilot CLI session
  - Says: "I need to configure the memory stack for my ECU"
  - Expected: agent invokes `memstack-requirements`, asks structured questions
  - Engineer provides: 5 blocks (including ASIL-D crash recorder, ASIL-B safety counter)
  - Expected: agent produces `memstack_input.json` + `memory_hw_spec.json`
  - Expected: agent presents budget summary, asks for confirmation
  - Engineer confirms
  - Verify: both JSON files validate against schemas

- [ ] **Task 2: Full workflow test — configuration execution (Fee variant)**
  - Engineer says: "Go ahead and configure"
  - Expected: agent invokes `memstack-configure`, follows rigid checklist
  - Expected: Step 1 (analysis) → STOP → user confirms
  - Expected: Step 2 (ARXML generation) → pre-validation passes
  - Expected: Step 3 (DVP import + validation) → errors fixed in ≤3 iterations
  - Expected: Step 4 (ASIL review) → STOP → user reviews table → approves
  - Expected: Step 5 (code generation) → succeeds
  - Expected: Step 6 (build verification) → compiles
  - Expected: Step 7 (completion) → verification checklist, session summary
  - Verify: all 7 steps complete, ≥4 STOP gates hit

- [ ] **Task 3: Full workflow test — Ea (EEPROM) variant**
  - Repeat Tasks 1–2 with `memory_type: EEPROM` hardware spec
  - Verify: Ea + Eep templates used instead of Fee + Fls
  - Verify: NvM references Ea blocks, MemIf routes to Ea

- [ ] **Task 4: Knowledge update test**
  - During testing, note a new validation error pattern
  - Add pattern to `.github/skills/arxml-validation-fix/SKILL.md`
  - Commit and push
  - Start new Copilot CLI session
  - Trigger the same error
  - Verify: agent knows the fix from the updated skill
  - Verify: no redeployment or special action needed

- [ ] **Task 5: Edge case tests**
  - Single block: 1 NvM block → full workflow completes
  - Large project: 50 blocks → completes without context exhaustion
  - All ASIL-D: 5 blocks all ASIL-D → all get REDUNDANT + CRC32, safety review catches all
  - DATASET blocks: 1 block with 4 datasets → correct Fee sizing
  - Session resume: exit Copilot, `copilot --resume` → picks up where left off
  - Verify: no crashes, no context failures, no skipped steps

- [ ] **Task 6: Superpowers compatibility test**
  - Install Superpowers plugin: `copilot plugin marketplace add obra/superpowers-marketplace`
  - Run the memstack configuration workflow
  - Verify: Superpowers skills don't conflict with memstack skills
  - Verify: memstack plan format is readable by Superpowers execution skills
  - If conflicts found: document and resolve

- [ ] **Task 7: Documentation finalization**
  - Update README with tested setup instructions
  - Create `docs/user-guide.md` — step-by-step guide for engineers
  - Create `docs/knowledge-update-guide.md` — how to add new patterns to skills
  - Document known quirks from spike report and testing
  - Files: `README.md`, `docs/user-guide.md`, `docs/knowledge-update-guide.md`

#### Acceptance Criteria — Phase 1 Final Gate

| # | Criterion | Verification |
|---|-----------|-------------|
| **A5.1** | **Requirements gathering produces valid input files** | JSON validates against schemas |
| **A5.2** | **Full Fee workflow completes end-to-end** | All 7 steps, ≥4 STOP gates hit |
| **A5.3** | **Full Ea workflow completes end-to-end** | All 7 steps, correct Ea/Eep templates |
| **A5.4** | **Agent invokes requirements BEFORE configure** | Requirements skill triggers first |
| **A5.5** | **Agent follows rigid checklist with no skipped steps** | All checkboxes checked in order |
| **A5.6** | **Safety reviewer STOPs and waits for human** | Workflow pauses at ASIL gate |
| **A5.7** | **Verification checklist runs before completion** | All 9+ checks executed |
| **A5.8** | **MCP tools drive DVP without manual intervention** | validate + generate called from conversation |
| **A5.9** | **Hooks enforce ARXML pre-validation** | Malformed ARXML blocked during workflow |
| **A5.10** | **Knowledge update via git commit works** | New pattern available in next session |
| **A5.11** | **50-block project completes without context exhaustion** | No mid-workflow context failures |
| **A5.12** | **Session resume works** | `--resume` continues from last step |
| **A5.13** | **Superpowers plugin doesn't conflict** | Both skill systems coexist |
| **A5.14** | **All automated tests pass** | `pytest tests/ -v` → 0 failures |

**Quality metrics:**

| # | Metric | Target |
|---|--------|--------|
| Q5.1 | End-to-end time (5 blocks) | < 10 minutes |
| Q5.2 | End-to-end time (50 blocks) | < 20 minutes |
| Q5.3 | First-attempt ARXML accuracy | ≥ 80% blocks pass DVP validation on first import |
| Q5.4 | Validation iterations to 0 errors | ≤ 3 typical |
| Q5.5 | Human interventions (non-ASIL project) | ≤ 3 (confirm analysis + approve generation + completion) |

---

## Phase 2 — GitLab Duo Migration

### Timeline: 2 weeks (10 working days)

### Rationale

Phase 2 is a targeted migration of platform glue only. Skills content, MCP
server, scripts, templates, and tests do NOT change.

### Structure

```
Phase 2.0: Platform Spike .............. Days 1–2
Phase 2.1: Platform Adapter ............ Days 3–6
Phase 2.2: Integration Testing ......... Days 7–8
Phase 2.3: Validation & Handoff ........ Days 9–10
```

---

### Phase 2.0 — Platform Spike (Days 1–2)

#### Tasks

- [ ] **Task 1: Skill discovery on GitLab Duo**
  - Does Duo load `skills/<name>/SKILL.md`? Or `.github/skills/<name>/SKILL.md`?
  - Test with a simple spike skill
  - Record which directory path Duo discovers

- [ ] **Task 2: MCP server on GitLab Duo**
  - Does Duo connect to our stdio MCP server?
  - Test with the echo server from Phase 1.0

- [ ] **Task 3: Hook support on GitLab Duo**
  - Does Duo have `preToolUse` / `postToolUse` lifecycle hooks?
  - If not: identify the alternative enforcement mechanism
  - Options: MCP tool preconditions, CI pipeline gates, chat rules

- [ ] **Task 4: Agent delegation on GitLab Duo**
  - Does Duo delegate to custom agents?
  - If agents are UI-configured: document the setup procedure

- [ ] **Task 5: Write spike report**
  - `docs/spike-gitlab-duo.md`

#### Acceptance Criteria

| # | Criterion | Pass/Fail |
|---|-----------|-----------|
| S2.1 | Skill loads on Duo when user asks matching question | |
| S2.2 | MCP server connects via Duo | |
| S2.3 | Hooks fire OR alternative enforcement identified | |
| S2.4 | Custom agent accessible from Duo OR workaround documented | |

#### Decision Gate

- S2.1 + S2.2 pass → standard migration
- S2.3 fails → add MCP tool preconditions (scoped to missing enforcement only)
- S2.1 fails → skills loaded via instruction file or Duo knowledge integration

---

### Phase 2.1 — Platform Adapter (Days 3–6)

#### Tasks

- [ ] **Task 1: Determine skill directory strategy**
  - Based on spike: do we need dual directories, symlinks, or a shared path?
  - Implement the chosen strategy
  - Verify: skills accessible from BOTH Copilot CLI AND GitLab Duo

- [ ] **Task 2: Create GitLab Duo config files**
  - `.gitlab/duo/mcp.json` — MCP server config (Duo format)
  - `.gitlab/duo/chat-rules.md` or equivalent — chat customization
  - `AGENTS.md` already exists and should work for Duo

- [ ] **Task 3: Handle hook gap (if hooks not on Duo)**
  - If needed: add precondition checks to specific MCP tools
  - Scope: only the enforcement that hooks would provide (ARXML pre-validation, git commit before import)
  - NOT a full thick-server rewrite

- [ ] **Task 4: Verify Copilot CLI non-regression**
  - Re-run Phase 1.5 Task 2 (full Fee workflow) on Copilot CLI
  - Verify: no breakage from GitLab Duo additions

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A6.1 | Skills accessible from GitLab Duo | Test with NvM domain question |
| A6.2 | MCP server responds via Duo | `davinci_validate` succeeds |
| A6.3 | ARXML pre-validation enforced on Duo | Malformed ARXML blocked |
| A6.4 | Copilot CLI still works | Full workflow re-test passes |

---

### Phase 2.2 — Integration Testing (Days 7–8)

#### Tasks

- [ ] **Task 1: Guided advisory test on Duo**
  - Ask domain questions → verify skills load and answers are correct
- [ ] **Task 2: MCP workflow test on Duo**
  - analyze → generate → import → validate → fix → review → generate code
- [ ] **Task 3: Knowledge update test on Duo**
  - Add new error pattern, commit, new session → pattern available
- [ ] **Task 4: Document platform differences**
  - `docs/platform-differences.md`

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A7.1 | Domain questions correct on Duo | 3 per module |
| A7.2 | MCP tools callable from Duo | validate + generate succeed |
| A7.3 | Knowledge update works | New pattern in next session |
| A7.4 | Safety review requires human approval | Workflow pauses |

---

### Phase 2.3 — Validation & Handoff (Days 9–10)

#### Tasks

- [ ] **Task 1: Full workflow test on GitLab Duo** (repeat Phase 1.5 Task 2)
- [ ] **Task 2: Update README** — dual-platform instructions
- [ ] **Task 3: Document differences** — `docs/platform-differences.md`

#### Acceptance Criteria — Phase 2 Final Gate

| # | Criterion | Verification |
|---|-----------|-------------|
| **A8.1** | **Full workflow completes on GitLab Duo** | All 7 steps |
| **A8.2** | **Full workflow still completes on Copilot CLI** | Non-regression |
| **A8.3** | **Skills work on both from same repo** | No content duplication |
| **A8.4** | **MCP server works on both from same code** | No code changes |
| **A8.5** | **README covers both platforms** | Setup for each |
| **A8.6** | **All tests pass** | `pytest tests/ -v` → 0 failures |

---

## Risk Register

| Risk | Phase | Mitigation |
|------|-------|------------|
| Copilot CLI skill auto-activation unreliable for AUTOSAR terms | 1.2 | Tune descriptions; fall back to `/skill-name`; sessionStart bootstrap forces skill checking |
| Copilot CLI hook JSON format differs from expectations | 1.3 | Spike reveals format (1.0); adapt scripts before integration |
| Copilot CLI subagents lack MCP tool access | 1.4 | Main session calls MCP; subagents advisory only |
| DVP startup 15-30s per CLI call | 1.3 | Batch operations; pre-validate with Python; PAI if WF license available |
| Agent skips process skill steps | 1.2 | Rigid skill format with checklists; "DO NOT PROCEED" gates; red-flags table |
| Superpowers conflicts with memstack skills | 1.5 | Test coexistence; our skills use memstack- prefix to avoid name collisions |
| GitLab Duo has no lifecycle hooks | 2.0 | MCP tool preconditions (scoped) |
| GitLab Duo skill directory incompatible | 2.1 | Symlinks, dual dirs, or shared `.agents/skills/` path |
| Context exhaustion on 50+ block projects | 1.5 | Subagent dispatch per error group; pre-compute in Python scripts; minimal parent context |
| Knowledge update not picked up in active session | 1.2 | New session required; document as expected behavior |

---

## Final Inventory After Phase 1

```
.github/
  skills/                              ← 13 skills (4 process + 9 knowledge)
    using-memstack-skills/SKILL.md
    memstack-requirements/SKILL.md
    memstack-configure/SKILL.md
    memstack-verification/SKILL.md
    memstack-nvm/SKILL.md
    memstack-fee/SKILL.md
    memstack-ea/SKILL.md
    memstack-memif/SKILL.md
    memstack-fls-eep/SKILL.md
    arxml-generation/SKILL.md
    arxml-validation-fix/SKILL.md
    davinci-cli-reference/SKILL.md
  agents/                              ← 5 agents
    input-analyzer.agent.md
    arxml-generator.agent.md
    validation-fixer.agent.md
    safety-reviewer.agent.md
    build-verifier.agent.md
  hooks/
    memstack.json                      ← hook registration (version: 1)

hooks/                                 ← 5 hook scripts
  session-start-bootstrap.sh
  pre-arxml-write.sh
  post-arxml-write.sh
  post-generate.sh
  session-end.sh

mcp-servers/vector-davinci-mcp/        ← MCP server (unchanged)
scripts/                               ← Python pipeline (unchanged)
templates/                             ← Jinja2 ARXML (unchanged)
schemas/                               ← JSON schemas (unchanged)
tests/                                 ← Tests (unchanged, 61+ passing)
docs/                                  ← Documentation
  spike-copilot-cli.md
  user-guide.md
  knowledge-update-guide.md
  plans/                               ← Generated config plans (Superpowers-compatible)

AGENTS.md                              ← Project conventions
.mcp.json                              ← MCP server registration
README.md                              ← Copilot CLI setup instructions
```

---

## Success Metrics

### Phase 1 Exit

| Metric | Target |
|--------|--------|
| Skills on Copilot CLI | 13/13 load correctly |
| MCP tools callable | 9/9 (or 5/5 without WF) |
| Hooks enforce pre-validation | 100% — malformed files blocked |
| Bootstrap injection works | Agent checks skills before any AUTOSAR answer |
| Requirements gathered before config | Always — never skips to configure |
| Rigid checklist followed | All steps, all STOP gates |
| Safety review requires human | Always — never auto-proceeds |
| Verification runs before completion | All 9+ checks |
| Fee workflow end-to-end | < 20 min for 50 blocks |
| Ea workflow end-to-end | Completes without errors |
| Knowledge update via git | Available in next session |
| Superpowers compatible | No conflicts |
| Tests pass | 61+ / 0 failures |

### Phase 2 Exit

| Metric | Target |
|--------|--------|
| Skills on GitLab Duo | 13/13 |
| MCP on Duo | Core tools functional |
| Pre-validation enforced on Duo | 100% |
| Full workflow on Duo | End-to-end success |
| Copilot CLI non-regression | All Phase 1 criteria still met |
| Both from same repo | No duplication |
