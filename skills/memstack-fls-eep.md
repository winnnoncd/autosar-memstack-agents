---
name: memstack-fls-eep
description: >
  Fls (Flash driver) and Eep (EEPROM driver) MCAL configuration.
  Bottom of the memory stack — defines physical memory geometry.
---

# Fls / Eep Configuration Patterns

## Fls (Flash Driver)

### FlsSector Definitions
Each physical flash sector needs a `FlsSectorConfiguration`:
```xml
<ECUC-CONTAINER-VALUE>
  <SHORT-NAME>FlsSector_0</SHORT-NAME>
  <DEFINITION-REF>/MICROSAR/Fls/FlsSectorConfiguration</DEFINITION-REF>
  <PARAMETER-VALUES>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Fls/FlsSectorConfiguration/FlsSectorStartAddress</DEFINITION-REF>
      <VALUE>0x00100000</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Fls/FlsSectorConfiguration/FlsSectorSize</DEFINITION-REF>
      <VALUE>4096</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Fls/FlsSectorConfiguration/FlsNumberOfSectors</DEFINITION-REF>
      <VALUE>8</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Fls/FlsSectorConfiguration/FlsPageSize</DEFINITION-REF>
      <VALUE>8</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
  </PARAMETER-VALUES>
</ECUC-CONTAINER-VALUE>
```

### Key Fls Parameters
- FlsSectorStartAddress: base address of flash region allocated for Fee
- FlsSectorSize: physical erase sector size (from MCU datasheet)
- FlsNumberOfSectors: how many sectors allocated for Fee
- FlsPageSize: minimum write granularity (Fee block alignment)
- FlsEraseValue: typically 0xFF for NOR flash
- FlsMaxReadSize: max bytes per read call
- FlsMaxWriteSize: max bytes per write call

### Fls-to-Fee Linkage
Fee's FeeSectorSize **must equal** FlsSectorSize.
Fee's total area = FlsNumberOfSectors × FlsSectorSize.

## Eep (EEPROM Driver)

### Key Eep Parameters
- EepBaseAddress: start address of EEPROM device
- EepSize: total EEPROM size in bytes
- EepPageSize: write page size (typical: 32, 64, 128 bytes for I2C EEPROM)
- EepEraseValue: typically 0xFF
- EepBusType: I2C or SPI

### Eep Configuration
```xml
<ECUC-CONTAINER-VALUE>
  <SHORT-NAME>EepGeneral</SHORT-NAME>
  <DEFINITION-REF>/MICROSAR/Eep/EepGeneral</DEFINITION-REF>
  <PARAMETER-VALUES>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Eep/EepGeneral/EepBaseAddress</DEFINITION-REF>
      <VALUE>0x0000</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/Eep/EepGeneral/EepSize</DEFINITION-REF>
      <VALUE>32768</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
  </PARAMETER-VALUES>
</ECUC-CONTAINER-VALUE>
```

## Deriving Parameters from Hardware Spec

Given `memory_hw_spec.json`:
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

Mapping:
- memory_type = "INTERNAL_FLASH" → use Fls + Fee
- memory_type = "EEPROM" → use Eep + Ea
- sectors[0].start → FlsSectorStartAddress
- sectors[0].size → FlsSectorSize = FeeSectorSize
- sectors[0].count → FlsNumberOfSectors (must be >= 2 for Fee)
- page_size → FlsPageSize (Fee block alignment boundary)
- erase_value → FlsEraseValue

## Common Validation Errors

| Error | Category | Fix |
|---|---|---|
| FlsSectorSize mismatch with Fee | PARAM_ADJUST | Ensure FeeSectorSize = FlsSectorSize |
| FlsPageSize = 0 | PARAM_ADJUST | Set to actual page size from MCU datasheet |
| FlsSectorStartAddress overlap | PARAM_ADJUST | Verify sectors don't overlap with application code |
| Missing FlsSectorConfiguration | STRUCTURAL | Add sector definition per hardware spec |
