---
name: validation-fixer
description: Use when DVP validation returns errors and ARXML patches need to be applied to achieve 0-error validation
---

# Validation Fixer Agent

## Purpose
Fix DVP validation errors through iterative validate → group → subagent-dispatch → patch → re-validate cycles. The parent agent stays lean; subagents handle per-error-group patching with only the relevant module context.

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
        STOP → present remaining errors + escalation_list to user

    # Step 1: Import ARXML into DVP
    davinci_import_arxml([
        "project/config/Fls_Config.arxml",   (or Eep)
        "project/config/Fee_Config.arxml",   (or Ea)
        "project/config/MemIf_Config.arxml",
        "project/config/NvM_Config.arxml"
    ])

    # Step 2: Run validation
    result = davinci_validate()

    # Step 3: Check for success
    if result.error_count == 0:
        git commit -m "post-validation: 0 errors after iteration {iteration}"
        RETURN { status: "PASS", iterations: iteration, escalations: escalation_list }

    # Step 4: Group errors by root container path
    errors_by_root = group_by_root_container(result.errors)
    # Fix root causes first to avoid wasting iterations on cascading errors

    # Step 5: Separate ESCALATE errors
    for error in all_errors:
        if error.category == "ESCALATE":
            escalation_list.append(error)
            remove from errors_by_root

    # Step 6: Dispatch one subagent per error group (in parallel if possible)
    patches = []
    for root_path, errors in errors_by_root:
        module = infer_module(root_path)   # e.g. "NvM", "Fee", "MemIf", "Fls"
        module_skill = MODULE_SKILL_MAP[module]

        # Dispatch subagent with minimal context (~500 tokens):
        patch = dispatch_subagent(
            context={
                "error_group": errors,          # only these errors, not all
                "root_path": root_path,
                "module_skill": module_skill,   # e.g. memstack-nvm
                "fix_skill": "arxml-validation-fix"
            },
            task="Generate ARXML patches for these specific validation errors. "
                 "Return a list of patches: [{file, old_content, new_content}]. "
                 "Fix root causes first. Do not guess — use the module skill formulas."
        )
        patches.extend(patch.patches)

    # Step 7: Apply all patches
    for patch in patches:
        apply_patch(patch.file, patch.old_content, patch.new_content)

    # Step 8: Git checkpoint
    git commit -m "validation-fix: iteration {iteration}, {len(patches)} patches applied"

    GOTO LOOP
```

## Module-to-Skill Mapping

```python
MODULE_SKILL_MAP = {
    "NvM":   "memstack-nvm",
    "Fee":   "memstack-fee",
    "Ea":    "memstack-ea",
    "MemIf": "memstack-memif",
    "Fls":   "memstack-fls-eep",
    "Eep":   "memstack-fls-eep",
}
```

## Error Grouping Strategy

```python
def group_by_root_container(errors):
    """
    Group errors by their root AUTOSAR container path.

    Example:
      /AUTOSAR/NvM/NvMBlockDescriptor_Odo/NvMBlockCrcType  → group: NvM/NvMBlockDescriptor_Odo
      /AUTOSAR/NvM/NvMBlockDescriptor_Odo/NvMTargetBlockRef → group: NvM/NvMBlockDescriptor_Odo
      /AUTOSAR/Fee/FeeBlock_Odo/FeeBlockSize                → group: Fee/FeeBlock_Odo

    Fix all errors in the same root container together before re-validating.
    Avoids wasting iterations on cascading errors from the same root cause.
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

## Subagent Context Format

Each subagent receives only:
1. The error group details (≤500 tokens): module, container path, error messages
2. The relevant module skill (`memstack-nvm`, `memstack-fee`, etc.)
3. The `arxml-validation-fix` skill

The subagent does NOT receive:
- Full error list from other groups
- Other module skills
- The complete ARXML files (it reads them directly if needed)

This keeps parent context lean: error summary + subagent results only.

## Subagent Patch Return Format

```json
{
    "root_path": "/AUTOSAR/NvM/NvMBlockDescriptor_Odo",
    "patches": [
        {
            "file": "project/config/NvM_Config.arxml",
            "description": "Set NvMBlockCrcType to NVM_CRC16 for Odo block",
            "old_content": "<ECUC-TEXTUAL-PARAM-VALUE>...",
            "new_content": "<ECUC-TEXTUAL-PARAM-VALUE>..."
        }
    ],
    "escalations": []
}
```

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
