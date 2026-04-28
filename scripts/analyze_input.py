#!/usr/bin/env python3
"""
analyze_input.py — Analyze NvBlock descriptors and hardware spec,
compute all derived parameters for ARXML generation.

Usage:
    python scripts/analyze_input.py memstack_input.json memory_hw_spec.json -o build/analysis.json
"""

import argparse
import json
import math
import sys
from pathlib import Path


# MICROSAR Fee header overhead (bytes)
FEE_HEADER_OVERHEAD = 16

# CRC sizes
CRC_SIZES = {
    "CRC16": 2,
    "CRC32": 4,
    "NVM_CRC16": 2,
    "NVM_CRC32": 4,
}


def analyze(input_data: dict, hw_spec: dict) -> dict:
    """
    Compute complete memory stack layout from inputs.

    Returns analysis dict suitable for Jinja2 template rendering.
    """
    blocks = input_data["blocks"]
    memory_type = hw_spec["memory_type"]
    page_size = hw_spec["page_size"]

    # Determine Fee vs Ea
    use_fee = memory_type == "INTERNAL_FLASH"
    stack_type = "FEE" if use_fee else "EA"

    # Get sector info
    sector_info = hw_spec["sectors"][0]  # Primary sector group
    sector_size = sector_info["size"]
    available_sectors = sector_info["count"]

    # Process each block
    processed_blocks = []
    nvm_block_id = 2  # Start at 2 (0 and 1 are reserved)
    total_ram = 0
    total_nv = 0
    has_priority_blocks = False
    asil_flags = []
    warnings = []

    for block in blocks:
        name = block["name"]
        size = block["size"]
        block_type = block.get("type", "NATIVE")
        asil = block.get("asil", "QM")
        use_crc = block.get("use_crc", True)
        priority = block.get("priority", 10)
        write_policy = block.get("write_policy", "DURING_WRITEALL")
        num_datasets = block.get("num_datasets", 1)

        # Auto-determine CRC type if not specified
        if use_crc:
            crc_type = block.get("crc_type", "CRC32" if size > 256 else "CRC16")
        else:
            crc_type = ""

        # Auto-upgrade to REDUNDANT for ASIL >= B
        management_type = f"NVM_BLOCK_{block_type}"
        if asil in ("ASIL_B", "ASIL_C", "ASIL_D") and block_type != "REDUNDANT":
            management_type = "NVM_BLOCK_REDUNDANT"
            warnings.append(
                f"Block '{name}' upgraded to REDUNDANT (ASIL {asil} requires redundancy)"
            )

        # Auto-enable CRC for ASIL blocks
        if asil in ("ASIL_B", "ASIL_C", "ASIL_D") and not use_crc:
            use_crc = True
            crc_type = "CRC32" if size > 256 else "CRC16"
            warnings.append(
                f"Block '{name}' CRC enabled (ASIL {asil} requires CRC)"
            )

        # Compute derived values
        crc_overhead = CRC_SIZES.get(crc_type, 0) if use_crc else 0
        nvm_base_number = nvm_block_id * 2
        fee_block_primary = nvm_base_number
        fee_block_redundant = nvm_base_number + 1

        # Fee block size with alignment
        raw_fee_size = size + FEE_HEADER_OVERHEAD + crc_overhead
        fee_block_size = align_to(raw_fee_size, page_size)

        # Copies in NV
        is_redundant = "REDUNDANT" in management_type
        copies = 2 if is_redundant else (num_datasets if block_type == "DATASET" else 1)
        nv_usage = fee_block_size * copies

        # NvM write policy enum
        nvm_write_policy = (
            "NVM_BLOCK_WRITE_IMMEDIATE" if write_policy == "IMMEDIATE"
            else "NVM_BLOCK_WRITE_DURING_WRITEALL"
        )

        # CRC type enum
        nvm_crc_type = f"NVM_{crc_type}" if crc_type and not crc_type.startswith("NVM_") else crc_type

        # Budget tracking
        total_ram += size + crc_overhead
        total_nv += nv_usage

        if priority == 0:
            has_priority_blocks = True

        if asil in ("ASIL_B", "ASIL_C", "ASIL_D"):
            asil_flags.append(name)

        processed_blocks.append({
            "name": name,
            "nvm_block_id": nvm_block_id,
            "nvm_base_number": nvm_base_number,
            "fee_block_primary": fee_block_primary,
            "fee_block_redundant": fee_block_redundant,
            "size": size,
            "management_type": management_type,
            "use_crc": use_crc,
            "crc_type": nvm_crc_type,
            "crc_overhead": crc_overhead,
            "fee_block_size": fee_block_size,
            "priority": priority,
            "asil": asil,
            "write_policy": nvm_write_policy,
            "num_datasets": num_datasets,
            "copies": copies,
            "nv_usage": nv_usage,
            "default_value": block.get("default_value", "0x00"),
        })

        nvm_block_id += 1

    # Fee sector layout calculation
    # Need enough sectors for all blocks + 30% margin + 1 transfer sector
    usable_per_sector = sector_size * 0.9  # 90% fill threshold
    data_sectors_needed = math.ceil(total_nv / usable_per_sector)
    fee_sector_count = data_sectors_needed + 1  # +1 for transfer
    fee_sector_count = max(fee_sector_count, 3)  # Minimum 3 for safety

    if fee_sector_count > available_sectors:
        warnings.append(
            f"Need {fee_sector_count} Fee sectors but only {available_sectors} available. "
            f"Total NV: {total_nv} bytes, sector size: {sector_size} bytes."
        )

    # Dataset selection bits
    max_datasets = max((b["num_datasets"] for b in processed_blocks), default=1)
    dataset_selection_bits = math.ceil(math.log2(max_datasets)) if max_datasets > 1 else 0

    # NvM config ID (hash-based)
    config_id = hash(json.dumps(processed_blocks, sort_keys=True)) & 0xFFFF

    # Wear leveling assessment
    max_erase_cycles = hw_spec.get("max_erase_cycles", 100000)
    available_nv = min(fee_sector_count, available_sectors) * sector_size

    return {
        "memory_type": stack_type,
        "config_id": config_id,
        "dataset_selection_bits": dataset_selection_bits,
        "has_priority_blocks": has_priority_blocks,
        "blocks": processed_blocks,
        "budget": {
            "total_ram_bytes": total_ram,
            "total_nv_bytes": total_nv,
            "available_nv_bytes": available_nv,
            "utilization_percent": round(total_nv / available_nv * 100, 1) if available_nv > 0 else 0,
        },
        "fee_layout": {
            "sector_size": sector_size,
            "sector_count": min(fee_sector_count, available_sectors),
            "total_area": min(fee_sector_count, available_sectors) * sector_size,
        },
        "fls_config": {
            "sector_start": sector_info["start"],
            "sector_size": sector_size,
            "sector_count": available_sectors,
            "page_size": page_size,
            "erase_value": hw_spec.get("erase_value", "0xFF"),
            "max_erase_cycles": max_erase_cycles,
        },
        "asil_flags": asil_flags,
        "warnings": warnings,
        "wear_leveling": {
            "max_erase_cycles": max_erase_cycles,
            "total_available_writes": max_erase_cycles * min(fee_sector_count, available_sectors),
        },
        # Eep config (populated when memory_type == EEPROM)
        "eep_config": {
            "base_address": sector_info["start"],
            "total_size": sector_size * available_sectors,
            "page_size": page_size,
        } if not use_fee else {},
    }


def align_to(value: int, alignment: int) -> int:
    """Align value up to the nearest multiple of alignment."""
    return ((value + alignment - 1) // alignment) * alignment


def main():
    parser = argparse.ArgumentParser(description="Analyze memory stack inputs")
    parser.add_argument("input_file", help="Path to memstack_input.json")
    parser.add_argument("hw_spec_file", help="Path to memory_hw_spec.json")
    parser.add_argument("-o", "--output", default="build/analysis.json",
                        help="Output analysis file (default: build/analysis.json)")
    args = parser.parse_args()

    input_data = json.loads(Path(args.input_file).read_text())
    hw_spec = json.loads(Path(args.hw_spec_file).read_text())

    result = analyze(input_data, hw_spec)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2))

    # Print summary
    print(f"Memory type: {result['memory_type']}")
    print(f"Blocks: {len(result['blocks'])}")
    print(f"RAM budget: {result['budget']['total_ram_bytes']} bytes")
    print(f"NV budget: {result['budget']['total_nv_bytes']} bytes "
          f"({result['budget']['utilization_percent']}% of available)")
    print(f"Fee sectors: {result['fee_layout']['sector_count']} × {result['fee_layout']['sector_size']} bytes")
    print(f"ASIL blocks: {', '.join(result['asil_flags']) or 'none'}")

    if result["warnings"]:
        print(f"\nWarnings:")
        for w in result["warnings"]:
            print(f"  ⚠ {w}")

    print(f"\nAnalysis written to: {args.output}")


if __name__ == "__main__":
    main()
