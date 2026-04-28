# AUTOSAR Memory Stack Auto-Configuration Agent

A Claude Code harness for automatic configuration of the AUTOSAR Classic Memory Stack
(NvM → MemIf → Fee/Fls or Ea/Eep) using Vector DaVinci Configurator.

## Architecture

```
Claude Code (orchestrator)
  ├── Skills:  Domain knowledge for each BSW module
  ├── Agents:  Specialized workers (analyze, generate, validate, review)
  ├── Hooks:   Deterministic guards on ARXML writes + session persistence
  ├── MCP:     DaVinci Configurator CLI + PAI bridge
  └── Templates: Jinja2 ARXML templates for each module
```

## Quick Start

### Prerequisites

- Claude Code v2.1+ installed
- Vector DaVinci Configurator Classic (Generation 6+) with valid license
- Option WF license (optional — enables PAI parameter-level access)
- Python 3.10+ with `lxml`, `jinja2`, `mcp`
- A MICROSAR SIP installed in your DaVinci project

### Setup

```bash
# 1. Clone this repo into your AUTOSAR project
git clone https://github.com/<your-user>/autosar-memstack-agents.git
cd autosar-memstack-agents

# 2. Install Python dependencies
pip install -r mcp-servers/vector-davinci-mcp/requirements.txt

# 3. Configure DaVinci path in .mcp.json
#    Edit DVP_EXE to point to your DaVinciCFG.exe
#    Edit DVP_PROJECT to point to your .dpa project

# 4. Prepare input files
#    - memstack_input.json  (NvBlock descriptors)
#    - memory_hw_spec.json  (target MCU memory geometry)
#    See schemas/ for JSON schema definitions, tests/fixtures/ for examples.

# 5. Launch Claude Code in this directory
claude

# 6. Run the master workflow
/configure-memstack
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

## Workflow

```
/configure-memstack
  │
  ├── Step 1: Input Analysis (Explore agent)
  │     Read NvBlock descriptors + HW spec → compute block layout
  │
  ├── Step 2: ARXML Generation (Plan agent)
  │     Fls → Fee → MemIf → NvM (bottom-up for reference resolution)
  │
  ├── Step 3: Validation Loop (Evaluator-Optimizer agent)
  │     Import → Validate → Parse errors → Patch → Re-validate (max 5x)
  │
  ├── Step 4: ASIL Review Gate ⛔ HUMAN APPROVAL REQUIRED
  │     Redundancy, CRC, wear-leveling checks for safety blocks
  │
  ├── Step 5: Code Generation
  │     davinci_generate() → collect BSW .c/.h files
  │
  └── Step 6: Build Verification (Bash agent)
        Compile + MISRA-C check on generated code
```

## Repository Structure

```
├── CLAUDE.md                    # Session-persistent project conventions
├── .mcp.json                    # MCP server registration
├── skills/                      # Domain knowledge (loaded on demand)
├── agents/                      # Subagent definitions
├── hooks/                       # Deterministic lifecycle hooks
├── mcp-servers/                 # DaVinci MCP bridge
│   └── vector-davinci-mcp/
├── templates/                   # Jinja2 ARXML templates
├── schemas/                     # JSON schemas for input validation
└── tests/                       # Unit + integration tests
```

## Safety Philosophy

This harness follows Claude Code's **human decision authority** design value:
- ASIL-rated blocks always require human approval before code generation
- Git commit before every DaVinci import (reversibility)
- Deny-first permission model for MCP tools
- Safety reviewer agent presents findings — never auto-approves

## License

MIT
