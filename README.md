# AUTOSAR Memory Stack Auto-Configuration Agent

An agent harness for automatic configuration of the AUTOSAR Classic Memory Stack
(NvM → MemIf → Fee/Fls or Ea/Eep) using Vector DaVinci Configurator.

> **Platform:** GitHub Copilot CLI (Phase 1) · GitLab Duo (Phase 2)
> See `docs/IMPLEMENTATION_PLAN_v4.md` for the full migration plan.

## Architecture

```
Copilot CLI (orchestrator)
  ├── Skills:     Domain knowledge + process enforcement (.github/skills/)
  ├── Agents:     Specialized subagents (.github/agents/)
  ├── Hooks:      Lifecycle guards on ARXML writes + session persistence (.github/hooks/)
  ├── MCP:        DaVinci Configurator CLI + PAI bridge (.mcp.json)
  └── Templates:  Jinja2 ARXML templates for each module (templates/)
```

### Skill Taxonomy

**Process skills (rigid — follow exactly):**
- `using-memstack-skills` — session bootstrap, skill priority, rationalization guards
- `memstack-requirements` — requirements gathering before any configuration
- `memstack-configure` — rigid 7-step workflow with STOP gates
- `memstack-verification` — post-completion and ASIL review checklist

**Knowledge skills (flexible — adapt to context):**
- `memstack-nvm`, `memstack-fee`, `memstack-ea`, `memstack-memif`, `memstack-fls-eep`
- `arxml-generation`, `arxml-validation-fix`, `davinci-cli-reference`

## Quick Start

### Prerequisites

- GitHub Copilot CLI (GA February 2026)
- Vector DaVinci Configurator Classic (Generation 6+) with valid license
- Option WF license (optional — enables PAI parameter-level access)
- Python 3.10+ with `lxml`, `jinja2`, `mcp`, `jsonschema`
- A MICROSAR SIP installed in your DaVinci project

### Setup

```bash
# 1. Clone this repo into your AUTOSAR project workspace
git clone https://github.com/<your-user>/autosar-memstack-agents.git
cd autosar-memstack-agents

# 2. Install Python dependencies
pip install -r mcp-servers/vector-davinci-mcp/requirements.txt

# 3. Configure DaVinci path in .mcp.json
#    Set DVP_EXE to your DaVinciCFG.exe path
#    Set DVP_PROJECT to your .dpa project file

# 4. Launch Copilot CLI in this directory
copilot

# 5. Start the memory stack workflow
# The agent will invoke memstack-requirements automatically
```

### Input File Format

**memstack_input.json** — defines each NvM block:
```json
{
  "blocks": [
    {
      "name": "VehicleOdometer",
      "size": 8,
      "type": "NATIVE",
      "asil": "QM",
      "use_crc": true,
      "crc_type": "CRC16",
      "write_policy": "DURING_WRITEALL",
      "priority": 10,
      "default_value": "0x00"
    }
  ]
}
```

**memory_hw_spec.json** — defines target flash/EEPROM:
```json
{
  "memory_type": "INTERNAL_FLASH",
  "sectors": [
    { "start": "0x00100000", "size": 4096, "count": 8 }
  ],
  "page_size": 8,
  "erase_value": "0xFF",
  "max_erase_cycles": 100000
}
```

See `schemas/` for JSON schema definitions, `tests/fixtures/` for examples.

## Workflow

```
"Configure memory stack" (user prompt)
  │
  ├── memstack-requirements skill
  │     Ask structured questions → produce memstack_input.json + memory_hw_spec.json
  │     → STOP: confirm budget summary
  │
  └── memstack-configure skill (invoked by user after confirmation)
        │
        ├── Step 1: Input Analysis
        │     python scripts/analyze_input.py → build/analysis.json
        │     → STOP: confirm analysis
        │
        ├── Step 2: ARXML Generation
        │     python scripts/render_arxml.py → project/config/*.arxml
        │     → pre-validate with scripts/validate_arxml.py
        │
        ├── Step 3: DVP Import + Validation Loop (max 5 iterations)
        │     davinci_import_arxml → davinci_validate
        │     → per-error-group subagent dispatch for patches
        │
        ├── Step 4: ASIL Review Gate ⛔ HUMAN APPROVAL REQUIRED
        │     memstack-verification (ASIL checks) → structured table
        │     → STOP: mandatory human approval
        │
        ├── Step 5: Code Generation
        │     davinci_generate() → BSW .c/.h files
        │
        ├── Step 6: Build Verification
        │     build-verifier agent: compile + MISRA-C check
        │
        └── Step 7: Completion
              memstack-verification (full checklist) → session summary
```

## Repository Structure

```
├── AGENTS.md                         # Project conventions (read by agent)
├── .mcp.json                         # MCP server registration
├── .github/
│   ├── skills/                       # 13 skills (4 process + 9 knowledge)
│   │   ├── using-memstack-skills/
│   │   ├── memstack-requirements/
│   │   ├── memstack-configure/
│   │   ├── memstack-verification/
│   │   ├── memstack-nvm/
│   │   ├── memstack-fee/
│   │   └── ...
│   ├── agents/                       # 5 subagent definitions
│   │   ├── input-analyzer.agent.md
│   │   ├── arxml-generator.agent.md
│   │   ├── validation-fixer.agent.md
│   │   ├── safety-reviewer.agent.md
│   │   └── build-verifier.agent.md
│   └── hooks/
│       └── memstack.json             # Hook registration (version: 1)
├── hooks/                            # Hook scripts
│   ├── session-start-bootstrap.sh
│   ├── pre-arxml-write.sh
│   ├── post-arxml-write.sh
│   ├── post-generate.sh
│   └── session-end.sh
├── mcp-servers/vector-davinci-mcp/   # DaVinci MCP bridge (platform-agnostic)
├── scripts/                          # Python pipeline scripts
├── templates/                        # Jinja2 ARXML templates
├── schemas/                          # JSON schemas for input validation
├── tests/                            # Unit + integration tests (61 tests)
└── docs/                             # Documentation and plan files
```

## Safety Philosophy

This harness follows a **human decision authority** design value:
- ASIL-rated blocks always require human approval before code generation
- Git commit before every DaVinci import (reversibility)
- Deny-first permission model via preToolUse hook (malformed ARXML blocked)
- Safety reviewer agent presents findings — never auto-approves

## Development

```bash
# Run tests
pip install pytest lxml jinja2 jsonschema
pytest tests/ -v

# Validate hook config
python -m json.tool .github/hooks/memstack.json

# Test sessionStart bootstrap hook
echo '{}' | bash hooks/session-start-bootstrap.sh
```

## License

MIT
