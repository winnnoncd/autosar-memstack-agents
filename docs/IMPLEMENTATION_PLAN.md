# Revised Implementation Plan: AUTOSAR Memory Stack Auto-Configuration
## Claude Code Harness — Skills · Agents · Workflows · MCP
*Revision 2 — April 2026*

---

## 0. Scope & Goal

**Objective:** Build a Claude Code harness that automatically configures the AUTOSAR Classic Memory Stack (NvM → MemIf → Fee/Fls or Ea/Eep) in DaVinci Configurator, from input artifacts through validated code generation.

**End state (MVP):** A single slash command `/configure-memstack` that reads input artifacts, generates ARXML for all memory stack modules, imports into DaVinci, validates, auto-fixes errors, generates BSW code, and produces a delta report — with human approval gates at safety-critical decision points.

**Design principle:** The model reasons; the harness governs. Every phase builds infrastructure that constrains the AI's action space while amplifying its productive capability. This is not prompt engineering — it is systems engineering around a language model.

---

## 1. Phase Structure Overview

The project is structured as 6 MVP phases followed by 3 post-MVP evolution tracks. Each phase has explicit success criteria organized in three tiers:

- **Gate criteria** — must pass to proceed to next phase (binary go/no-go)
- **Quality criteria** — measured metrics that indicate readiness for production use
- **Stretch goals** — improvements that are nice-to-have but not blocking

```
┌─────────────────────────────────────────────────────────────┐
│                      MVP (4 weeks)                          │
│                                                             │
│  Phase 1: MCP Server ──┐                                   │
│  Phase 2: Skills       ├── can overlap (Days 3–10)         │
│  Phase 3: Agents       ┘                                   │
│  Phase 4: Hooks & Templates                                │
│  Phase 5: Orchestration & CLAUDE.md                        │
│  Phase 6: Integration Testing & Hardening                  │
│                                                             │
│  ─── MVP GATE ─── (all 6 phase gates must pass)           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                   Post-MVP Tracks                           │
│                                                             │
│  Track A: Stack Expansion (Com, Os, Dcm, CanIf, PduR)     │
│  Track B: Harness Deepening (Agent Teams, PAI persistent)  │
│  Track C: Governance & Observability                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1 — MCP Server (Days 1–5)

### 2.1 What We Build

The MCP server is the critical path. Without it, Claude cannot drive DaVinci. This phase delivers the Python stdio server wrapping DaVinci CLI + PAI, with structured error parsing.

Components:
- `server.py` — MCP server main, 9 tools registered
- `cli_wrapper.py` — DaVinciCFG.exe subprocess interface
- `validation_parser.py` — XML/HTML/text report parser (3-level fallback)
- `pai_bridge.py` — Groovy script invoker for parameter-level access
- 4 Groovy templates: get_parameter, set_parameter, batch_set, query_blocks
- `.mcp.json` — server registration for Claude Code

### 2.2 Success Criteria

**Gate criteria (must pass to proceed):**

| # | Criterion | Verification |
|---|-----------|-------------|
| G1.1 | `davinci_validate()` returns structured error list from a real .dpa project | Run against sample project, get ≥1 error parsed with module + severity + message |
| G1.2 | `davinci_import_arxml()` imports a valid ARXML fragment without error | Import a hand-crafted NvM ARXML, DVP exit code 0 |
| G1.3 | `davinci_generate()` triggers code generation and returns file list | Run on sample project, get ≥1 generated .c file in output |
| G1.4 | Validation parser handles all 3 fallback levels (XML → HTML → stdout) | Unit tests pass for each parser path with synthetic reports |
| G1.5 | MCP server starts via stdio and responds to `list_tools` | `claude --mcp-debug` shows 9 tools registered |

**Quality criteria (measured metrics):**

| # | Metric | Target | How to measure |
|---|--------|--------|----------------|
| Q1.1 | CLI round-trip time (import + validate) | < 60s for 50-block project | Time from MCP call to structured response |
| Q1.2 | Validation error parsing accuracy | 100% of ERROR-severity entries captured | Compare parser output to DVP GUI count |
| Q1.3 | Error categorization accuracy | ≥ 80% correctly categorized (AUTO_FIX vs ESCALATE etc.) | Manual review of 20 sample errors |

**Stretch goals:**

| # | Goal | Value |
|---|------|-------|
| S1.1 | `davinci_get_parameter()` reads a value via PAI | Proves WF license works, enables Phase 3 fixer agent to use PAI path |
| S1.2 | `davinci_batch_set()` sets 10 params in one DVP session | Proves persistent-session performance advantage |

### 2.3 Key Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| DVP validation report XML schema is undocumented — parser misses fields | Built 3-level fallback (XML → HTML → regex). If XML schema changes, HTML parsing still works. Request schema from Vector support as parallel track. |
| DVP startup 15–30s per CLI call compounds in validation loop | Phase 1 measures actual startup time. If >20s, Phase 3 will batch all patches before a single re-validate instead of per-patch validation. PAI stretch goal (S1.1) eliminates startup if WF license is available. |
| Option WF license not available | PAI bridge is stretch goal only. All gate criteria use CLI-only path. PAI is additive, never required. |

---

## 3. Phase 2 — Skills (Days 3–10, overlapping with Phase 1)

### 3.1 What We Build

9 skill files encoding domain knowledge that makes ARXML generation accurate on first attempt. Each skill is a Markdown file with structured parameter rules, cross-module formulas, and a validation error → fix pattern catalog.

Skills:
- `memstack-configure.md` — master orchestration (slash command)
- `memstack-nvm.md` — NvM block types, ID rules, CRC, priorities
- `memstack-fee.md` — Fee sector layout, block sizing, wear leveling
- `memstack-ea.md` — Ea variant for EEPROM
- `memstack-memif.md` — MemIf device routing
- `memstack-fls-eep.md` — Fls/Eep MCAL driver params
- `arxml-generation.md` — AUTOSAR R4.x ARXML authoring rules
- `arxml-validation-fix.md` — error pattern → fix strategy catalog
- `davinci-cli-reference.md` — DaVinci CLI/PAI quick reference

### 3.2 Success Criteria

**Gate criteria:**

| # | Criterion | Verification |
|---|-----------|-------------|
| G2.1 | NvM skill contains block ID assignment rules that produce correct consecutive IDs starting at 2 | Unit test: analyze 50 blocks, verify IDs = [2, 3, ..., 51] |
| G2.2 | Fee skill contains Fee block number formula that matches NvM cross-reference | Unit test: for each block, FeeBlockNumber = NvMNvBlockNum × 2 |
| G2.3 | Fee skill contains FeeBlockSize formula that accounts for header (16B) + CRC + page alignment | Unit test: FeeBlockSize ≥ NvMBlockLength + 16 + CRC_overhead, and FeeBlockSize % page_size == 0 |
| G2.4 | Validation fix catalog covers all 5 categories (AUTO_FIX, PARAM_ADJUST, MISSING_REF, STRUCTURAL, ESCALATE) | Grep catalog, ≥2 patterns per category |
| G2.5 | ASIL rules encoded: ASIL ≥ B → REDUNDANT + CRC mandatory | Unit test: ASIL_D block auto-upgraded to REDUNDANT with CRC32 |
| G2.6 | arxml-generation skill defines bottom-up generation order: Fls → Fee → MemIf → NvM | Inspect skill, verify order documented and rationale stated |

**Quality criteria:**

| # | Metric | Target | How to measure |
|---|--------|--------|----------------|
| Q2.1 | First-attempt ARXML accuracy | ≥ 80% of blocks pass DVP validation on first import | Run 50-block test, count blocks with 0 errors after first import |
| Q2.2 | Validation fix coverage | ≥ 90% of memory-stack DVP errors have a matching fix pattern | Collect error set from 3 real projects, match against catalog |
| Q2.3 | Skill context cost | Each module skill < 2000 tokens when loaded | Measure with `tiktoken` |

**Stretch goals:**

| # | Goal | Value |
|---|------|-------|
| S2.1 | Validation fix catalog reaches 30+ patterns | Higher first-pass accuracy, fewer validation iterations |
| S2.2 | Skills parameterized by MICROSAR SIP version | Handles SIP differences without manual template editing |

### 3.3 Skill Evolution Strategy (Post-MVP)

Skills are the easiest harness component to extend. Post-MVP growth follows two axes:

**Depth axis** — enrich existing module skills with more parameter patterns, more error→fix mappings, and OEM-specific deviation rules. Each real-project deployment will surface new patterns that get folded back into the skill. Target: validation fix catalog grows from ~20 patterns (MVP) to 100+ patterns within 3 months.

**Breadth axis** — add skills for new BSW modules (see Track A in Post-MVP section). Each new module follows the same template: parameter rules + cross-module formulas + error catalog. The `memstack-nvm.md` skill serves as the pattern for all future module skills.

**Measurement:** Track "first-attempt accuracy" per module over time. Each skill revision should monotonically improve this metric. If accuracy drops after a revision, the revision introduced a regression — roll back.

---

## 4. Phase 3 — Agents (Days 8–15)

### 4.1 What We Build

5 subagent definitions, each a Markdown file with frontmatter specifying role, tools, context mode, and skills to load.

Agents:
- `input-analyzer.md` — Explore agent, reads inputs, computes derived params
- `arxml-generator.md` — Plan agent, renders Jinja2 templates bottom-up
- `validation-fixer.md` — general-purpose agent, evaluator-optimizer loop (max 5 iterations)
- `safety-reviewer.md` — Plan agent, ASIL compliance check, hard human gate
- `build-verifier.md` — Bash agent, compile + MISRA check

### 4.2 Success Criteria

**Gate criteria:**

| # | Criterion | Verification |
|---|-----------|-------------|
| G3.1 | Input analyzer produces correct `analysis.json` for the 5-block sample fixture | `analyze_input.py` output matches expected block IDs, Fee numbers, budget, ASIL flags |
| G3.2 | ARXML generator produces 4 well-formed ARXML files (Fls, Fee, MemIf, NvM) from analysis.json | `validate_arxml.py` returns 0 errors for all 4 files |
| G3.3 | Validation fixer reduces error count across iterations | Start with ≥5 synthetic errors, fixer produces patches, error count decreases each iteration |
| G3.4 | Safety reviewer identifies all ASIL-non-compliant blocks | Inject a block with ASIL_D + NATIVE (no redundancy) → reviewer flags it |
| G3.5 | Safety reviewer STOPS and waits for human — never auto-proceeds | Code review confirms no auto-approval path exists |
| G3.6 | All agents run in forked context and return summary only | Verify `context: fork` in each agent definition; parent receives summary, not full child history |

**Quality criteria:**

| # | Metric | Target | How to measure |
|---|--------|--------|----------------|
| Q3.1 | Validation iterations to 0 errors (50-block project) | ≤ 3 typical, ≤ 5 max | Count iterations in fixer agent log |
| Q3.2 | Fixer auto-fix rate | ≥ 70% of errors resolved without ESCALATE | Count AUTO_FIX + PARAM_ADJUST + MISSING_REF vs ESCALATE |
| Q3.3 | Input analyzer handles edge cases | 0 crashes on: single block, 200 blocks, 0-size block (error), all-ASIL_D blocks | Run edge case test suite |
| Q3.4 | Safety review completeness | 100% of ASIL ≥ B blocks appear in review table | Compare review output to ASIL flags in analysis.json |

**Stretch goals:**

| # | Goal | Value |
|---|------|-------|
| S3.1 | Fixer agent uses PAI for single-parameter fixes when WF license available | Faster fix cycle (no ARXML roundtrip for simple value changes) |
| S3.2 | Fixer agent implements cascading error deduplication | Group by root container, fix root cause first — reduces wasted iterations |

### 4.3 Agent Evolution Strategy (Post-MVP)

**From subagents to Agent Teams:** The MVP uses a tree architecture (parent → child → parent). Post-MVP, the safety-reviewer and build-verifier can run as Agent Team teammates in parallel, communicating via JSON inboxes. This shaves ~30% off the review phase wall-clock time. Prerequisites: Claude Code v2.1.19+ for Agent Teams, tmux for terminal visibility.

**Specialist decomposition:** As BSW module coverage expands (Track A), the monolithic validation-fixer agent will need to split into per-module fixer specialists. Each specialist loads only its module's skill and handles errors for that module. The orchestrator routes errors to the correct specialist. This follows the routing workflow pattern from the SotA research.

**Cross-model review:** Following the `metaswarm` pattern, a post-MVP adversarial review step can use a different model (e.g., haiku for fast scan, opus for deep review) to review ARXML generated by the primary model. The writer and reviewer are always different model instances — never self-reviewing.

---

## 5. Phase 4 — Hooks & Templates (Days 12–15)

### 5.1 What We Build

Hooks:
- `pre-arxml-write.sh` — PreToolUse: validates ARXML before writing (blocks malformed files)
- `post-arxml-write.sh` — PostToolUse: quick well-formedness check after edit
- `post-generate.sh` — PostToolUse: compile smoke test on generated code
- `session-end.sh` — SessionEnd: writes progress delta to CLAUDE.md
- `.claude/hooks.json` — hook registration config

Templates:
- 6 Jinja2 ARXML templates: NvM, Fee, Ea, MemIf, Fls, Eep

Scripts:
- `validate_arxml.py` — pre-DVP ARXML validation (lxml)
- `analyze_input.py` — input analysis + derived parameter computation
- `render_arxml.py` — template rendering engine

### 5.2 Success Criteria

**Gate criteria:**

| # | Criterion | Verification |
|---|-----------|-------------|
| G4.1 | Pre-ARXML hook blocks a malformed XML file with exit code 1 | Feed it `<AUTOSAR><unclosed>`, verify BLOCK in stderr |
| G4.2 | Pre-ARXML hook blocks duplicate SHORT-NAMEs | Feed it ARXML with 2 `<AR-PACKAGE><SHORT-NAME>Dupe</SHORT-NAME>`, verify BLOCK |
| G4.3 | Session-end hook writes timestamp + block count + validation status to CLAUDE.md | Run hook, verify CLAUDE.md has new `### Session` entry |
| G4.4 | NvM template renders 50 blocks with correct IDs, CRC, references | Render + validate_arxml.py returns 0 errors |
| G4.5 | Fee template produces FeeBlockSize aligned to page_size for every block | Render + check: all FeeBlockSize % page_size == 0 |
| G4.6 | MemIf template correctly switches between Fee and Ea based on memory_type | Render with "FEE" → MemIfDevice_Fee; render with "EA" → MemIfDevice_Ea |
| G4.7 | NvM template references Ea blocks (not Fee) when memory_type == "EA" | Render with "EA" → VALUE-REF contains "/Ea/EaBlockConfiguration/EaBlock_" |
| G4.8 | Both flash (Fee+Fls) and EEPROM (Ea+Eep) template sets render and validate | Full pipeline for each variant passes validate_arxml.py |

**Quality criteria:**

| # | Metric | Target | How to measure |
|---|--------|--------|----------------|
| Q4.1 | Template rendering time (50 blocks, all 4 templates) | < 2 seconds | `time python render_arxml.py` |
| Q4.2 | Pre-validation time per file | < 0.5 seconds | `time python validate_arxml.py NvM_Config.arxml` |
| Q4.3 | Hook false positive rate | 0% (never blocks a valid file) | Run all templates through pre-arxml hook |

**Stretch goals:**

| # | Goal | Value |
|---|------|-------|
| S4.1 | Post-generate hook runs gcc syntax check on generated .c files | Catches generation bugs before human sees output |
| S4.2 | Templates parameterized by AUTOSAR schema version (R4.4 vs R4.5) | Supports multiple SIP versions |

### 5.3 Hook Evolution Strategy (Post-MVP)

Hooks are the deterministic enforcement layer — they fire regardless of model behavior. Post-MVP hook growth:

**Security hooks:** A PreToolUse hook that blocks MCP write operations unless the git working tree is clean (enforces reversibility). A PostToolUse hook that scans generated code for secret/credential patterns before presenting to user.

**Audit hooks:** A PostToolUse hook that logs every MCP call (tool name, arguments, result summary) to a JSONL audit trail. This addresses the "Observability-Evaluation Gap" from the SotA open research directions.

**CI/CD hooks:** A SessionEnd hook that triggers a Jenkins pipeline or GitHub Action to run the full DVP validation + generation + build on a CI server, decoupling the engineer's workstation from the build cycle.

---

## 6. Phase 5 — Orchestration & CLAUDE.md (Days 14–18)

### 6.1 What We Build

- `skills/memstack-configure.md` — master slash command orchestrating all 7 workflow steps
- `CLAUDE.md` — session-persistent project conventions, module generation order, session log format
- JSON schemas for input validation: `nvm_input_schema.json`, `hw_memory_spec.json`

### 6.2 Success Criteria

**Gate criteria:**

| # | Criterion | Verification |
|---|-----------|-------------|
| G5.1 | `/configure-memstack` is recognized as a valid slash command | Claude Code shows it in auto-complete |
| G5.2 | Master skill delegates to all 5 agents in correct order | Trace execution: input-analyzer → arxml-generator → validation-fixer → safety-reviewer → (human gate) → build-verifier |
| G5.3 | Workflow stops at ASIL review gate and waits for human input | Run with ASIL_D blocks, verify workflow pauses with review table |
| G5.4 | CLAUDE.md is re-read after /compact (survives context compaction) | Compact, then verify Claude still knows project conventions |
| G5.5 | Session log is appended (not overwritten) across sessions | Run 2 sessions, verify both entries present in CLAUDE.md |

**Quality criteria:**

| # | Metric | Target | How to measure |
|---|--------|--------|----------------|
| Q5.1 | End-to-end time: input → generated code (5 blocks) | < 5 minutes | Wall-clock time |
| Q5.2 | End-to-end time: input → generated code (50 blocks) | < 15 minutes | Wall-clock time |
| Q5.3 | Context usage at workflow completion | < 70% of context window | Check context meter after full run |
| Q5.4 | Human interventions required (non-ASIL project) | 1 (final generation approval only) | Count prompts requiring human response |

**Stretch goals:**

| # | Goal | Value |
|---|------|-------|
| S5.1 | Detailed delta report written to `build/memstack_config_report.md` | Full traceability: which blocks, how many iterations, what was fixed |
| S5.2 | `/configure-memstack --dry-run` generates ARXML but skips DVP import | Useful for offline review before committing to DVP |

---

## 7. Phase 6 — Integration Testing & Hardening (Days 16–20)

### 7.1 What We Build

- `tests/test_integration.py` — end-to-end pipeline test (analyze → render → validate)
- `tests/test_memstack.py` — unit tests for analysis, ARXML validation, report parsing
- `tests/fixtures/` — sample inputs (5-block, EEPROM variant, S32K hardware spec)
- Test against a real .dpa project with MICROSAR SIP (if available)
- Documentation + README finalization

### 7.2 Success Criteria

**Gate criteria (MVP GO/NO-GO):**

| # | Criterion | Verification |
|---|-----------|-------------|
| G6.1 | All unit + integration tests pass (current: 61 tests) | `pytest tests/ -v` → 0 failures |
| G6.2 | Full pipeline succeeds on the 5-block sample fixture | analyze → render → validate_arxml → all 4 files pass |
| G6.3 | Full pipeline succeeds for both Fee+Fls and Ea+Eep variants | Run with INTERNAL_FLASH and EEPROM inputs |
| G6.4 | ASIL blocks correctly handled end-to-end | CrashData (ASIL_D): REDUNDANT, CRC32, CalcRamBlockCrc=TRUE, FeeImmediateData=TRUE |
| G6.5 | Cross-module references valid in all generated ARXML | NvM → Fee refs, Fee → Fls refs, MemIf → Fee refs all point to existing containers |
| G6.6 | Edge cases don't crash: 1 block, 200 blocks, all-ASIL_D, DATASET blocks | Run edge case fixture set |

**Quality criteria (MVP readiness):**

| # | Metric | Target | How to measure |
|---|--------|--------|----------------|
| Q6.1 | Test coverage of scripts/ | ≥ 80% line coverage | `pytest --cov=scripts` |
| Q6.2 | Blocks configurable per session | ≥ 50 | Run 50-block fixture through full pipeline |
| Q6.3 | First-attempt ARXML accuracy | ≥ 80% blocks pass validation on first DVP import | Count per-block errors on first import |
| Q6.4 | Validation iterations to 0 errors | ≤ 3 typical | Average across 5 test runs |
| Q6.5 | Generated code compiles | 100% — 0 compilation errors | gcc syntax check on generated .c/.h |

**Stretch goals:**

| # | Goal | Value |
|---|------|-------|
| S6.1 | Test against 2 different MICROSAR SIP versions | Proves template compatibility |
| S6.2 | Test with a real OEM project (>100 NvM blocks) | Validates scalability assumptions |
| S6.3 | Performance benchmark: plot validation time vs block count | Identifies scaling bottlenecks |

### 7.3 MVP Gate Summary

The MVP is **ready for production use** when ALL gate criteria across all 6 phases pass. The consolidated MVP gate checklist:

```
[ ] MCP server connects to real DVP, all 3 core tools work (import, validate, generate)
[ ] Skills encode correct NvM/Fee/MemIf/Fls formulas (verified by unit tests)
[ ] Agents execute in correct order with forked context
[ ] Safety reviewer blocks workflow until human approval
[ ] Hooks enforce ARXML pre-validation and session persistence
[ ] Templates render valid ARXML for both flash and EEPROM variants
[ ] Cross-module references are correct in all generated ARXML
[ ] 61+ tests pass with 0 failures
[ ] End-to-end pipeline succeeds on 50-block project in < 15 minutes
[ ] ASIL blocks get REDUNDANT + CRC without human intervention
[ ] Human intervenes only at safety gate + final approval
```

---

## 8. Implementation Timeline (Revised)

```
Week 1 (Days 1–5):
  ├── MCP server core: CLI wrapper + validation parser
  ├── G1.1–G1.5 gate verification with real .dpa
  ├── Begin skills in parallel (NvM, Fee knowledge encoding)
  └── Milestone: MCP server passes all 5 gate criteria

Week 2 (Days 6–10):
  ├── Complete all 9 skills
  ├── Jinja2 templates: NvM + Fee + Ea + MemIf + Fls + Eep
  ├── Input analyzer agent + analyze_input.py script
  ├── G2.1–G2.6 gate verification via unit tests
  └── Milestone: analyze → render → validate pipeline works offline

Week 3 (Days 11–15):
  ├── ARXML generator agent + render_arxml.py
  ├── Validation fixer agent (evaluator-optimizer loop)
  ├── Safety reviewer agent (hard human gate)
  ├── All 4 hooks + hooks.json registration
  ├── G3.1–G3.6 and G4.1–G4.8 gate verification
  └── Milestone: full agent chain works with MCP

Week 4 (Days 16–20):
  ├── Master orchestration skill (/configure-memstack)
  ├── Build verifier agent
  ├── CLAUDE.md finalization
  ├── Integration testing (61+ tests, edge cases)
  ├── G5.1–G5.5 and G6.1–G6.6 gate verification
  ├── README + documentation
  └── Milestone: MVP gate checklist 100% green
```

---

## 9. Risk Register (Updated)

| Risk | Impact | Probability | Mitigation | Residual |
|------|--------|-------------|------------|----------|
| DVP validation report XML schema undocumented | Parser misses fields | High | 3-level fallback parser (XML → HTML → regex) | Low after fallback |
| Option WF license not available | No PAI parameter-level access | Medium | All gate criteria use CLI-only path. PAI is stretch goal only. | Low — full workflow works without PAI |
| DVP startup time 15–30s per CLI call | Validation loop takes 2–5 min per iteration | High | Batch operations; pre-validate with lxml; measure in Phase 1, adjust fixer strategy | Medium — still workable |
| MICROSAR SIP version differences | Templates generate invalid ARXML for older SIP | Medium | Test against 2 SIP versions (S6.1); parameterize templates by schema version (S4.2) | Medium until tested |
| Cascading validation errors waste iterations | Fixer uses 5 iterations on symptoms, not root causes | High | Error grouping by root container (S3.2); fix root causes first | Low after grouping implemented |
| Context window exhaustion in long sessions | Agents fail mid-workflow | Medium | Forked context per agent; summary-only return; pre-compute in scripts (not in-context) | Low after forking |
| ASIL blocks misconfigured by AI | Safety violation in production | Low (gate-enforced) | Hard human gate (G3.5); safety reviewer never auto-approves; redundancy/CRC auto-upgrade with ESCALATE | Very low |
| DVP CLI invocation differences across DVP versions | Commands fail silently or with unexpected errors | Medium | Document tested DVP version in README; add version detection in MCP server startup | Low after detection |

---

## 10. Post-MVP: Track A — Stack Expansion

### 10.1 Goal
Extend the harness from memory stack (NvM/Fee/Fls) to cover the full BSW configuration surface: Communication stack, Diagnostics, OS, and eventually all AUTOSAR BSW modules.

### 10.2 Module Expansion Roadmap

```
MVP (current):  NvM → MemIf → Fee/Ea → Fls/Eep
                └── memory stack ──────────────┘

Wave 1 (Month 2–3):
    Com → PduR → CanIf → Can Driver
    └── communication stack (DBC → Com signals → PDU routing) ──┘

Wave 2 (Month 3–4):
    Dcm → Dem → NvM (diagnostic storage link)
    └── diagnostics stack (ODX → DIDs → DTCs → fault memory) ──┘

Wave 3 (Month 4–6):
    Os → EcuM → BswM → SchM
    └── system services (tasks, modes, startup, scheduling) ──┘

Wave 4 (Month 6+):
    Rte → application integration
    └── full ECU configuration from SWC descriptors ──────────┘
```

### 10.3 What Each Wave Requires

Each new BSW module follows the same pattern established by the memory stack MVP:

| Component | Effort per module | Template |
|-----------|-------------------|----------|
| **Skill** (parameter rules + error catalog) | 1–2 days | Copy `memstack-nvm.md`, replace with module-specific knowledge |
| **Jinja2 ARXML template** | 1 day | Copy `NvM_Config.arxml.j2`, replace containers/parameters |
| **Agent extension** | 0.5 days | Add module to arxml-generator's rendering list; extend fixer's error catalog |
| **MCP tools** | 0 days (reuse existing) | `davinci_import_arxml` and `davinci_validate` are module-agnostic |
| **Tests** | 1 day | Copy `test_integration.py` test class, adapt for new module |

Estimated effort: **3–5 days per BSW module** once the MVP harness exists.

### 10.4 Wave 1 Deep Dive: Com Stack

The Com stack is the natural next target because it has the richest input artifacts (DBC files, System Extract) and the most cross-module references (Com → PduR → CanIf → Can).

New skills needed:
- `comstack-com.md` — Com signal configuration from DBC signals
- `comstack-pdur.md` — PDU routing tables
- `comstack-canif.md` — CAN interface configuration
- `comstack-can-driver.md` — CAN MCAL driver parameters

New input:
- `com_input.json` — derived from DBC files (signal list, PDU map, timing)
- DBC parser script (`scripts/parse_dbc.py`)

New agent:
- `dbc-analyzer.md` — Explore agent that reads DBC and extracts signals, messages, PDUs

The master orchestration skill would gain a `/configure-comstack` command, or the existing `/configure-memstack` would evolve into `/configure-bsw` with module selection.

### 10.5 Success Criteria for Wave 1

| # | Criterion | Verification |
|---|-----------|-------------|
| A1.1 | Com module ARXML generated from DBC input passes DVP validation in ≤ 3 iterations | Run on sample DBC with 20 signals |
| A1.2 | PduR routing table correctly links Com IPDUs to CanIf | Cross-reference check: every ComIPdu has matching PduR route |
| A1.3 | CanIf configuration matches CAN channel and baud rate from DBC | Verify CanIfBaudrate and CanIfHrhCount match DBC network attributes |
| A1.4 | Master skill handles both `/configure-memstack` and `/configure-comstack` | Both commands work independently and in sequence |

---

## 11. Post-MVP: Track B — Harness Deepening

### 11.1 Agent Teams for Parallel Review

**Current (MVP):** Sequential tree — safety-reviewer runs, then build-verifier runs.

**Target:** Safety-reviewer and build-verifier run as Agent Team teammates in parallel. They communicate findings via JSON inboxes. The team lead (main orchestrator) synthesizes both reviews before presenting to human.

```
MVP (tree):                           Post-MVP (team):
  orchestrator                          orchestrator (team lead)
    → safety-reviewer (wait)              ├── safety-reviewer (teammate)
    → build-verifier (wait)               └── build-verifier (teammate)
  Total: T_review + T_build              Total: max(T_review, T_build)
```

**Success criterion:** Wall-clock time for review+build phase reduced by ≥ 30%.

**Prerequisite:** Claude Code v2.1.19+ Agent Teams feature; tmux available.

### 11.2 PAI Persistent Session

**Current (MVP):** CLI-only path — each `davinci_validate()` starts a new DVP process (15–30s startup).

**Target:** Keep DVP alive as a background process via PAI. The MCP server maintains a persistent connection. After the first `davinci_open_project()`, subsequent calls go through PAI Groovy scripts without restarting DVP.

**Architecture change:**
```python
class PAIPersistentSession:
    """Maintains a long-lived DVP process for zero-startup PAI calls."""

    def __init__(self, dvp_exe, project_path):
        self.process = subprocess.Popen(
            [dvp_exe, "--project", project_path, "--interactive"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def execute_groovy(self, script_text: str) -> dict:
        """Send Groovy script to running DVP process, get JSON result."""
        self.process.stdin.write(script_text.encode() + b"\n---END---\n")
        self.process.stdin.flush()
        return self._read_json_response()
```

**Success criteria:**
- Validation round-trip time drops from 20–30s to < 3s
- 5-iteration validation loop completes in < 30s total (vs 2–3 min with CLI)
- Session survives context compaction (/compact)

**Prerequisite:** Option WF license; DVP interactive mode confirmation from Vector.

### 11.3 Cross-Session Memory

**Current (MVP):** CLAUDE.md session log + session-end hook. Fragile — depends on human not deleting entries.

**Target:** Structured memory using the layered approach from the SotA research:
1. **Slim index** (`memory/index.json`): block names, last-configured date, validation status
2. **Topic files** (`memory/nvm_blocks.json`): per-module detailed state
3. **Session summaries** (`memory/sessions/`): timestamped session logs

The session-end hook writes to all three layers. The UserPromptSubmit hook loads the slim index at session start, providing Claude with project state without consuming full context.

**Success criterion:** New session picks up exactly where previous session left off, without human re-explaining context. Verify by configuring 25 blocks in session 1, then adding 25 more in session 2 — total should be 50 consecutive blocks with correct IDs.

---

## 12. Post-MVP: Track C — Governance & Observability

### 12.1 Audit Trail

Every MCP tool call logged to `audit/audit.jsonl`:
```json
{"timestamp": "2026-05-15T10:23:45Z", "tool": "davinci_validate", "args": {}, "result_summary": "12 errors", "duration_ms": 22340, "session": "abc123"}
{"timestamp": "2026-05-15T10:24:12Z", "tool": "davinci_import_arxml", "args": {"files": ["NvM_Config.arxml"]}, "result_summary": "ok", "duration_ms": 8210, "session": "abc123"}
```

**Value:** Traceability for regulated industries (ISO 26262 process evidence, EU AI Act compliance). Answers "who configured what, when, and how many iterations did it take?"

**Success criterion:** Complete audit trail for every `/configure-memstack` run. Auditor can reconstruct the full configuration history from the JSONL log.

### 12.2 Cost Attribution

Track token usage and DVP license time per configuration run:
- Claude API tokens consumed (input + output)
- DVP process-seconds (CLI startup + validation + generation)
- Wall-clock time per workflow step

**Value:** Enables ROI measurement. Compare AI-assisted configuration time vs manual configuration time for the same block set.

### 12.3 Guardrail Engine

Following the `claude-code-harness` Go-native pattern: a lightweight binary that runs as a PreToolUse hook and enforces hard security rules that the model cannot override:

- Block any `davinci_set_parameter` call that modifies an ASIL block without prior `safety-reviewer` approval in the same session
- Block `davinci_generate()` on production branch without human sign-off
- Block force-push patterns in git operations
- Block secret/credential patterns in ARXML content

**Value:** Defense-in-depth. Even if the model hallucinates an approval or skips the safety review, the guardrail engine blocks the dangerous action at the harness level.

---

## 13. Consolidated Success Metrics

### MVP Metrics

| Metric | Target | Measurement point |
|--------|--------|-------------------|
| Blocks configurable per session | ≥ 50 | Phase 6 integration test |
| First-attempt ARXML accuracy | ≥ 80% of blocks | Phase 6 DVP validation |
| Validation iterations to 0 errors | ≤ 3 typical, ≤ 5 max | Phase 6 integration test |
| End-to-end time (50 blocks) | < 15 minutes | Phase 6 wall-clock |
| Human interventions (non-ASIL) | 1 (generation approval) | Phase 5 workflow trace |
| Generated code compiles | 100% | Phase 6 build test |
| Test count | ≥ 61, 0 failures | Phase 6 pytest |
| ASIL compliance | 100% of ASIL blocks reviewed by human | Phase 3 safety reviewer |

### Post-MVP Metrics (6-month targets)

| Metric | Target | Track |
|--------|--------|-------|
| BSW modules covered | ≥ 15 (from 6) | Track A |
| Validation loop time (PAI) | < 30s for 5 iterations | Track B |
| Cross-session state recovery | 100% correct across session boundary | Track B |
| Audit trail completeness | Every MCP call logged | Track C |
| Engineer time savings | ≥ 60% reduction vs manual configuration | Track C (cost attribution) |
| Validation fix catalog size | ≥ 100 patterns (from ~20) | Skill evolution |
| Agent team parallel speedup | ≥ 30% for review phase | Track B |

---

## 14. Dependency Map

```
                    Phase 1: MCP Server
                   /        |         \
                  /         |          \
     Phase 2: Skills   Phase 4: Hooks   Phase 4: Templates
          \         \       |          /
           \         \      |         /
            Phase 3: Agents (uses skills + MCP)
                     |
            Phase 5: Orchestration (wires everything)
                     |
            Phase 6: Integration Test (validates everything)
                     |
              ─── MVP GATE ───
                   / | \
                  /  |  \
         Track A  Track B  Track C
       (breadth) (depth)  (governance)
```

Phase 1 is the only true serial dependency. Phases 2, 3, and 4 can overlap significantly once the MCP server core exists. Phase 5 integrates everything. Phase 6 validates it all.

Post-MVP tracks are independent — they can be pursued in any order based on project priorities. Track A (stack expansion) has the most immediate user value. Track B (harness deepening) has the most performance impact. Track C (governance) is required for regulated deployments.
