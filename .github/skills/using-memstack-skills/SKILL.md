---
name: using-memstack-skills
description: Use at session start or when uncertain which AUTOSAR memory stack skill applies
---

# Using AUTOSAR Memory Stack Skills

This skill is loaded at session start. It tells the agent HOW to use the domain skills — priority order, selection rules, and rationalization traps to avoid.

## Skill Priority Order

When answering any AUTOSAR memory stack question, apply this priority order:

**1. Process skills (RIGID — follow exactly, no adaptation):**

| Skill | When |
|---|---|
| `memstack-requirements` | User wants to configure, add blocks, or set up memory stack — invoke THIS FIRST |
| `memstack-configure` | Only after requirements are gathered and input files exist |
| `memstack-verification` | Before claiming configuration is complete; during ASIL review |
| `using-memstack-skills` | Session start; when uncertain which skill applies |

**2. Knowledge skills (flexible — adapt to context):**

| Skill | Invoke when |
|---|---|
| `memstack-nvm` | NvM blocks, block types, IDs, CRC, job priority |
| `memstack-fee` | Fee sectors, block sizing, wear leveling, FeeImmediateData |
| `memstack-ea` | Ea blocks, external EEPROM target |
| `memstack-memif` | MemIf device routing, NvM↔Fee/Ea connection |
| `memstack-fls-eep` | Fls sectors, Eep parameters, MCAL driver config |
| `arxml-generation` | ARXML authoring, ECUC structure, namespace, pre-validation |
| `arxml-validation-fix` | DVP validation errors, ARXML patch strategy |
| `davinci-cli-reference` | DaVinci CLI commands, PAI Groovy, MCP tool mapping |

---

## Rule 1: Invoke `memstack-requirements` BEFORE `memstack-configure`

If the user mentions configuring, setting up, adding blocks, or initializing the memory stack:

1. **Invoke `memstack-requirements` FIRST** — always, no exceptions
2. Only invoke `memstack-configure` after:
   - ✅ `memstack_input.json` exists and validates against `schemas/nvm_input_schema.json`
   - ✅ `memory_hw_spec.json` exists and validates against `schemas/hw_memory_spec.json`
   - ✅ User has confirmed the budget summary

Do NOT skip `memstack-requirements` because:
- The user "seems to know what they want"
- The user said "just configure it"
- The input files happen to already exist from a previous session
- You want to save time

---

## Rule 2: Invoke any skill with 1% relevance

If there is even a **1% chance** a domain skill applies, invoke it before answering.

Trigger topics: NvM, NVRAM, NvBlock, Fee, flash EEPROM emulation, Ea, EEPROM abstraction, MemIf, memory abstraction interface, Fls, Eep, MCAL, ARXML, ECUC, DaVinci, DVP, PAI, Groovy, memory stack, block configuration, CRC, ASIL, safety-critical storage, block ID, sector layout.

---

## Rationalization Red Flags

Stop and re-check your reasoning immediately if you are about to think or say any of the following. These are rationalization patterns — they feel like valid reasoning but they bypass required process:

| Red Flag Thought | Why It Is Wrong |
|---|---|
| "I already know the answer, I don't need the skill" | Domain skills contain exact MICROSAR-version-specific formulas and error patterns that general training misses |
| "The user didn't say NvM explicitly, so I'll skip memstack-nvm" | NvM is always involved in memory stack work; default to invoking it |
| "I'll skip memstack-requirements because the user gave me a JSON file" | Requirements gathering is mandatory — even if JSON exists, it must be validated and the budget confirmed |
| "I'll go straight to memstack-configure to be efficient" | Skipping requirements always requires backtracking — it costs more time, not less |
| "The validation error is obvious, I don't need arxml-validation-fix" | The error catalog contains non-obvious root causes and cascading-error patterns; do not guess |
| "ASIL is just metadata here, I can auto-approve" | NEVER. ASIL >= B requires mandatory human approval — this is a hard stop, not a suggestion |
| "I've done this before, I know the Fee block size formula" | Always check memstack-fee — the MICROSAR header size and CRC overhead vary by version |
| "There's only one block, I don't need the full workflow" | Rigid process skills apply regardless of block count |
| "Step X seems unnecessary for this simple case" | Rigid process skills have no optional steps. Follow every step |
| "The user wants fast results, I'll skip verification" | memstack-verification must run before claiming configuration complete |
| "I'll combine requirements and configuration into one step" | These are separate skills with a mandatory human confirmation gate between them |
| "The previous session already ran requirements, I'll skip it" | Each session must verify input files exist and are valid before proceeding |

---

## Skill Selection Quick Reference

```
User asks about...                    → Invoke
─────────────────────────────────────────────────────────────────
"configure memory stack"              → memstack-requirements (FIRST)
"add NvM blocks"                      → memstack-requirements (FIRST)
"set up NvM"                          → memstack-requirements (FIRST)
NvM block type / ID / CRC             → memstack-nvm
Fee sector / block size               → memstack-fee
Ea block / EEPROM target              → memstack-ea
MemIf routing / device index          → memstack-memif
Fls sector / Eep parameters           → memstack-fls-eep
ARXML structure / namespace           → arxml-generation
DVP validation error / fix            → arxml-validation-fix
DaVinci CLI / PAI / MCP tools         → davinci-cli-reference
"go ahead and configure"              → memstack-configure (only if input files valid)
"is the configuration complete?"      → memstack-verification
ASIL review                           → memstack-verification
```
