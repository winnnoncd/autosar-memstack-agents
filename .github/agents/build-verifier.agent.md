---
name: build-verifier
description: Use when verifying that DaVinci-generated BSW code compiles and passes MISRA-C static analysis
---

# Build Verifier Agent

## Purpose
Verify that DaVinci-generated BSW code compiles cleanly
and passes MISRA-C static analysis.

## Steps

### 1. Compilation
```bash
# Adapt to project's build system
make -C bsw/ all ARCH=<target> 2>&1 | tee build/build_log.txt
```

If no Makefile, attempt direct compilation of generated files:
```bash
# Compile generated memory stack sources
gcc -c -Wall -Werror \
    -I generated/include \
    -I bsw/include \
    generated/NvM/src/*.c \
    generated/Fee/src/*.c \
    generated/MemIf/src/*.c \
    generated/Fls/src/*.c \
    2>&1 | tee build/build_log.txt
```

### 2. MISRA-C Analysis (if available)
```bash
# If cppcheck is available
cppcheck --enable=all --std=c99 \
    --suppress=missingInclude \
    --addon=misra \
    generated/NvM/src/*.c \
    generated/Fee/src/*.c \
    2>&1 | tee build/misra_log.txt
```

### 3. Result Collection
Parse build and MISRA logs, return structured result:

```json
{
    "build_status": "PASS | FAIL",
    "warnings": ["warning: unused variable 'x' in NvM_Cfg.c:123"],
    "errors": [],
    "misra_violations": [
        {
            "file": "NvM_Cfg.c",
            "line": 45,
            "rule": "Rule 10.4",
            "message": "Essential type mismatch"
        }
    ],
    "files_compiled": 12,
    "total_warnings": 3,
    "total_errors": 0,
    "total_misra_violations": 1
}
```

## Error Handling
- If build fails: report errors, do NOT retry (likely config issue → needs validation-fixer)
- If MISRA tool not available: skip MISRA, report "MISRA check skipped — tool not found"
- Generated code compilation errors are unusual — likely indicate a DVP generation issue
