---
name: memstack-requirements
description: Use when user wants to configure, set up, or add blocks to the AUTOSAR memory stack and requirements have not yet been gathered
---

# Memory Stack Requirements Gathering

This skill gathers all information needed before any configuration work begins. Ask questions one at a time. Do not proceed to configuration until this skill is complete.

---

## When This Skill Activates

Invoke this skill BEFORE `memstack-configure` when the user says any of:
- "configure memory stack", "set up NvM", "add NvM blocks"
- "I need memory stack configuration", "let's set up the EEPROM blocks"
- Any request to start memory stack work where `memstack_input.json` does not yet exist

---

## Question Flow

Ask these questions **one at a time**. Wait for the answer before asking the next. Do not front-load all questions.

### Phase A — Block Inventory

**A1.** "How many NvM blocks do you need to configure?"

For each block (repeat A2–A8 per block):

**A2.** "What is the name of block N?" *(must be a valid C identifier: letters, digits, underscores, starts with letter/underscore)*

**A3.** "What is the data size of [BlockName] in bytes?" *(1–65535)*

**A4.** "What block type is [BlockName]?"
- `NATIVE` — single copy, no redundancy
- `REDUNDANT` — dual copy, required for ASIL >= B
- `DATASET` — multiple calibration variants

  If `DATASET`: "How many dataset instances does [BlockName] need?"

**A5.** "What is the ASIL level of [BlockName]?"
- `QM` — no safety requirement
- `ASIL_A`, `ASIL_B`, `ASIL_C`, `ASIL_D`

  ⚠️ If ASIL >= B and type is not REDUNDANT:
  "⚠️ [BlockName] is [ASIL] — this requires REDUNDANT block type and CRC. Shall I set it to REDUNDANT automatically?"

**A6.** "Does [BlockName] need CRC protection?" *(default: yes for ASIL >= A, recommended for all)*

**A7.** "What is the write policy for [BlockName]?"
- `DURING_WRITEALL` — written on NvM_WriteAll() (normal shutdown)
- `IMMEDIATE` — written immediately on NvM_WriteBlock() (crash/safety data)

  ⚠️ If IMMEDIATE: "Note: IMMEDIATE write blocks require a Fee sector partition and impact timing. Confirm?"

**A8.** "What is the job priority for [BlockName]?" *(0 = highest/immediate, 1–255 = queued; default 10)*

---

### Phase B — Hardware Target

**B1.** "What type of memory is the target hardware using?"
- `INTERNAL_FLASH` → will use Fee + Fls stack
- `EEPROM` → will use Ea + Eep stack

**B2.** "What is the flash/EEPROM sector start address?" *(hex, e.g. `0x00100000`)*

**B3.** "What is the physical sector size in bytes?" *(e.g., 4096 for typical NOR flash)*

**B4.** "How many sectors are available for the memory stack?" *(minimum 2 for Fee, recommended 3+)*

**B5.** "What is the write page size in bytes?" *(e.g., 8 for NOR flash, 64 for I2C EEPROM)*

**B6.** "What is the maximum erase cycle count for the hardware?" *(e.g., 100000)*

---

## Output: Generate Input Files

Once all answers are collected, generate and write both files:

### `memstack_input.json`
```json
{
  "blocks": [
    {
      "name": "<BlockName>",
      "size": <bytes>,
      "type": "<NATIVE|REDUNDANT|DATASET>",
      "asil": "<QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D>",
      "use_crc": <true|false>,
      "crc_type": "<CRC16|CRC32>",
      "write_policy": "<DURING_WRITEALL|IMMEDIATE>",
      "priority": <0-255>,
      "num_datasets": <N>
    }
  ]
}
```

Rules:
- `crc_type`: auto-determine if not specified — CRC16 for size <= 256, CRC32 for size > 256
- `use_crc`: always TRUE for ASIL >= B; recommended TRUE for all
- `type`: auto-upgrade to REDUNDANT if ASIL >= B and user confirms
- `num_datasets`: only include for DATASET type blocks

### `memory_hw_spec.json`
```json
{
  "memory_type": "<INTERNAL_FLASH|EEPROM>",
  "sectors": [
    { "start": "<0xADDRESS>", "size": <bytes>, "count": <N> }
  ],
  "page_size": <bytes>,
  "erase_value": "0xFF",
  "max_erase_cycles": <N>
}
```

---

## Validation Step

After writing both files, validate against schemas:
```bash
python3 -c "
import json, jsonschema
schema = json.load(open('schemas/nvm_input_schema.json'))
data = json.load(open('memstack_input.json'))
jsonschema.validate(data, schema)
print('memstack_input.json: valid')
"

python3 -c "
import json, jsonschema
schema = json.load(open('schemas/hw_memory_spec.json'))
data = json.load(open('memory_hw_spec.json'))
jsonschema.validate(data, schema)
print('memory_hw_spec.json: valid')
"
```

If either validation fails: fix the generated file and re-validate before proceeding.

---

## Budget Summary

After validation, compute and present the budget summary:
```bash
python scripts/analyze_input.py memstack_input.json memory_hw_spec.json -o build/analysis.json
```

Present to user:
```
Block Budget Summary:
  Total blocks:      N
  Total RAM bytes:   X bytes
  Total NV bytes:    Y bytes
  Available NV:      Z bytes
  Utilization:       P%

  ASIL blocks requiring special handling:
    - [BlockName]: ASIL_D → REDUNDANT + CRC32 + CalcRamBlockCrc

  [Any warnings about budget overruns or sector count]
```

⚠️ If any ASIL >= B blocks are present, explicitly confirm:
"[BlockName] is [ASIL] — it will be configured as REDUNDANT with CRC. Confirm this is intended."

---

## Completion

After the user confirms the budget summary and any ASIL flags:

> "Requirements gathered. Input files validated. Budget confirmed.
> Invoke `memstack-configure` to proceed with configuration against DaVinci Configurator."

Do NOT invoke `memstack-configure` automatically — the user must explicitly request it.
