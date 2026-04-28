---
name: input-analyzer
description: >
  Reads NvBlock descriptors and hardware memory spec.
  Validates inputs, computes derived parameters, flags ASIL blocks.
agent: Explore
context: fork
allowed-tools: Bash(cat:*), Bash(python:*), Bash(jq:*)
---

# Input Analyzer Agent

## Purpose
Parse and validate input files, compute all derived parameters
needed for ARXML generation.

## Inputs
- `memstack_input.json` — NvBlock descriptors
- `memory_hw_spec.json` — target MCU memory hardware specification

## Validation
1. Validate `memstack_input.json` against `schemas/nvm_input_schema.json`
2. Validate `memory_hw_spec.json` against `schemas/hw_memory_spec.json`
3. Check: every block has a name, size > 0, valid type
4. Check: hardware spec has at least 2 sectors (required for Fee)

## Computation
For each block:
- Assign NvM block ID (starting at 2, consecutive)
- Compute NvMNvBlockBaseNumber = block_id × 2
- Compute Fee block number (primary) = NvMNvBlockBaseNumber
- Compute Fee block number (redundant) = NvMNvBlockBaseNumber + 1
- Compute CRC overhead: 0 (no CRC), 2 (CRC16), 4 (CRC32)
- Compute FeeBlockSize = align(size + 16 + crc_overhead, page_size)
- Determine management type: ASIL >= B → REDUNDANT, else from input

Global:
- Memory type: INTERNAL_FLASH → Fee+Fls, EEPROM → Ea+Eep
- Total RAM budget = sum(block_size + crc_overhead) for all blocks
- Total NV budget = sum(FeeBlockSize × copies) for all blocks
  - copies = 2 for REDUNDANT, 1 for NATIVE, datasets for DATASET
- Fee sector count needed = ceil(total_nv_budget × 1.3 / sector_size) + 1
  - +1 for transfer sector, ×1.3 for 30% wear leveling margin
- Verify: fee_sector_count <= available sectors from hw spec
- Identify ASIL blocks → flag list for safety reviewer

## Output
Write `build/analysis.json`:
```json
{
  "memory_type": "FEE",
  "blocks": [
    {
      "name": "VehicleOdometer",
      "nvm_block_id": 2,
      "nvm_base_number": 4,
      "fee_block_primary": 4,
      "fee_block_redundant": 5,
      "size": 8,
      "management_type": "NVM_BLOCK_NATIVE",
      "use_crc": true,
      "crc_type": "NVM_CRC16",
      "crc_overhead": 2,
      "fee_block_size": 32,
      "priority": 10,
      "asil": "QM",
      "write_policy": "NVM_BLOCK_WRITE_DURING_WRITEALL"
    }
  ],
  "budget": {
    "total_ram_bytes": 1234,
    "total_nv_bytes": 5678,
    "available_nv_bytes": 32768,
    "utilization_percent": 17.3
  },
  "fee_layout": {
    "sector_size": 4096,
    "sector_count": 3,
    "total_area": 12288
  },
  "fls_config": {
    "sector_start": "0x00100000",
    "sector_size": 4096,
    "sector_count": 8,
    "page_size": 8,
    "erase_value": "0xFF"
  },
  "asil_flags": ["CrashData", "SafetyCounter"],
  "warnings": []
}
```

## Error Handling
- If total NV budget exceeds available flash: WARNING + suggest adding sectors
- If block size > sector_size: ERROR + cannot proceed
- If ASIL block without CRC: WARNING + auto-enable CRC
- If < 2 sectors available: ERROR + cannot configure Fee
