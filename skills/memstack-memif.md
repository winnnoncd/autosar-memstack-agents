---
name: memstack-memif
description: >
  MemIf (Memory Abstraction Interface) configuration patterns.
  Routes NvM requests to the correct lower-layer module (Fee or Ea).
---

# MemIf Configuration Patterns

## Purpose
MemIf is a thin routing layer between NvM and Fee/Ea.
It maps device indices to lower-layer modules.

## Configuration

### MemIfNumberOfDevices
- Typically 1 (single flash or single EEPROM)
- Set to 2 if using both internal flash (Fee) and external EEPROM (Ea)

### MemIfDevice Container
Each device needs a `MemIfDevice` container:
```xml
<ECUC-CONTAINER-VALUE>
  <SHORT-NAME>MemIfDevice_Fee</SHORT-NAME>
  <DEFINITION-REF>
    /MICROSAR/MemIf/MemIfDevice
  </DEFINITION-REF>
  <PARAMETER-VALUES>
    <ECUC-NUMERICAL-PARAM-VALUE>
      <DEFINITION-REF>/MICROSAR/MemIf/MemIfDevice/MemIfDeviceIndex</DEFINITION-REF>
      <VALUE>0</VALUE>
    </ECUC-NUMERICAL-PARAM-VALUE>
  </PARAMETER-VALUES>
  <REFERENCE-VALUES>
    <ECUC-REFERENCE-VALUE>
      <DEFINITION-REF DEST="ECUC-REFERENCE-DEF">
        /MICROSAR/MemIf/MemIfDevice/MemIfDeviceReference
      </DEFINITION-REF>
      <VALUE-REF DEST="ECUC-CONTAINER-VALUE">
        /AUTOSAR/Fee
      </VALUE-REF>
    </ECUC-REFERENCE-VALUE>
  </REFERENCE-VALUES>
</ECUC-CONTAINER-VALUE>
```

### Device Index Mapping
- Device 0: primary memory (usually Fee for internal flash)
- Device 1: secondary memory (Ea for external EEPROM, if present)
- NvM blocks reference the device index via Fee/Ea configuration

## Common Validation Errors

| Error | Category | Fix |
|---|---|---|
| MemIfDeviceReference unresolved | MISSING_REF | Point to /AUTOSAR/Fee or /AUTOSAR/Ea |
| MemIfNumberOfDevices mismatch | PARAM_ADJUST | Set to actual count of MemIfDevice containers |
| Missing MemIfDevice container | STRUCTURAL | Add MemIfDevice with correct index and reference |
