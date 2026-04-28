---
name: arxml-generation
description: >
  ARXML authoring rules for AUTOSAR R4.x ECUC configuration.
  Covers namespace, container structure, cross-module references,
  and pre-validation with Python/lxml.
---

# ARXML Generation Rules

## Namespace and Schema
```xml
<?xml version="1.0" encoding="UTF-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://autosar.org/schema/r4.0 AUTOSAR_00049.xsd">
```
- R4.4: AUTOSAR_00049.xsd
- R4.5+: AUTOSAR_00050.xsd
- Check SIP version to determine correct schema

## ECUC Container Structure
```
AUTOSAR
  └── AR-PACKAGES
        └── AR-PACKAGE (SHORT-NAME: "AUTOSAR")
              └── AR-PACKAGES
                    └── AR-PACKAGE (SHORT-NAME: "<ModuleName>")
                          └── ELEMENTS
                                └── ECUC-MODULE-CONFIGURATION-VALUES
                                      └── CONTAINERS
                                            └── ECUC-CONTAINER-VALUE (per instance)
```

## Parameter Value Types
- **ECUC-NUMERICAL-PARAM-VALUE**: integers, booleans (0/1), floats
- **ECUC-TEXTUAL-PARAM-VALUE**: enumerations, strings
- **ECUC-REFERENCE-VALUE**: cross-module references

## DEFINITION-REF Rules
- Always include DEST attribute matching the parameter definition type
- Path format: `/MICROSAR/<Module>/<Container>/<Parameter>`
- For Vector MICROSAR, use `/MICROSAR/` prefix (not `/AUTOSAR_MOD_ECUConfigurationParameters/`)

## Cross-Module Reference Patterns

### NvM → Fee
```xml
<ECUC-REFERENCE-VALUE>
  <DEFINITION-REF DEST="ECUC-CHOICE-REFERENCE-DEF">
    /MICROSAR/NvM/NvMBlockDescriptor/NvMTargetBlockReference
  </DEFINITION-REF>
  <VALUE-REF DEST="ECUC-CONTAINER-VALUE">
    /AUTOSAR/Fee/FeeBlockConfiguration/FeeBlock_<Name>
  </VALUE-REF>
</ECUC-REFERENCE-VALUE>
```

### Fee → Fls
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

### MemIf → Fee
```xml
<ECUC-REFERENCE-VALUE>
  <DEFINITION-REF DEST="ECUC-REFERENCE-DEF">
    /MICROSAR/MemIf/MemIfDevice/MemIfDeviceReference
  </DEFINITION-REF>
  <VALUE-REF DEST="ECUC-CONTAINER-VALUE">
    /AUTOSAR/Fee
  </VALUE-REF>
</ECUC-REFERENCE-VALUE>
```

## SHORT-NAME Rules
- Must be unique within parent container
- No spaces, start with letter or underscore
- Convention: `<ModuleName>_<Descriptor>` (e.g., `NvMBlockDescriptor_VehicleOdo`)
- Fee blocks: `FeeBlock_<NvMBlockName>` (maintains traceability)

## Pre-Validation Script
Run before DVP import to catch issues early (saves 15-30s DVP startup):

```python
# scripts/validate_arxml.py
from lxml import etree
import sys

def validate_arxml(filepath):
    """Pre-validate ARXML before DVP import."""
    errors = []

    # 1. Parse XML
    try:
        tree = etree.parse(filepath)
    except etree.XMLSyntaxError as e:
        return [f"XML syntax error: {e}"]

    root = tree.getroot()
    ns = {'ar': 'http://autosar.org/schema/r4.0'}

    # 2. Check no duplicate SHORT-NAMEs in same parent
    for parent in root.iter():
        names = [
            child.text
            for child in parent
            if child.tag.endswith('SHORT-NAME') and child.text
        ]
        seen = set()
        for name in names:
            if name in seen:
                errors.append(f"Duplicate SHORT-NAME '{name}' in {parent.tag}")
            seen.add(name)

    # 3. Check all DEFINITION-REFs have DEST attribute
    for defref in root.iter('{http://autosar.org/schema/r4.0}DEFINITION-REF'):
        if 'DEST' not in defref.attrib:
            errors.append(f"DEFINITION-REF missing DEST: {defref.text}")

    # 4. Check VALUE-REFs point to plausible paths
    for valref in root.iter('{http://autosar.org/schema/r4.0}VALUE-REF'):
        path = valref.text or ""
        if not path.startswith("/"):
            errors.append(f"VALUE-REF not absolute path: {path}")

    # 5. Check numerical values are valid
    for numval in root.iter('{http://autosar.org/schema/r4.0}VALUE'):
        text = (numval.text or "").strip()
        if text and not _is_valid_value(text):
            errors.append(f"Invalid numerical value: {text}")

    return errors

def _is_valid_value(text):
    """Check if value is valid integer, float, hex, or boolean."""
    if text.lower() in ('true', 'false', '0', '1'):
        return True
    try:
        if text.startswith('0x') or text.startswith('0X'):
            int(text, 16)
        else:
            float(text)
        return True
    except ValueError:
        return False
```

## Template Rendering Order
Generate ARXML files **bottom-up** to ensure references resolve:
1. Fls_Config.arxml (or Eep_Config.arxml) — no outgoing references
2. Fee_Config.arxml (or Ea_Config.arxml) — references Fls/Eep
3. MemIf_Config.arxml — references Fee/Ea
4. NvM_Config.arxml — references Fee/Ea blocks

Import into DVP in the same order.
