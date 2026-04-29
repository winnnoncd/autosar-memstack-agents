# Final Implementation Plan: AUTOSAR Memory Stack Auto-Configuration
## Phase 1 — GitHub Copilot CLI · Phase 2 — GitLab Duo Migration
*Version 3 — April 2026*

---

## 0. Context and Starting Point

### 0.1 What Exists

The repository (`autosar-memstack-agents`) contains a working implementation with 51 files and 61 passing tests:

- **MCP server** (6 files) — Python stdio server wrapping DaVinci CLI + PAI with 9 tools
- **Skills** (9 files) — AUTOSAR domain knowledge as Markdown with YAML frontmatter
- **Agents** (5 files) — Subagent definitions for analyze, generate, validate, review, build
- **Hooks** (4 scripts + config) — Lifecycle hooks for ARXML validation and session persistence
- **Templates** (6 files) — Jinja2 ARXML templates for NvM, Fee, Ea, MemIf, Fls, Eep
- **Scripts** (3 files) — Python pipeline: analyze_input.py, render_arxml.py, validate_arxml.py
- **Tests** (2 files, 61 tests) — Unit + integration tests covering both Fee and Ea variants

The code is functionally correct. The problem: it's structured for Claude Code primitives.

### 0.2 What Needs to Change

The platform investigation revealed that Copilot CLI has converged on nearly identical
primitives to Claude Code — skills, agents, hooks, MCP — but with different file layout
conventions and config formats. The knowledge content (AUTOSAR rules, ARXML patterns,
error catalogs) is fully portable. Only the structural glue needs adaptation.

| Component | Current (Claude Code) | Target (Copilot CLI) | Change scope |
|---|---|---|---|
| Skills | `skills/memstack-nvm.md` | `.github/skills/memstack-nvm/SKILL.md` | Directory restructure |
| Agents | `agents/validation-fixer.md` | `.github/agents/validation-fixer.agent.md` | Frontmatter adaptation |
| Hooks | `.claude/hooks.json` | `.github/hooks/memstack.json` | JSON schema change |
| Instructions | `CLAUDE.md` | `AGENTS.md` | Rename + minor format |
| MCP config | `.mcp.json` | `.mcp.json` (same) or Copilot config | Verify compatibility |
| Scripts | `scripts/*.py` | `scripts/*.py` | No change |
| Templates | `templates/*.j2` | `templates/*.j2` | No change |
| MCP server | `mcp-servers/...` | `mcp-servers/...` | No change |
| Tests | `tests/*.py` | `tests/*.py` | No change |

### 0.3 Design Principles

1. **Skills are the knowledge layer.** All AUTOSAR domain knowledge lives in SKILL.md files
   conforming to the Agent Skills open standard. These files are platform-agnostic.

2. **MCP is the tool layer.** The DaVinci MCP server is the single integration point to
   external tooling. It works on any platform that supports MCP.

3. **Platform glue is thin and replaceable.** Agent definitions, hook configs, and instruction
   files are per-platform adapters. They reference the portable skills and MCP tools.

4. **Test against the real platform early.** Each phase begins with a spike that verifies
   the platform primitives work before investing in full migration.

---

## Phase 1 — GitHub Copilot CLI

### Timeline: 4 weeks (20 working days)

### Phase 1 Structure

```
Phase 1.0: Platform Spike (Days 1–3)
  └── Verify Copilot CLI primitives with minimal test cases

Phase 1.1: Repo Restructure (Days 4–6)
  └── Migrate file layout to Copilot CLI conventions

Phase 1.2: Skill Validation (Days 7–10)
  └── Verify all 9 skills load and activate correctly

Phase 1.3: MCP + Hook Integration (Days 11–14)
  └── DaVinci MCP server + hook enforcement on Copilot CLI

Phase 1.4: Agent Conversion (Days 15–17)
  └── Convert 5 agents to .agent.md format, verify delegation

Phase 1.5: End-to-End Validation (Days 18–20)
  └── Full workflow test with real user, acceptance sign-off
```

---

### Phase 1.0 — Platform Spike (Days 1–3)

#### Purpose
Verify that Copilot CLI's primitives work for our specific use case before committing
to full migration. This phase produces a spike report documenting what works, what doesn't,
and what needs workarounds.

#### Tasks

**Spike 1: Skill discovery.** Create a minimal skill `.github/skills/spike-test/SKILL.md`
with a simple description. Start a Copilot CLI session and ask a question matching the
description. Verify the skill is loaded into context.

**Spike 2: MCP server connection.** Create a minimal MCP server (Python, stdio) that
exposes a single echo tool. Register it in `.mcp.json`. Start Copilot CLI and ask it
to call the tool. Verify the tool is invoked and result returned.

**Spike 3: Hook execution.** Create a minimal `preToolUse` hook in `.github/hooks/spike.json`
that logs to a file. Trigger a tool use in Copilot CLI. Verify the log file is written.
Then test a blocking hook (exit code 1) and verify the tool call is denied.

**Spike 4: Agent delegation.** Create a minimal `.github/agents/spike-agent.agent.md` with
a description. Ask Copilot CLI a question that should trigger delegation. Verify a
subagent is spawned with its own context.

#### Acceptance Criteria

| # | Criterion | Pass/Fail |
|---|-----------|-----------|
| S0.1 | Skill auto-loads when user prompt matches description | |
| S0.2 | Skill loads on `/skill-name` slash command | |
| S0.3 | MCP server starts via stdio, tool listed in session | |
| S0.4 | MCP tool call succeeds, result shown in conversation | |
| S0.5 | `preToolUse` hook fires on tool invocation | |
| S0.6 | Hook returning exit 1 blocks tool execution | |
| S0.7 | Hook receives JSON stdin with `toolName` field | |
| S0.8 | Custom agent spawns as subagent with isolated context | |

#### Deliverable
Spike report: `docs/spike-copilot-cli.md` documenting results for each spike, any
platform quirks discovered, and any workarounds needed.

#### Decision gate
If S0.1, S0.3, and S0.5 all fail → STOP, reassess approach (fall back to thick MCP
server strategy). If any single spike fails, document the failure and design a
workaround before proceeding.

---

### Phase 1.1 — Repo Restructure (Days 4–6)

#### Purpose
Migrate file layout from Claude Code conventions to Copilot CLI conventions.
No content changes — only directory structure and config format.

#### Tasks

**1.1a: Restructure skills to Agent Skills standard.**

```
BEFORE:                              AFTER:
skills/memstack-nvm.md               .github/skills/memstack-nvm/SKILL.md
skills/memstack-fee.md               .github/skills/memstack-fee/SKILL.md
skills/memstack-ea.md                .github/skills/memstack-ea/SKILL.md
skills/memstack-memif.md             .github/skills/memstack-memif/SKILL.md
skills/memstack-fls-eep.md           .github/skills/memstack-fls-eep/SKILL.md
skills/arxml-generation.md           .github/skills/arxml-generation/SKILL.md
skills/arxml-validation-fix.md       .github/skills/arxml-validation-fix/SKILL.md
skills/davinci-cli-reference.md      .github/skills/davinci-cli-reference/SKILL.md
skills/memstack-configure.md         .github/skills/memstack-configure/SKILL.md
```

SKILL.md frontmatter stays the same: `name` and `description` are required fields in
both Claude Code and Copilot CLI. Remove Claude-specific fields (`agent`, `context`,
`allowed-tools`) from skills — these belong on agents, not skills, in Copilot's model.

**1.1b: Rename instruction file.**

```
BEFORE: CLAUDE.md
AFTER:  AGENTS.md
```

Content stays the same. Both Copilot CLI and GitLab Duo read `AGENTS.md`.

**1.1c: Migrate hooks config.**

```
BEFORE: .claude/hooks.json (Claude format)
AFTER:  .github/hooks/memstack.json (Copilot format with version: 1)
```

Adapt based on spike results. The hook scripts (`hooks/*.sh`) stay unchanged.
Only the registration JSON changes.

**1.1d: Verify MCP config compatibility.**

Test whether Copilot CLI reads `.mcp.json` in the same format as Claude Code.
If not, create the Copilot-compatible equivalent.

**1.1e: Update .gitignore and README.**

Remove Claude Code references. Add Copilot CLI setup instructions.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A1.1 | All 9 skills exist as `.github/skills/<name>/SKILL.md` | `find .github/skills -name SKILL.md | wc -l` = 9 |
| A1.2 | No Claude-specific frontmatter in SKILL.md files | `grep -r "agent:\|context:\|allowed-tools:" .github/skills/` returns nothing |
| A1.3 | `AGENTS.md` exists at repo root, `CLAUDE.md` removed | `ls AGENTS.md && ! ls CLAUDE.md` |
| A1.4 | Hook config at `.github/hooks/memstack.json` is valid JSON | `python -m json.tool .github/hooks/memstack.json` succeeds |
| A1.5 | MCP config is loadable by Copilot CLI | Copilot CLI session shows DaVinci tools listed |
| A1.6 | All 61 existing tests still pass | `pytest tests/ -v` → 0 failures |
| A1.7 | No files remain in `.claude/` directory | `! test -d .claude` |

---

### Phase 1.2 — Skill Validation (Days 7–10)

#### Purpose
Verify that all 9 skills load correctly on Copilot CLI, activate on the right prompts,
and provide useful guidance when loaded.

#### Tasks

**1.2a: Test auto-activation for each skill.** For each skill, submit a prompt to Copilot
CLI that should trigger it based on the `description` field. Verify the skill content
appears in the model's response (demonstrates it was loaded into context).

Test prompts:
- `memstack-nvm`: "How should I configure NvM for a 64-byte ASIL-D block?"
- `memstack-fee`: "What sector layout do I need for Fee with 8KB flash sectors?"
- `memstack-ea`: "How do I configure Ea for an external I2C EEPROM?"
- `memstack-memif`: "How does MemIf route requests between Fee and Ea?"
- `memstack-fls-eep`: "What Fls parameters do I need for S32K internal flash?"
- `arxml-generation`: "What's the correct ARXML structure for an ECUC module config?"
- `arxml-validation-fix`: "DVP validation says FeeBlockSize is too small. How do I fix it?"
- `davinci-cli-reference`: "What CLI command runs DaVinci validation?"
- `memstack-configure`: "Configure the full memory stack for my project."

**1.2b: Test slash command invocation.** Verify `/memstack-nvm`, `/memstack-fee`, etc.
load the skill explicitly.

**1.2c: Test knowledge accuracy.** For each skill, ask 3 domain-specific questions
and verify the answers are correct against the skill content:
- NvM: "What block ID does the first user block get?" → 2
- NvM: "What's the Fee block number formula?" → NvMNvBlockNum × 2
- Fee: "What's the minimum sector count for Fee?" → 2 (recommended 3)
- Fee: "How do I calculate FeeBlockSize?" → NvMBlockLength + 16 + CRC + alignment

**1.2d: Tune descriptions if needed.** If any skill fails to auto-activate, revise
the `description` field for better keyword coverage. Re-test.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A2.1 | All 9 skills auto-activate on their test prompts | Manual test, 9/9 pass |
| A2.2 | All 9 skills load on `/skill-name` invocation | Manual test, 9/9 pass |
| A2.3 | NvM skill: block ID = 2, Fee formula correct | 3/3 knowledge questions correct |
| A2.4 | Fee skill: sector count, block size formula correct | 3/3 knowledge questions correct |
| A2.5 | Validation fix skill: correctly categorizes a Fee size error as PARAM_ADJUST | Confirm fix category in response |
| A2.6 | No skill loads when asking an unrelated question ("What's the weather?") | Manual test, no spurious activation |

---

### Phase 1.3 — MCP + Hook Integration (Days 11–14)

#### Purpose
Connect the DaVinci MCP server to Copilot CLI and verify all 9 MCP tools work.
Verify hooks enforce ARXML pre-validation and session persistence.

#### Tasks

**1.3a: MCP server registration and startup.** Configure `.mcp.json` (or Copilot
equivalent) to start the DaVinci MCP server. Start Copilot CLI session. Verify all 9
tools appear in the tool list.

**1.3b: Test MCP tools against real DVP.** For each tool that doesn't require WF license:
- `davinci_open_project` → opens sample .dpa, returns success
- `davinci_import_arxml` → imports a test ARXML, exit 0
- `davinci_validate` → returns structured error list
- `davinci_generate` → triggers generation, returns file list
- `davinci_export_arxml` → exports to file

**1.3c: Test MCP tools via PAI (if WF license available):**
- `davinci_get_parameter` → reads NvMBlockLength for a known block
- `davinci_set_parameter` → sets NvMBlockLength, mini-validates
- `davinci_batch_set` → sets 5 params in one session

**1.3d: Adapt hook scripts for Copilot CLI's JSON input format.**

Copilot CLI hooks receive JSON via stdin:
```json
{"timestamp": 1704614400000, "cwd": "/path", "toolName": "edit", "toolArgs": "..."}
```

Our current hook scripts expect file paths as arguments. Adapt them to:
1. Read JSON from stdin
2. Extract `toolName` and `toolArgs`
3. Determine if the operation involves `.arxml` files
4. Run the Python pre-validation if so

**1.3e: Test hook enforcement.**
- Create a malformed ARXML file. Ask Copilot to import it.
- Verify `preToolUse` hook fires, detects malformation, blocks the import.
- Create a valid ARXML file. Ask Copilot to import it.
- Verify hook passes, import proceeds.

**1.3f: Test session-end hook.** End a Copilot CLI session. Verify `AGENTS.md`
has a new session log entry appended.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A3.1 | MCP server starts, all 9 tools listed in Copilot session | `copilot` session, verify tool list |
| A3.2 | `davinci_validate()` returns structured errors from real .dpa | ≥1 error parsed with module + severity |
| A3.3 | `davinci_import_arxml()` imports valid ARXML, exit 0 | DVP exit code 0, no error in response |
| A3.4 | `davinci_generate()` triggers code gen, returns file list | ≥1 generated .c file |
| A3.5 | `preToolUse` hook blocks malformed ARXML write | Tool call denied, error message shown |
| A3.6 | `preToolUse` hook allows valid ARXML write | Tool call proceeds |
| A3.7 | `sessionEnd` hook writes log entry to AGENTS.md | `tail -5 AGENTS.md` shows new entry |
| A3.8 | All hook scripts handle Copilot CLI's JSON stdin format | No parse errors in hook execution |

**Quality criteria:**

| # | Metric | Target |
|---|--------|--------|
| Q3.1 | MCP tool round-trip time (validate) | < 60s |
| Q3.2 | Validation error parsing accuracy | 100% of ERROR entries captured |
| Q3.3 | Hook false positive rate | 0% (never blocks valid ARXML) |

---

### Phase 1.4 — Agent Conversion (Days 15–17)

#### Purpose
Convert the 5 agent definitions from Claude Code format to Copilot CLI `.agent.md`
format. Verify delegation, subagent spawning, and tool access.

#### Tasks

**1.4a: Convert agent frontmatter.**

Claude Code format:
```yaml
---
name: validation-fixer
description: Runs the DVP validation → parse → fix → re-validate loop.
agent: general-purpose
context: fork
allowed-tools: mcp__davinci__*, Bash(python:*), Bash(git:*)
skills: [arxml-validation-fix, davinci-cli-reference]
---
```

Copilot CLI format (`.agent.md`):
```yaml
---
name: validation-fixer
description: Runs the DVP validation → parse → fix → re-validate loop.
  Implements the evaluator-optimizer workflow pattern.
  Max 5 iterations before escalating to human.
tools: ['mcp__davinci__davinci_validate', 'mcp__davinci__davinci_import_arxml',
        'bash', 'edit', 'view']
---
```

Key differences to handle:
- `agent` and `context: fork` → Copilot manages subagent spawning based on `description`
- `allowed-tools` → `tools` (Copilot format, list of tool names)
- `skills` → reference in body text or let Copilot auto-activate based on prompt
- File extension: `.md` → `.agent.md`
- Location: `agents/` → `.github/agents/`

**1.4b: Convert all 5 agents.**

| Agent | File |
|---|---|
| input-analyzer | `.github/agents/input-analyzer.agent.md` |
| arxml-generator | `.github/agents/arxml-generator.agent.md` |
| validation-fixer | `.github/agents/validation-fixer.agent.md` |
| safety-reviewer | `.github/agents/safety-reviewer.agent.md` |
| build-verifier | `.github/agents/build-verifier.agent.md` |

**1.4c: Test agent delegation.** For each agent, submit a prompt that should trigger
delegation. Verify Copilot spawns a subagent (visible in CLI output).

**1.4d: Test agent MCP access.** Verify that the validation-fixer agent, when spawned
as a subagent, can call DaVinci MCP tools.

**1.4e: Test safety-reviewer stops for human approval.** Submit a prompt that triggers
the safety-reviewer agent with ASIL-D blocks. Verify the agent presents a review table
and does NOT auto-proceed to code generation.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A4.1 | All 5 agents exist as `.github/agents/*.agent.md` | `ls .github/agents/*.agent.md | wc -l` = 5 |
| A4.2 | No Claude-specific frontmatter (`context: fork`, `agent:`) | `grep -r "context:\|^agent:" .github/agents/` returns nothing |
| A4.3 | Copilot delegates to input-analyzer on "analyze my memstack input" | Subagent spawned visible in CLI |
| A4.4 | Copilot delegates to validation-fixer on "fix these DVP validation errors" | Subagent spawned visible in CLI |
| A4.5 | Subagent can call DaVinci MCP tools | validation-fixer calls `davinci_validate` successfully |
| A4.6 | safety-reviewer presents review table and waits for human | Manual test: workflow pauses at review |
| A4.7 | `/agent` command lists all 5 custom agents | Copilot CLI interactive, `/agent` shows list |

---

### Phase 1.5 — End-to-End Validation (Days 18–20)

#### Purpose
Run the full interactive workflow on Copilot CLI with a real user and a real DaVinci
project. Verify the harness guides users effectively. Sign off on Phase 1 completion.

#### Tasks

**1.5a: Full workflow test (Fee variant).** One engineer runs the complete workflow
on Copilot CLI against a real .dpa project with MICROSAR SIP:

```
1. Ask about configuring NvM for a crash recorder block (skill activation)
2. Provide memstack_input.json with 5 blocks (input analysis)
3. Request ARXML generation (template rendering + pre-validation)
4. Request DVP import + validation (MCP tool call)
5. Ask to fix validation errors (validation-fixer agent)
6. Review ASIL safety table (safety-reviewer agent, human gate)
7. Approve code generation (MCP tool call)
8. Check build result (build-verifier agent)
```

**1.5b: Full workflow test (Ea variant).** Repeat with `memory_type: EEPROM` input.

**1.5c: Knowledge update test.** During the test, encounter a new validation error
pattern. Have the engineer add it to the validation fix skill. Start a new session.
Verify the updated knowledge is available.

**1.5d: Edge case tests on Copilot CLI.**
- Single block configuration
- 50+ blocks (context pressure)
- All-ASIL-D blocks (safety review completeness)
- Session resume after `/compact` or context compaction
- Session resume after explicit exit and `--resume`

**1.5e: Documentation finalization.** Update README with Copilot CLI-specific
setup instructions, tested model recommendations, known quirks.

#### Acceptance Criteria — Phase 1 Final Gate

| # | Criterion | Verification |
|---|-----------|-------------|
| **A5.1** | **Full Fee workflow completes end-to-end on Copilot CLI** | Engineer runs all 8 steps, 0 blocking failures |
| **A5.2** | **Full Ea workflow completes end-to-end on Copilot CLI** | Engineer runs all 8 steps, 0 blocking failures |
| **A5.3** | **Skills provide correct guidance on domain questions** | 3 domain questions per module, all correct |
| **A5.4** | **MCP tools drive DVP operations without manual intervention** | validate + generate called from conversation |
| **A5.5** | **Hooks enforce ARXML pre-validation** | Malformed ARXML blocked by hook during workflow |
| **A5.6** | **Safety reviewer stops for human approval on ASIL blocks** | Workflow pauses, engineer must explicitly approve |
| **A5.7** | **Knowledge update flows through git → new session** | New error pattern added, available in next session |
| **A5.8** | **50-block project completes without context exhaustion** | No mid-workflow context failures |
| **A5.9** | **Session resume works after exit** | `--resume` picks up where previous session ended |
| **A5.10** | **All 61 automated tests still pass** | `pytest tests/ -v` → 0 failures |

**Quality metrics:**

| # | Metric | Target |
|---|--------|--------|
| Q5.1 | End-to-end time (5 blocks, Fee) | < 10 minutes |
| Q5.2 | End-to-end time (50 blocks, Fee) | < 20 minutes |
| Q5.3 | First-attempt ARXML accuracy | ≥ 80% blocks pass validation on first import |
| Q5.4 | Validation iterations to 0 errors | ≤ 3 typical |
| Q5.5 | Human interventions (non-ASIL project) | ≤ 2 (safety gate + generation approval) |

---

## Phase 2 — GitLab Duo Migration

### Timeline: 2 weeks (10 working days), starts when GitLab Duo transition begins

### Phase 2 Rationale

Phase 2 is NOT a redesign. It is a targeted migration of the platform glue layer
from Copilot CLI conventions to GitLab Duo conventions. The portable components
(skills content, MCP server, scripts, templates, tests) do not change.

### Phase 2 Structure

```
Phase 2.0: Platform Spike (Days 1–2)
  └── Verify GitLab Duo primitives with same spike tests as Phase 1.0

Phase 2.1: Platform Adapter (Days 3–6)
  └── Create GitLab Duo config alongside Copilot CLI config

Phase 2.2: Integration Testing (Days 7–8)
  └── MCP server + skill loading + workflow test on Duo

Phase 2.3: Validation & Handoff (Days 9–10)
  └── End-to-end test, documentation, dual-platform README
```

---

### Phase 2.0 — Platform Spike (Days 1–2)

#### Purpose
Repeat the same 4 spike tests from Phase 1.0 on GitLab Duo. The spike report
will identify what works identically, what needs adaptation, and what's missing.

#### Tasks

Same 4 spikes as Phase 1.0, targeting GitLab Duo CLI:
1. Skill discovery — does Duo load `skills/<name>/SKILL.md`?
2. MCP server connection — does Duo connect to our stdio MCP server?
3. Hook execution — does Duo have lifecycle hooks? If not, what's the alternative?
4. Agent delegation — does Duo delegate to custom agents from chat?

#### Acceptance Criteria

| # | Criterion | Pass/Fail |
|---|-----------|-----------|
| S2.1 | Skill loads on Duo Chat when user asks matching question | |
| S2.2 | MCP server connects via Duo's MCP client | |
| S2.3 | Hooks fire (or: alternative enforcement mechanism identified) | |
| S2.4 | Custom agent accessible from Duo Chat | |

#### Decision gate
- If S2.1 and S2.2 pass → proceed with standard migration
- If S2.3 fails (no hooks) → hook enforcement moves into MCP server preconditions
  (the thick-server fallback, scoped to only the missing enforcement)
- If S2.1 fails → skills must be loaded via different mechanism (instruction files,
  explicit prompt injection, or Duo's knowledge graph)

#### Deliverable
Spike report: `docs/spike-gitlab-duo.md`

---

### Phase 2.1 — Platform Adapter (Days 3–6)

#### Purpose
Create GitLab Duo configuration files alongside existing Copilot CLI config.
Both platforms work from the same repo — the adapter layer is additive, not replacing.

#### Tasks

**2.1a: Determine skill directory strategy.**

GitLab Duo expects `skills/<name>/SKILL.md`. Copilot CLI expects
`.github/skills/<name>/SKILL.md`. Two options:

- Option A: Symlinks — `skills/` contains the originals, `.github/skills/` contains
  symlinks. Works on Linux/macOS, fragile on Windows.
- Option B: Dual directories — skills exist in both locations. Use a script or
  CI step to sync. More robust but requires sync discipline.
- Option C: Use `.agents/skills/` — both platforms may support this shared path
  (needs spike confirmation).

Decision based on spike report.

**2.1b: Create GitLab Duo config files.**

```
.gitlab/duo/
  ├── mcp.json                    # MCP server config (GitLab format)
  └── chat-rules.md               # Chat customization rules
```

**2.1c: Create GitLab custom agent (if needed).**

GitLab Duo custom agents are configured via the GitLab UI (not file-based like
Copilot CLI). If the safety-reviewer agent needs to be a GitLab custom agent,
create it through the AI Catalog and document the setup steps.

Alternatively, if GitLab Duo's AGENTS.md + skills + MCP is sufficient for the
interactive workflow without explicit custom agents, skip this step.

**2.1d: Handle hook gap (if hooks not available on Duo).**

If the spike reveals GitLab Duo lacks lifecycle hooks, add precondition logic to
the MCP server's Tier 1 tools:

```python
# In memstack_validate() MCP tool:
def memstack_validate(arxml_paths):
    # Hook equivalent: pre-validate before DVP import
    for path in arxml_paths:
        errors = validate_arxml(path)
        if errors:
            return {"status": "blocked", "reason": "Pre-validation failed", "errors": errors}

    # Hook equivalent: git commit before DVP import
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", "pre-dvp-import"])

    # Actual DVP operation
    return cli.import_and_validate(arxml_paths)
```

This is scoped strictly to the missing enforcement — NOT a full thick-server rewrite.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A6.1 | Skills accessible from GitLab Duo Chat | Test with NvM domain question |
| A6.2 | MCP server connects and responds via GitLab Duo | `davinci_validate` call succeeds |
| A6.3 | ARXML pre-validation enforced (hook or MCP precondition) | Malformed ARXML blocked |
| A6.4 | AGENTS.md read by GitLab Duo at session start | Session behavior reflects project conventions |
| A6.5 | Copilot CLI config still works (no regression) | Re-run Phase 1.5 A5.1 on Copilot |

---

### Phase 2.2 — Integration Testing (Days 7–8)

#### Purpose
Run the interactive workflow on GitLab Duo to verify functional parity with
Copilot CLI.

#### Tasks

**2.2a: Guided advisory test.** Ask Duo Chat domain questions about NvM, Fee, etc.
Verify skills load and provide correct answers.

**2.2b: MCP workflow test.** Execute: analyze → generate ARXML → import → validate →
fix errors → review → generate code. Verify each step completes.

**2.2c: Knowledge update test.** Add a new error pattern to the validation fix skill,
commit, start new session. Verify Duo has the updated knowledge.

**2.2d: Compare Duo vs Copilot CLI experience.** Document any behavioral differences
in skill activation timing, MCP tool presentation, context management.

#### Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| A7.1 | Domain questions answered correctly on Duo | 3 questions per module, all correct |
| A7.2 | DaVinci MCP tools callable from Duo Chat | validate + generate succeed |
| A7.3 | ARXML pre-validation enforced on Duo | Malformed file blocked |
| A7.4 | Knowledge update available in new session | New pattern in next conversation |
| A7.5 | Safety-critical review requires human approval | Workflow pauses for ASIL blocks |

---

### Phase 2.3 — Validation & Handoff (Days 9–10)

#### Purpose
Final sign-off on dual-platform support. Documentation for both platforms.

#### Tasks

**2.3a: End-to-end test on GitLab Duo.** Repeat Phase 1.5's full workflow test
(5-block Fee variant) on Duo.

**2.3b: Update README with dual-platform instructions.** Setup sections for both
Copilot CLI and GitLab Duo, clearly labeled.

**2.3c: Document known differences.** Create `docs/platform-differences.md` listing
any behavioral differences between the two platforms and their workarounds.

#### Acceptance Criteria — Phase 2 Final Gate

| # | Criterion | Verification |
|---|-----------|-------------|
| **A8.1** | **Full workflow completes on GitLab Duo** | Engineer runs 8-step workflow |
| **A8.2** | **Full workflow still completes on Copilot CLI** | Re-run Phase 1.5 A5.1 |
| **A8.3** | **Skills work on both platforms from same repo** | Same skill content, no duplication |
| **A8.4** | **MCP server works on both platforms from same code** | No code changes between platforms |
| **A8.5** | **README covers both platforms** | Setup instructions for each |
| **A8.6** | **All 61 automated tests still pass** | `pytest tests/ -v` → 0 failures |

---

## Risk Register

| Risk | Phase | Impact | Mitigation |
|------|-------|--------|------------|
| Copilot CLI skill auto-activation unreliable for AUTOSAR terminology | 1.2 | Skills don't load when needed | Tune description keywords; fall back to explicit `/skill-name` invocation |
| Copilot CLI hook JSON input format differs from expectations | 1.3 | Hook scripts fail to parse input | Spike reveals format (Phase 1.0); adapt scripts before integration |
| Copilot CLI subagent doesn't have MCP tool access | 1.4 | Agents can't drive DVP | Fall back to main session calling MCP tools directly, agents as advisory only |
| DVP startup time 15-30s per CLI call on Copilot | 1.3 | Slow validation loop | Batch operations; pre-validate with Python; PAI persistent session if WF license available |
| GitLab Duo has no lifecycle hooks | 2.0 | No deterministic enforcement | Move enforcement into MCP server preconditions (scoped, not full redesign) |
| GitLab Duo skill directory location incompatible | 2.1 | Skills not discovered | Symlinks, dual directories, or `.agents/skills/` shared path |
| GitLab Duo custom agents require UI configuration | 2.1 | Can't define agents in repo files alone | Document UI setup steps; accept that agent definitions are platform-managed on Duo |
| Knowledge update not picked up in active session | 1.2, 2.2 | Stale knowledge after git push | Start new session after knowledge commits; document this as expected behavior |

---

## What's Not Included (Deferred to Post-Phase 2)

The following items from the previous plan revisions are deferred until both platforms
are stable:

- **Track A: BSW Stack Expansion** (Com, Os, Dcm modules) — add new skills/templates
  per module following the established pattern. 3-5 days per module.
- **Track B: PAI Persistent Session** — zero-startup DVP access via persistent Groovy
  process. Depends on WF license availability.
- **Track C: Governance** — audit trail, cost attribution, guardrail engine. Implement
  when the framework is deployed to multiple teams.
- **Agent Teams / Parallel Review** — run safety-reviewer and build-verifier concurrently.
  Depends on Copilot CLI's `/fleet` maturity and Duo's flow orchestration.
- **Cross-Session Memory** — structured layered memory beyond AGENTS.md session log.
  Copilot CLI has "Copilot Memory" feature that may cover this natively.

These are all additive — they don't require architectural changes to the framework
established in Phases 1 and 2.

---

## Success Metrics Summary

### Phase 1 Exit Criteria

| Metric | Target |
|--------|--------|
| All 9 skills load on Copilot CLI | 9/9 |
| All MCP tools callable from Copilot CLI | 9/9 (or 5/5 without WF license) |
| Hooks enforce ARXML pre-validation | 100% — malformed files blocked |
| Full Fee workflow end-to-end | Completes in < 20 min for 50 blocks |
| Full Ea workflow end-to-end | Completes without errors |
| Safety review requires human approval | Always — never auto-proceeds |
| Knowledge update via git commit | Available in next session |
| Automated tests pass | 61/61 |

### Phase 2 Exit Criteria

| Metric | Target |
|--------|--------|
| Skills accessible on GitLab Duo | 9/9 |
| MCP server works on GitLab Duo | Core tools functional |
| ARXML pre-validation enforced on Duo | 100% |
| Full workflow completes on Duo | End-to-end success |
| Copilot CLI still works (no regression) | All Phase 1 criteria still met |
| Both platforms from same repo | No skill content duplication |
