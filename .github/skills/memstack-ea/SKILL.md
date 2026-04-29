---
name: memstack-ea
description: Use when configuring Ea blocks for external EEPROM, when target hardware uses EEPROM rather than internal flash
---

# Ea Configuration Patterns

## When to Use Ea vs Fee
- **Fee + Fls**: Internal flash with sector erase (most common)
- **Ea + Eep**: External EEPROM (I2C/SPI) with byte-level write

## Ea Block Configuration

### EaBlockNumber
- Same mapping as Fee: EaBlockNumber = NvMNvBlockNum × 2
- Redundant copy at EaBlockNumber + 1

### EaBlockSize
```
EaBlockSize = NvMBlockLength + Ea_Header_Overhead + CRC_Overhead
```
Ea header overhead is typically 8 bytes (smaller than Fee — no sector management).

### Key Differences from Fee
- No sector layout needed (EEPROM has no erase sectors)
- No wear leveling sectors (EEPROM has inherent byte-level write)
- Simpler configuration: just block definitions + Eep reference
- EaDeviceIndex maps to MemIf device index

## Ea-to-Eep Reference
```xml
<ECUC-REFERENCE-VALUE>
  <DEFINITION-REF DEST="ECUC-REFERENCE-DEF">
    /MICROSAR/Ea/EaGeneral/EaEepReference
  </DEFINITION-REF>
  <VALUE-REF DEST="ECUC-CONTAINER-VALUE">
    /AUTOSAR/Eep/EepGeneral
  </VALUE-REF>
</ECUC-REFERENCE-VALUE>
```

## Common Validation Errors

| Error | Category | Fix |
|---|---|---|
| EaBlockNumber mismatch with NvM | MISSING_REF | Set EaBlockNumber = NvMNvBlockNum × 2 |
| EaEepReference unresolved | MISSING_REF | Add reference to /AUTOSAR/Eep/EepGeneral |
| EaBlockSize too small | PARAM_ADJUST | Add header + CRC overhead to NvMBlockLength |
