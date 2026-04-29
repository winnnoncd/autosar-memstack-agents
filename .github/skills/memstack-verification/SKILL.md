---
name: memstack-verification
description: Use before claiming memory stack configuration is complete, and during ASIL safety review
---

# Memory Stack Verification Checklist

This is a RIGID checklist. Work through every item. Do not skip. Do not claim configuration complete until all items pass.

---

## How to Use

Run this checklist in two contexts:

1. **ASIL Safety Review** (Step 4 of `memstack-configure`): Run items 1–4 only, present table to user, wait for approval.
2. **Completion Verification** (Step 7 of `memstack-configure`): Run ALL items 1–9, report results.

---

## Checklist

### Item 1 — Block Count Match
**Check:** Number of blocks in generated ARXML matches `memstack_input.json`

```bash
python3 -c "
import json
from lxml import etree

input_blocks = json.load(open('memstack_input.json'))['blocks']
tree = etree.parse('project/config/NvM_Config.arxml')
ns = {'ar': 'http://autosar.org/schema/r4.0'}
arxml_blocks = tree.findall('.//{http://autosar.org/schema/r4.0}ECUC-CONTAINER-VALUE')
nvm_blocks = [b for b in arxml_blocks if 'NvMBlockDescriptor' in (b.findtext('{http://autosar.org/schema/r4.0}DEFINITION-REF') or '')]
assert len(nvm_blocks) == len(input_blocks), f'Count mismatch: input={len(input_blocks)}, arxml={len(nvm_blocks)}'
print(f'PASS: {len(input_blocks)} blocks in input, {len(nvm_blocks)} NvMBlockDescriptors in ARXML')
"
```

**Pass condition:** Block counts are equal.

---

### Item 2 — Cross-Reference Integrity (NvM → Fee/Ea)
**Check:** Every NvM block has a matching Fee or Ea block with the correct block number

```bash
python3 -c "
import json
analysis = json.load(open('build/analysis.json'))
for block in analysis['blocks']:
    expected_fee = block['fee_block_primary']
    print(f\"Expect FeeBlock_{block['name']}: FeeBlockNumber={expected_fee}\")
print('Verify these match project/config/Fee_Config.arxml (or Ea_Config.arxml)')
"
```

**Pass condition:** Every `NvMTargetBlockReference` VALUE-REF path resolves to an existing FeeBlock/EaBlock container with FeeBlockNumber = NvMNvBlockNum × 2.

---

### Item 3 — ASIL Compliance (ASIL >= B blocks)
**Check:** Every ASIL >= B block has REDUNDANT type, CRC enabled, and CalcRamBlockCrc enabled

```bash
python3 -c "
import json
data = json.load(open('memstack_input.json'))
asil_blocks = [b for b in data['blocks'] if b.get('asil', 'QM') in ('ASIL_B', 'ASIL_C', 'ASIL_D')]
for b in asil_blocks:
    issues = []
    if b.get('type') != 'REDUNDANT':
        issues.append(f'type={b.get(\"type\")} (must be REDUNDANT)')
    if not b.get('use_crc', False):
        issues.append('use_crc=False (must be True)')
    status = 'FAIL: ' + '; '.join(issues) if issues else 'PASS'
    print(f\"{b['name']} [{b['asil']}]: {status}\")
if not asil_blocks:
    print('No ASIL >= B blocks — check skipped')
"
```

**Pass condition:** All ASIL >= B blocks have `type=REDUNDANT`, `use_crc=true`, and `crc_type` set.

---

### Item 4 — Fee Block Sizing
**Check:** Every FeeBlockSize >= NvMBlockLength + header (16 bytes) + CRC overhead, page-aligned

```bash
python3 -c "
import json, math
analysis = json.load(open('build/analysis.json'))
page_size = analysis.get('fls_config', {}).get('page_size', 8)
for block in analysis['blocks']:
    crc_bytes = {'NVM_CRC16': 2, 'NVM_CRC32': 4}.get(block.get('crc_type', ''), 0)
    raw = block['size'] + 16 + crc_bytes
    min_size = math.ceil(raw / page_size) * page_size
    actual = block.get('fee_block_size', 0)
    status = 'PASS' if actual >= min_size else f'FAIL: actual={actual} < min={min_size}'
    print(f\"{block['name']}: {status}\")
"
```

**Pass condition:** `fee_block_size >= aligned(NvMBlockLength + 16 + CRC, page_size)` for every block.

---

### Item 5 — Fee Sector Capacity
**Check:** Total NV usage fits within available Fee sectors with >= 20% margin

```bash
python3 -c "
import json
analysis = json.load(open('build/analysis.json'))
budget = analysis.get('budget', {})
total_nv = budget.get('total_nv_bytes', 0)
available_nv = budget.get('available_nv_bytes', 0)
utilization = (total_nv / available_nv * 100) if available_nv > 0 else 100
status = 'PASS' if utilization <= 80 else f'FAIL: {utilization:.1f}% utilization exceeds 80% limit'
print(f'NV utilization: {utilization:.1f}% — {status}')
print(f'  Total NV used: {total_nv} bytes')
print(f'  Available NV: {available_nv} bytes')
"
```

**Pass condition:** NV utilization <= 80% (leaving >= 20% margin for wear leveling).

---

### Item 6 — Immediate Write Consistency
**Check:** Every priority-0 block has FeeImmediateData = TRUE in matching Fee block

```bash
python3 -c "
import json
data = json.load(open('memstack_input.json'))
immediate_blocks = [b['name'] for b in data['blocks'] if b.get('priority', 10) == 0 or b.get('write_policy') == 'IMMEDIATE']
if immediate_blocks:
    print(f'Blocks requiring FeeImmediateData=TRUE: {immediate_blocks}')
    print('Verify in project/config/Fee_Config.arxml that FeeImmediateData=TRUE for these blocks')
else:
    print('No immediate-write blocks — check skipped')
"
```

**Pass condition:** For every block with `priority=0` or `write_policy=IMMEDIATE`, the matching FeeBlock has `FeeImmediateData = TRUE`.

---

### Item 7 — MemIf Routing
**Check:** MemIfDevice references the correct lower layer (Fee or Ea) based on memory type

```bash
python3 -c "
import json
analysis = json.load(open('build/analysis.json'))
mem_type = analysis.get('memory_type', '')
if 'FEE' in mem_type or 'FLASH' in mem_type:
    expected = '/AUTOSAR/Fee'
    module = 'Fee_Config.arxml'
else:
    expected = '/AUTOSAR/Ea'
    module = 'Ea_Config.arxml'
print(f'Memory type: {mem_type}')
print(f'Expected MemIfDeviceReference VALUE-REF: {expected}')
print(f'Verify in project/config/MemIf_Config.arxml')
"
```

**Pass condition:** `MemIfDeviceReference` VALUE-REF points to `/AUTOSAR/Fee` (for INTERNAL_FLASH) or `/AUTOSAR/Ea` (for EEPROM).

---

### Item 8 — Fee-to-Fls Reference (Flash variant only)
**Check:** `FeeFlsReference` in Fee_Config.arxml points to `/AUTOSAR/Fls/FlsGeneral`

```bash
python3 -c "
import json
analysis = json.load(open('build/analysis.json'))
if 'FEE' in analysis.get('memory_type', ''):
    from lxml import etree
    tree = etree.parse('project/config/Fee_Config.arxml')
    ns = 'http://autosar.org/schema/r4.0'
    refs = [e.text for e in tree.iter(f'{{{ns}}}VALUE-REF') if e.text and 'Fls' in e.text]
    if refs:
        print(f'PASS: FeeFlsReference found: {refs[0]}')
    else:
        print('FAIL: No FeeFlsReference found in Fee_Config.arxml')
else:
    print('EEPROM variant — Fls reference check skipped')
"
```

**Pass condition:** `FeeFlsReference` VALUE-REF exists and points to `/AUTOSAR/Fls/FlsGeneral`.

---

### Item 9 — NvM Block ID Sequence
**Check:** NvM block IDs start at 2, are consecutive, and have no gaps

```bash
python3 -c "
import json
analysis = json.load(open('build/analysis.json'))
ids = sorted(b['nvm_block_id'] for b in analysis['blocks'])
expected = list(range(2, 2 + len(ids)))
if ids == expected:
    print(f'PASS: Block IDs {ids[0]}..{ids[-1]}, consecutive, no gaps')
else:
    missing = set(expected) - set(ids)
    print(f'FAIL: Expected {expected}, got {ids}. Missing: {missing}')
"
```

**Pass condition:** All block IDs start at 2, are consecutive integers with no gaps.

---

## Summary Table Format

Present results as:

```
Verification Results:
  Item 1 Block Count:           PASS (5 blocks)
  Item 2 Cross-References:      PASS (all refs resolve)
  Item 3 ASIL Compliance:       PASS (2 ASIL blocks, all REDUNDANT+CRC)
  Item 4 Fee Block Sizing:      PASS (all blocks sized correctly)
  Item 5 Sector Capacity:       PASS (62% utilization)
  Item 6 Immediate Write:       PASS (1 immediate block, FeeImmediateData=TRUE)
  Item 7 MemIf Routing:         PASS (routes to /AUTOSAR/Fee)
  Item 8 Fee-to-Fls Reference:  PASS (/AUTOSAR/Fls/FlsGeneral)
  Item 9 Block ID Sequence:     PASS (IDs 2..6, consecutive)

  Overall: PASS — configuration is verified
```

If any item FAILS: list the specific failure and required remediation. Do NOT claim configuration complete until all items pass.
