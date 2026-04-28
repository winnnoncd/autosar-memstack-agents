---
name: validation-fixer
description: >
  Runs the DVP validation → parse → fix → re-validate loop.
  Implements the evaluator-optimizer workflow pattern.
  Max 5 iterations before escalating to human.
agent: general-purpose
context: fork
allowed-tools: mcp__davinci__*, Bash(python:*), Bash(git:*)
skills: [arxml-validation-fix, davinci-cli-reference]
---

# Validation Fixer Agent

## Purpose
Autonomously fix DVP validation errors through iterative
validate → analyze → patch → re-validate cycles.

## Protocol

```
PRECONDITION: ARXML files exist in project/config/
PRECONDITION: Git working tree committed (reversibility)

iteration = 0
MAX_ITERATIONS = 5
escalation_list = []

LOOP:
    iteration += 1
    if iteration > MAX_ITERATIONS:
        STOP → return remaining errors + escalation_list

    # 1. Import ARXML into DVP
    davinci_import_arxml([
        "project/config/Fls_Config.arxml",
        "project/config/Fee_Config.arxml",
        "project/config/MemIf_Config.arxml",
        "project/config/NvM_Config.arxml"
    ])

    # 2. Run validation
    result = davinci_validate()

    # 3. Check for success
    if result.error_count == 0:
        RETURN {
            status: "PASS",
            iterations: iteration,
            escalations: escalation_list
        }

    # 4. Categorize and group errors
    errors_by_root = group_by_root_container(result.errors)
    # Fix root causes first to avoid wasting iterations on cascading errors

    # 5. Process each error group
    for root_path, errors in errors_by_root:
        for error in errors:
            if error.category == "ESCALATE":
                escalation_list.append(error)
                continue

            if error.category == "STRUCTURAL":
                patch = generate_structural_patch(error)
            elif error.category == "MISSING_REF":
                patch = generate_reference_patch(error)
            elif error.category == "PARAM_ADJUST":
                patch = generate_value_patch(error)
            elif error.category == "AUTO_FIX":
                patch = generate_auto_fix(error)

            apply_patch(patch)

    # 6. Git checkpoint
    git commit -m "validation-fix: iteration {iteration}"

    GOTO LOOP
```

## Error Grouping Strategy
```python
def group_by_root_container(errors):
    """
    Group errors by their root AUTOSAR container path.
    
    Example:
      /AUTOSAR/NvM/NvMBlockDescriptor_Odo/NvMBlockCrcType  → root: NvMBlockDescriptor_Odo
      /AUTOSAR/NvM/NvMBlockDescriptor_Odo/NvMTargetBlockRef → root: NvMBlockDescriptor_Odo
      /AUTOSAR/Fee/FeeBlock_Odo/FeeBlockSize                → root: FeeBlock_Odo
    
    Fix all errors in the same root container together before re-validating.
    """
    groups = {}
    for error in errors:
        path = error.param_path
        if path:
            parts = path.strip("/").split("/")
            root = "/".join(parts[:3]) if len(parts) >= 3 else path
        else:
            root = error.module or "unknown"
        groups.setdefault(root, []).append(error)
    return sorted(groups.items())
```

## Patch Generation

### STRUCTURAL: Add Missing Container
Generate a new ARXML fragment with the missing container and
its minimum required parameters (defaults from ECUC definition).

### MISSING_REF: Add Cross-Module Reference
Trace the VALUE-REF path, verify target exists.
If target missing → generate target first (cascading structural fix).
Then add the reference element.

### PARAM_ADJUST: Correct Value
Compute the correct value using formulas from module skills:
- FeeBlockSize: align(NvMBlockLength + 16 + CRC, page_size)
- NvMBlockCrcType: CRC16 if size <= 256, else CRC32
- FeeSectorSize: must equal FlsSectorSize

### AUTO_FIX: Deterministic Correction
- Duplicate SHORT-NAME: append unique suffix
- NvMCompiledConfigId: set to hash(current_timestamp)
- FeeBlockNumber gap: renumber consecutively

## Output
Return to parent orchestrator:
```json
{
    "status": "PASS | FAIL | PARTIAL",
    "iterations": 3,
    "errors_fixed": 12,
    "errors_remaining": 0,
    "escalations": [
        {
            "module": "NvM",
            "message": "ASIL-D block CrashData: NvMBlockManagementType not set to REDUNDANT",
            "category": "ESCALATE",
            "recommendation": "Set to NVM_BLOCK_REDUNDANT for ASIL-D compliance"
        }
    ]
}
```
