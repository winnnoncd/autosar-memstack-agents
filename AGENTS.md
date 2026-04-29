# autosar-memstack-agents

## Stack
- Configuration: ARXML (AUTOSAR R4.4+), XML, JSON
- Scripting: Python 3.10+, Jinja2, lxml
- Toolchain: Vector DaVinci Configurator Classic (Generation 6+)
- PAI: Groovy (DVP internal scripting, requires Option WF license)
- Build: GHS MULTI / GCC ARM for BSW compilation
- Language: C (generated BSW), Python (tooling), Groovy (PAI scripts)

## Conventions
- All ARXML must validate against AUTOSAR XSD before DVP import
- Run `python scripts/validate_arxml.py <file>` before any DVP import
- NvM block IDs start at 2, consecutive, no gaps
- Fee block numbers = NvM block number × 2
- Git commit current state before every DVP import (reversibility)
- ASIL >= B blocks always require human approval before code generation
- Never auto-approve safety-critical configuration decisions

## Module Generation Order
Always generate ARXML bottom-up: Fls/Eep → Fee/Ea → MemIf → NvM
This ensures cross-module references resolve at DVP import time.

## MCP Servers
- `davinci`: local DaVinci CLI + PAI bridge (see .mcp.json)

## Memory Stack Modules
- NvM: NVRAM Manager — block definitions, CRC, read/write-all
- MemIf: Memory Abstraction Interface — routes to Fee or Ea
- Fee: Flash EEPROM Emulation — sector layout, block mapping
- Ea: EEPROM Abstraction — block mapping (EEPROM variant)
- Fls: Flash driver (MCAL) — sector definitions
- Eep: EEPROM driver (MCAL) — device configuration

## Fee Block Number Calculation
- NvMNvBlockBaseNumber = NvMNvBlockNum × 2
- Fee primary block number = NvMNvBlockBaseNumber
- Fee redundant copy number = NvMNvBlockBaseNumber + 1

## Validation Loop Protocol
- Max 5 iterations of validate → fix → re-validate
- Group errors by root container path, fix root causes first
- Escalate to human if errors persist after 5 iterations
- Pre-validate with Python/lxml before DVP import (saves 15-30s startup)

## Current Focus
Initial implementation of memory stack auto-configuration workflow.

## Session Log
<!-- Appended by session-end hook -->
