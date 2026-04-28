---
name: memstack-nvm
description: >
  NvM (NVRAM Manager) module configuration patterns for AUTOSAR Classic.
  Covers block types, ID assignment, Fee block number calculation,
  CRC rules, priority, and common validation error fixes.
---

# NvM Configuration Patterns

## Block Types

### NVM_BLOCK_NATIVE
Single-instance storage block. No redundancy.
- NvMBlockLength = data size in bytes
- NvMRamBlockDataAddress = &Rte_NvMBlock_<Name>_Ram
- NvMRomBlockDataAddress = &Rte_NvMBlock_<Name>_Default (or NULL_PTR if no default)
- NvMBlockUseCrc: optional (recommended TRUE for data integrity)

### NVM_BLOCK_REDUNDANT
Dual-copy for safety-critical data. **Mandatory for ASIL >= B**.
- Same base parameters as NATIVE
- NvMBlockManagementType = NVM_BLOCK_REDUNDANT
- NvMBlockUseCrc = TRUE (mandatory — redundancy without CRC is invalid)
- NvMCalcRamBlockCrc = TRUE (runtime detection of RAM corruption)
- NvMBlockCrcType:
  - NVM_CRC16: blocks <= 256 bytes
  - NVM_CRC32: blocks > 256 bytes
- Fee stores 2 copies: primary at FeeBlockNumber, redundant at FeeBlockNumber + 1

### NVM_BLOCK_DATASET
Multiple datasets (e.g., calibration variants, multi-profile storage).
- NvMMaxNumOfDataSets = number of dataset instances
- NvMBlockLength = size of ONE dataset (not total)
- Fee stores NvMMaxNumOfDataSets × (block + header + CRC) in NV

## Block ID Assignment Rules
- Block 0: Reserved (NvM multi-block request status — internal)
- Block 1: NvM configuration block (NvM internal — auto-generated)
- Block 2+: User blocks — **start at 2, consecutive, no gaps**
- Maximum block count: typically 65533 (0xFFFD), but practical limit ~500 for Fee performance

## Fee Block Number Calculation (Critical Cross-Module Link)
```
NvMNvBlockBaseNumber = NvMNvBlockNum × 2

Fee block number (primary copy)   = NvMNvBlockBaseNumber
Fee block number (redundant copy) = NvMNvBlockBaseNumber + 1
```
This formula must be consistent between NvM and Fee configurations.
Mismatch here is the #1 cause of cross-module validation errors.

## NvM-to-Fee Reference
Each NvMBlockDescriptor must contain:
```xml
<ECUC-REFERENCE-VALUE>
  <DEFINITION-REF DEST="ECUC-CHOICE-REFERENCE-DEF">
    /MICROSAR/NvM/NvMBlockDescriptor/NvMTargetBlockReference
  </DEFINITION-REF>
  <VALUE-REF DEST="ECUC-CONTAINER-VALUE">
    /AUTOSAR/Fee/FeeBlockConfiguration/FeeBlock_<BlockName>
  </VALUE-REF>
</ECUC-REFERENCE-VALUE>
```

## Write Policies
- **NVM_BLOCK_WRITE_DURING_WRITEALL**: written when NvM_WriteAll() is called (shutdown)
- **NVM_BLOCK_WRITE_IMMEDIATE**: written immediately on NvM_WriteBlock() call
  - Use for crash-relevant data (odometer, DTC status)
  - Requires FeeImmediateData = TRUE in Fee config
  - Limit immediate-write blocks to < 5 (each triggers flash erase, impacts timing)

## Job Priority
- NvMBlockJobPriority = 0: highest priority (immediate processing)
- NvMBlockJobPriority = 1-255: lower priority (queued processing)
- Priority 0 blocks should also have NvMWriteBlockOnce = FALSE (crash data needs repeated writes)

## NvM Common Parameters
- NvMCompiledConfigId: unique 16-bit ID, change on every config update
  - Triggers full re-initialization of NvM data on ECU reflash
- NvMDatasetSelectionBits: 0 if no DATASET blocks, otherwise ceil(log2(max_datasets))
- NvMJobPrioritization: TRUE if any block uses priority 0

## Common Validation Errors and Fixes

| Error Pattern | Category | Root Cause | Fix |
|---|---|---|---|
| NvMTargetBlockReference unresolved | MISSING_REF | No matching Fee block | Create FeeBlockConfiguration with FeeBlockNumber = NvMNvBlockBaseNumber |
| NvMBlockCrcType not set | PARAM_ADJUST | Block uses CRC but type missing | Set NvMBlockCrcType to CRC16 (<=256B) or CRC32 (>256B) |
| NvMBlockLength = 0 | PARAM_ADJUST | Length not configured | Set to actual data size from input descriptor |
| NvMNvBlockNum duplicate | AUTO_FIX | Two blocks share same ID | Reassign IDs consecutively from 2 |
| NvMCalcRamBlockCrc without NvMBlockUseCrc | PARAM_ADJUST | Inconsistent CRC config | Set NvMBlockUseCrc = TRUE |
| NvMBlockManagementType missing for ASIL block | ESCALATE | Safety-relevant — needs review | Flag for human: set to REDUNDANT after confirmation |
| NvMCompiledConfigId = 0 | AUTO_FIX | Default value not changed | Set to hash of current config timestamp |
| NvMRamBlockDataAddress undefined | STRUCTURAL | Missing Rte buffer reference | Add reference to Rte_NvMBlock_<Name>_Ram symbol |
