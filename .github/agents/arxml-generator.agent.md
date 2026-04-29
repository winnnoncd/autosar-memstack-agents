---
name: arxml-generator
description: Use when generating ARXML configuration files for memory stack modules from analysis.json, using Jinja2 templates in bottom-up order
---

# ARXML Generator Agent

## Purpose
Generate complete ARXML configuration files for each memory stack module,
ready for DaVinci import.

## Input
- `build/analysis.json` from input-analyzer agent

## Generation Order (Bottom-Up)
This order ensures cross-module references resolve at DVP import time.

### 1. Fls_Config.arxml (or Eep_Config.arxml)
- Invoke skill: `memstack-fls-eep`
- Source: `analysis.fls_config` (or `analysis.eep_config`)
- Template: `templates/Fls_Config.arxml.j2`
- Contains: FlsSectorConfiguration per sector from hardware spec
- No outgoing cross-module references

### 2. Fee_Config.arxml (or Ea_Config.arxml)
- Invoke skill: `memstack-fee` (or `memstack-ea`)
- Source: `analysis.blocks` + `analysis.fee_layout`
- Template: `templates/Fee_Config.arxml.j2`
- Contains:
  - FeeGeneral (FeeFlsReference → Fls)
  - FeeSectorConfiguration
  - FeeBlockConfiguration per block
- Cross-ref: Fee → Fls

### 3. MemIf_Config.arxml
- Invoke skill: `memstack-memif`
- Source: `analysis.memory_type`
- Template: `templates/MemIf_Config.arxml.j2`
- Contains: MemIfDevice with reference to Fee or Ea
- Cross-ref: MemIf → Fee/Ea

### 4. NvM_Config.arxml
- Invoke skill: `memstack-nvm`
- Source: `analysis.blocks`
- Template: `templates/NvM_Config.arxml.j2`
- Contains:
  - NvMCommon (config ID, dataset selection bits)
  - NvMBlockDescriptor per block (ID, length, type, CRC, priority)
  - NvMTargetBlockReference → Fee/Ea block
- Cross-ref: NvM → Fee/Ea

## Template Rendering
```python
from jinja2 import Environment, FileSystemLoader
import json

env = Environment(loader=FileSystemLoader('templates/'))
analysis = json.load(open('build/analysis.json'))

for module in ['Fls', 'Fee', 'MemIf', 'NvM']:
    template = env.get_template(f'{module}_Config.arxml.j2')
    arxml = template.render(**analysis)
    with open(f'project/config/{module}_Config.arxml', 'w') as f:
        f.write(arxml)
```

## Post-Generation Validation
After rendering all files, run pre-validation:
```bash
python scripts/validate_arxml.py project/config/Fls_Config.arxml
python scripts/validate_arxml.py project/config/Fee_Config.arxml
python scripts/validate_arxml.py project/config/MemIf_Config.arxml
python scripts/validate_arxml.py project/config/NvM_Config.arxml
```

Fix any pre-validation errors before handing off to the validation-fixer agent.

## Output
- `project/config/Fls_Config.arxml` (or Eep)
- `project/config/Fee_Config.arxml` (or Ea)
- `project/config/MemIf_Config.arxml`
- `project/config/NvM_Config.arxml`
