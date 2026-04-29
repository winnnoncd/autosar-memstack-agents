---
name: memstack-fee
description: Use when configuring Fee sectors or block mappings, when working with flash EEPROM emulation, sector layout, or Fee validation errors
---

# Fee Configuration Patterns

## Sector Layout

### Minimum Sectors
Fee requires **at least 2 sectors** for wear leveling:
- Active sector: stores current block data
- Transfer/spare sector: receives data during sector swap

Recommended: **3 sectors** (active + transfer + spare) for reliability.
ASIL applications: consider **4 sectors** for additional redundancy margin.

### Sector Size
- Must match physical flash sector size from Fls driver
- FeeSectorSize = FlsSectorSize (exact match required)
- Total Fee area = FeeSectorCount × FeeSectorSize
- Total Fee area must accommodate all blocks with header overhead

### Sector Configuration ARXML
Each sector needs a `FeeSectorConfiguration` container:
```xml
<ECUC-CONTAINER-VALUE>
  <SHORT-NAME>FeeSector_0</SHORT-NAME>
  <DEFINITION-REF>
    /MICROSAR/Fee/FeeGeneral/FeeSectorConfiguration
  </DEFINITION-REF>
  <PARAMETER-VALUES>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Fee/FeeSectorConfiguration/FeeSectorSize</DEFINITION-REF>
      <VALUE>4096</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Fee/FeeSectorConfiguration/FeeNumberOfSectors</DEFINITION-REF>
      <VALUE>3</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
  </PARAMETER-VALUES>
</ECUC-CONTAINER-VALUE>
```

## Block Configuration

### FeeBlockNumber
- Must match NvM's NvMNvBlockBaseNumber exactly
- FeeBlockNumber = NvMNvBlockNum × 2

### FeeBlockSize Calculation
```
FeeBlockSize = NvMBlockLength
             + Fee_Header_Overhead   (16 bytes for MICROSAR)
             + CRC_Overhead          (2 bytes CRC16 or 4 bytes CRC32)
             + alignment_padding     (align to FlsPageSize boundary)
```

Alignment formula:
```python
def aligned_fee_block_size(nvm_length, crc_bytes, header=16, page_size=8):
    raw = nvm_length + header + crc_bytes
    return ((raw + page_size - 1) // page_size) * page_size
```

### FeeImmediateData
- Set TRUE for blocks with NvMBlockJobPriority = 0
- Immediate blocks are stored in a dedicated sector partition
- Max immediate block size: limited by single-page write capability
- Typical limit: FlsPageSize (or FlsMaxWriteSize if different)

### Block Ordering
- Sort FeeBlockConfiguration entries by FeeBlockNumber (ascending)
- No gaps in block numbers within a sector
- Gap detection: if FeeBlockNumber sequence has gaps, DVP may warn

## Fee-to-Fls Reference
```xml
<ECUC-REFERENCE-VALUE>
  <DEFINITION-REF DEST="ECUC-REFERENCE-DEF">
    /MICROSAR/Fee/FeeGeneral/FeeFlsReference
  </DEFINITION-REF>
  <VALUE-REF DEST="ECUC-CONTAINER-VALUE">
    /AUTOSAR/Fls/FlsGeneral
  </VALUE-REF>
</ECUC-REFERENCE-VALUE>
```

## Wear Leveling

### Sector Fill Threshold
- FeeThreshold: percentage of sector fill before triggering swap
- Default: 90% (0.9 × sector_size)
- For ASIL applications: 80% (more conservative, earlier swap)
- Too low: frequent swaps (performance impact)
- Too high: risk of running out of space during swap

### Write Cycle Budget
- Total writes per sector = max_erase_cycles (from Fls/hardware spec)
- Per-block writes ≈ total_writes × (sector_size / fee_block_size)
- Verify: expected_block_writes_per_lifetime < per-block budget
- For ASIL blocks: require margin >= 2× expected lifetime writes

## MICROSAR-Specific Notes (Vector)
- Fee header overhead: 16 bytes (may vary by MICROSAR version)
- Fee supports CRC over block data (FeeBlockCrc)
- FeeVirtualSectorsPerPhysicalSector: typically 1 for simple setups
- Fee instance handling: FeeDeviceIndex maps to MemIf device index

## Common Validation Errors and Fixes

| Error Pattern | Category | Fix |
|---|---|---|
| FeeBlockNumber not matching NvM | MISSING_REF | Set FeeBlockNumber = NvMNvBlockNum × 2 |
| FeeBlockSize too small | PARAM_ADJUST | Recalculate: NvMBlockLength + 16 + CRC + alignment |
| Missing FeeSectorConfiguration | STRUCTURAL | Add sector container with size matching FlsSectorSize |
| FeeSectorSize != FlsSectorSize | PARAM_ADJUST | Align FeeSectorSize to FlsSectorSize |
| FeeFlsReference unresolved | MISSING_REF | Add reference to /AUTOSAR/Fls/FlsGeneral |
| FeeBlockNumber gap | AUTO_FIX | Renumber blocks consecutively |
| FeeImmediateData inconsistent with NvM priority | PARAM_ADJUST | Set TRUE if NvMBlockJobPriority = 0 |
| Fee total block size exceeds sector capacity | ESCALATE | Increase sector count or reduce block sizes — needs engineering review |
