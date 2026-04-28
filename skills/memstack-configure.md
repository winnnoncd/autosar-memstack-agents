---
name: configure-memstack
description: >
  Automatically configure the AUTOSAR Classic memory stack
  (NvM, MemIf, Fee/Ea, Fls/Eep) from NvBlock descriptors and
  hardware memory spec. Generates ARXML, imports into DaVinci
  Configurator, validates, auto-fixes, and triggers code generation.
allowed-tools: Bash(*), mcp__davinci__*
agent: general-purpose
---

# Memory Stack Auto-Configuration — Master Workflow

## Prerequisites
Before running, ensure:
- DaVinci MCP server is registered in `.mcp.json` and responding
- Input files exist: `memstack_input.json` + `memory_hw_spec.json`
- DaVinci project (.dpa) is accessible with MICROSAR SIP installed
- Git working tree is clean (we will commit before DVP import)

## Step 1 — Input Analysis
**Delegate to: input-analyzer agent (Explore, forked context)**

Read and validate both input files against JSON schemas in `schemas/`.
Compute:
- Block list with assigned IDs (starting at 2, consecutive)
- Fee block numbers (NvM block ID × 2)
- Memory type determination: INTERNAL_FLASH → Fee+Fls, EEPROM → Ea+Eep
- Total RAM budget: sum of (block_size + CRC_overhead) for all blocks
- Total NV budget: sum of (block_size + header_16B + CRC_overhead + 10% margin)
- Verify NV budget fits in available flash/EEPROM sectors
- Identify ASIL >= B blocks → flag for Step 4 review

Output: `build/analysis.json` with full computed layout.

## Step 2 — ARXML Generation
**Delegate to: arxml-generator agent (Plan, forked context)**

Load module-specific skills and generate ARXML **bottom-up**:

1. **Fls_Config.arxml** (or Eep_Config.arxml)
   - Load skill: `memstack-fls-eep`
   - Flash sector definitions from `memory_hw_spec.json`
   - Sector start addresses, sizes, erase values

2. **Fee_Config.arxml** (or Ea_Config.arxml)
   - Load skill: `memstack-fee` (or `memstack-ea`)
   - Sector layout: num_sectors, sector_size
   - Block configurations: FeeBlockNumber, FeeBlockSize, FeeImmediateData
   - Cross-ref to Fls: FeeFlsReference

3. **MemIf_Config.arxml**
   - Load skill: `memstack-memif`
   - Device routing: MemIfDevice → Fee or Ea
   - MemIfNumberOfDevices

4. **NvM_Config.arxml**
   - Load skill: `memstack-nvm`
   - Block descriptors: ID, length, type, CRC, priority, RAM/ROM addresses
   - Cross-ref to Fee: NvMTargetBlockReference

Each file is rendered from Jinja2 templates in `templates/`.
Pre-validate each ARXML with `python scripts/validate_arxml.py` before proceeding.
Write all files to `project/config/`.

## Step 3 — DaVinci Import & Validation Loop
**Delegate to: validation-fixer agent (general-purpose, forked context)**

```
git add -A && git commit -m "pre-dvp-import: generated memstack ARXML"

iteration = 0
MAX_ITERATIONS = 5

while iteration < MAX_ITERATIONS:
    davinci_import_arxml(["project/config/Fls_Config.arxml",
                          "project/config/Fee_Config.arxml",
                          "project/config/MemIf_Config.arxml",
                          "project/config/NvM_Config.arxml"])
    errors = davinci_validate()

    if errors.count == 0:
        break

    # Group errors by root container path
    # Fix root causes first (avoid cascading error waste)
    # Generate ARXML patches per error category:
    #   AUTO_FIX:     apply directly
    #   PARAM_ADJUST: modify value in ARXML
    #   MISSING_REF:  add reference element
    #   STRUCTURAL:   add missing container
    #   ESCALATE:     collect for human review in Step 4

    apply_patches()
    iteration += 1

if iteration == MAX_ITERATIONS and errors remain:
    STOP — present remaining errors to human
```

## Step 4 — ASIL Review Gate
**Delegate to: safety-reviewer agent (Plan, forked context)**

⛔ **HUMAN APPROVAL REQUIRED — DO NOT AUTO-APPROVE**

Check all ASIL >= B blocks:
- [ ] NvMBlockManagementType = REDUNDANT
- [ ] NvMBlockUseCrc = TRUE
- [ ] NvMCalcRamBlockCrc = TRUE
- [ ] NvMBlockCrcType = CRC32 (for blocks > 256 bytes)
- [ ] FeeImmediateData = TRUE (for priority 0 blocks)
- [ ] Fee sector wear-leveling margin >= 2× expected write cycles
- [ ] NvM read-all order: ASIL blocks before QM blocks

Present structured review table. Wait for human "approved" before proceeding.

## Step 5 — Code Generation
After human approval:
```
git add -A && git commit -m "pre-generation: validated memstack config"
davinci_generate()
```
Collect generated `.c` and `.h` files from `generated/` directory.

## Step 6 — Build Verification
**Delegate to: build-verifier agent (Bash, forked context)**

- Compile generated BSW with project toolchain
- Run MISRA-C static analysis on generated files
- Report any compilation errors or MISRA violations

## Step 7 — Delta Report
Write session summary to `CLAUDE.md` under `## Session Log`:
- Blocks configured (count + names)
- Validation iterations needed
- Errors fixed automatically vs. escalated
- Code generation status
- Build verification result
- Open items for next session

Also write detailed report to `build/memstack_config_report.md`.
