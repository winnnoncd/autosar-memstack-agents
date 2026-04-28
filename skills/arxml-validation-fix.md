---
name: arxml-validation-fix
description: >
  Catalog of DVP validation errors with automated fix strategies
  for the memory stack modules (NvM, Fee, Ea, MemIf, Fls, Eep).
---

# Validation Error → Fix Pattern Catalog

## Error Categories

| Category | Description | Action |
|---|---|---|
| AUTO_FIX | Deterministic fix, no domain judgment needed | Apply immediately |
| PARAM_ADJUST | Parameter value needs correction (range, formula) | Compute correct value, apply |
| MISSING_REF | Cross-module reference missing or broken | Add/fix reference element |
| STRUCTURAL | Missing container or sub-container | Generate and add ARXML fragment |
| ESCALATE | Requires human judgment (ASIL, OEM, architecture) | Collect, present to human |

## Fix Priority
1. Fix STRUCTURAL errors first (missing containers cause cascading ref errors)
2. Fix MISSING_REF errors (broken references cause downstream param errors)
3. Fix PARAM_ADJUST errors (value corrections)
4. Fix AUTO_FIX errors (cosmetic / ID issues)
5. Collect ESCALATE errors for human review

## Deduplication Strategy
DVP often reports cascading errors from a single root cause.
Before fixing:
1. Group errors by module + parent container path
2. If a container is missing (STRUCTURAL), all its child errors are cascading
3. Fix the root STRUCTURAL error → re-validate → child errors likely resolve
4. Only fix leaf errors after root causes are addressed

## Memory Stack Error Patterns

### NvM Errors
```
ECUC_NvM_xxxx: NvMTargetBlockReference unresolved
  → MISSING_REF
  → Fix: Create matching FeeBlockConfiguration or EaBlockConfiguration
  → FeeBlockNumber = NvMNvBlockNum × 2

ECUC_NvM_xxxx: NvMBlockCrcType not configured
  → PARAM_ADJUST
  → Fix: Set CRC16 if NvMBlockLength <= 256, else CRC32
  → Prerequisite: NvMBlockUseCrc must be TRUE

ECUC_NvM_xxxx: NvMCompiledConfigId invalid
  → AUTO_FIX
  → Fix: Set to unique 16-bit value (hash of timestamp)

ECUC_NvM_xxxx: NvMNvBlockNum duplicate
  → AUTO_FIX
  → Fix: Reassign block IDs consecutively from 2

ECUC_NvM_xxxx: NvMBlockManagementType missing for ASIL block
  → ESCALATE
  → Reason: Safety decision — human must confirm REDUNDANT type
```

### Fee Errors
```
ECUC_Fee_xxxx: FeeBlockSize smaller than required
  → PARAM_ADJUST
  → Fix: FeeBlockSize = align(NvMBlockLength + 16 + CRC_bytes, FlsPageSize)

ECUC_Fee_xxxx: FeeSectorSize does not match Fls
  → PARAM_ADJUST
  → Fix: Set FeeSectorSize = FlsSectorSize

ECUC_Fee_xxxx: FeeFlsReference unresolved
  → MISSING_REF
  → Fix: Add reference to /AUTOSAR/Fls/FlsGeneral

ECUC_Fee_xxxx: Missing FeeSectorConfiguration
  → STRUCTURAL
  → Fix: Add FeeSectorConfiguration container with size from Fls

ECUC_Fee_xxxx: Total block size exceeds available sector space
  → ESCALATE
  → Reason: May require adding more flash sectors or reducing block sizes
```

### MemIf Errors
```
ECUC_MemIf_xxxx: MemIfDeviceReference unresolved
  → MISSING_REF
  → Fix: Point to /AUTOSAR/Fee or /AUTOSAR/Ea

ECUC_MemIf_xxxx: Missing MemIfDevice container
  → STRUCTURAL
  → Fix: Add MemIfDevice with index 0 referencing Fee (or Ea)
```

### Fls Errors
```
ECUC_Fls_xxxx: FlsSectorSize = 0
  → PARAM_ADJUST
  → Fix: Set from memory_hw_spec.json sectors[].size

ECUC_Fls_xxxx: Missing FlsSectorConfiguration
  → STRUCTURAL
  → Fix: Add sector config from hardware spec
```

### General Cross-Module
```
"Unresolved reference to ..."
  → MISSING_REF
  → Fix: Trace the VALUE-REF path, create the target container

"Duplicate SHORT-NAME ..."
  → AUTO_FIX
  → Fix: Append unique suffix (_1, _2, etc.)

"Value out of range [min, max]"
  → PARAM_ADJUST
  → Fix: Clamp to the range specified in ECUC parameter definition

"Required parameter not set"
  → PARAM_ADJUST or STRUCTURAL
  → Fix: Set to default value from ECUC definition, or create if missing
```

## Fix Application

### ARXML Patch Strategy
Prefer editing ARXML files over PAI parameter sets because:
- ARXML edits are version-controllable (git diff)
- PAI changes are in-memory only until exported
- ARXML patches can be reviewed before re-import

Exception: single-parameter fixes are faster via PAI if WF license available
and the fix is a simple value change (not structural).

### Git Safety
Always `git commit` before applying patches:
```bash
git add project/config/*.arxml
git commit -m "pre-patch: validation iteration N"
```
This ensures reversibility per the harness design value.
