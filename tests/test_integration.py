#!/usr/bin/env python3
"""
test_integration.py — End-to-end integration test for the memory stack pipeline.

Tests the full path: input → analyze → render ARXML → pre-validate ARXML.
Does NOT require DaVinci (no MCP calls) — tests everything Claude Code
controls before handing off to DVP.

Run: python -m pytest tests/test_integration.py -v
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "vector-davinci-mcp"))

import pytest
from jinja2 import Environment, FileSystemLoader
from lxml import etree

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
NS = "http://autosar.org/schema/r4.0"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analysis_fee(tmp_path):
    """Run full analysis for Fee (internal flash) variant."""
    from analyze_input import analyze
    input_data = json.loads((FIXTURES_DIR / "memstack_input_5blocks.json").read_text())
    hw_spec = json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())
    return analyze(input_data, hw_spec)


@pytest.fixture
def analysis_ea(tmp_path):
    """Run full analysis for Ea (EEPROM) variant."""
    from analyze_input import analyze
    input_data = json.loads((FIXTURES_DIR / "memstack_input_5blocks.json").read_text())
    hw_spec = {
        "memory_type": "EEPROM",
        "sectors": [{"start": "0x0000", "size": 256, "count": 4}],
        "page_size": 64,
        "erase_value": "0xFF",
        "max_erase_cycles": 1000000
    }
    result = analyze(input_data, hw_spec)
    # Add eep_config for the Eep template
    result["eep_config"] = {
        "base_address": "0x0000",
        "total_size": 32768,
        "page_size": 64,
    }
    return result


@pytest.fixture
def jinja_env():
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_and_parse(jinja_env, template_name, analysis):
    """Render a Jinja2 template and parse as XML."""
    template = jinja_env.get_template(template_name)
    arxml_text = template.render(**analysis)
    return etree.fromstring(arxml_text.encode("utf-8")), arxml_text


def find_short_names(root):
    """Extract all SHORT-NAME values from an ARXML tree."""
    return [
        elem.text
        for elem in root.iter(f"{{{NS}}}SHORT-NAME")
        if elem.text
    ]


# ---------------------------------------------------------------------------
# Fee/Fls Variant Tests
# ---------------------------------------------------------------------------

class TestFeeVariantPipeline:

    def test_analysis_produces_fee_type(self, analysis_fee):
        assert analysis_fee["memory_type"] == "FEE"

    def test_analysis_block_count(self, analysis_fee):
        assert len(analysis_fee["blocks"]) == 5

    def test_analysis_asil_flags(self, analysis_fee):
        assert "CrashData" in analysis_fee["asil_flags"]
        assert "SafetyCounter" in analysis_fee["asil_flags"]

    def test_analysis_crash_data_redundant(self, analysis_fee):
        crash = next(b for b in analysis_fee["blocks"] if b["name"] == "CrashData")
        assert "REDUNDANT" in crash["management_type"]
        assert crash["use_crc"] is True
        assert "CRC32" in crash["crc_type"]

    def test_fls_template_renders(self, jinja_env, analysis_fee):
        root, text = render_and_parse(jinja_env, "Fls_Config.arxml.j2", analysis_fee)
        names = find_short_names(root)
        assert "Fls" in names
        assert "FlsGeneral" in names
        assert any("FlsSector" in n for n in names)

    def test_fee_template_renders(self, jinja_env, analysis_fee):
        root, text = render_and_parse(jinja_env, "Fee_Config.arxml.j2", analysis_fee)
        names = find_short_names(root)
        assert "Fee" in names
        assert "FeeGeneral" in names
        assert "FeeBlock_VehicleOdometer" in names
        assert "FeeBlock_CrashData" in names

    def test_fee_block_count_matches_input(self, jinja_env, analysis_fee):
        root, _ = render_and_parse(jinja_env, "Fee_Config.arxml.j2", analysis_fee)
        fee_blocks = [
            n for n in find_short_names(root)
            if n.startswith("FeeBlock_")
        ]
        assert len(fee_blocks) == 5

    def test_fee_fls_reference_present(self, jinja_env, analysis_fee):
        root, text = render_and_parse(jinja_env, "Fee_Config.arxml.j2", analysis_fee)
        value_refs = [
            elem.text
            for elem in root.iter(f"{{{NS}}}VALUE-REF")
            if elem.text
        ]
        assert any("/AUTOSAR/Fls/FlsGeneral" in ref for ref in value_refs)

    def test_memif_template_renders(self, jinja_env, analysis_fee):
        root, text = render_and_parse(jinja_env, "MemIf_Config.arxml.j2", analysis_fee)
        names = find_short_names(root)
        assert "MemIf" in names
        assert "MemIfDevice_Fee" in names

    def test_memif_references_fee(self, jinja_env, analysis_fee):
        root, _ = render_and_parse(jinja_env, "MemIf_Config.arxml.j2", analysis_fee)
        value_refs = [
            elem.text
            for elem in root.iter(f"{{{NS}}}VALUE-REF")
            if elem.text
        ]
        assert any("/AUTOSAR/Fee" in ref for ref in value_refs)

    def test_nvm_template_renders(self, jinja_env, analysis_fee):
        root, text = render_and_parse(jinja_env, "NvM_Config.arxml.j2", analysis_fee)
        names = find_short_names(root)
        assert "NvM" in names
        assert "NvMCommon" in names
        assert "NvMBlockDescriptor_VehicleOdometer" in names
        assert "NvMBlockDescriptor_CrashData" in names

    def test_nvm_block_count_matches_input(self, jinja_env, analysis_fee):
        root, _ = render_and_parse(jinja_env, "NvM_Config.arxml.j2", analysis_fee)
        nvm_blocks = [
            n for n in find_short_names(root)
            if n.startswith("NvMBlockDescriptor_")
        ]
        assert len(nvm_blocks) == 5

    def test_nvm_references_fee_blocks(self, jinja_env, analysis_fee):
        root, _ = render_and_parse(jinja_env, "NvM_Config.arxml.j2", analysis_fee)
        value_refs = [
            elem.text
            for elem in root.iter(f"{{{NS}}}VALUE-REF")
            if elem.text
        ]
        fee_refs = [r for r in value_refs if "Fee" in r and "FeeBlock_" in r]
        assert len(fee_refs) == 5

    def test_nvm_crc_on_asil_blocks(self, jinja_env, analysis_fee):
        root, text = render_and_parse(jinja_env, "NvM_Config.arxml.j2", analysis_fee)
        # CrashData (ASIL_D) must have CRC
        assert "NvMBlockUseCrc" in text
        assert "NvMCalcRamBlockCrc" in text

    def test_all_arxml_well_formed(self, jinja_env, analysis_fee):
        """All 4 templates produce well-formed XML."""
        for template_name in [
            "Fls_Config.arxml.j2",
            "Fee_Config.arxml.j2",
            "MemIf_Config.arxml.j2",
            "NvM_Config.arxml.j2",
        ]:
            root, _ = render_and_parse(jinja_env, template_name, analysis_fee)
            assert root is not None

    def test_no_duplicate_short_names_per_template(self, jinja_env, analysis_fee):
        """No template produces duplicate SHORT-NAMEs at any level."""
        from validate_arxml import validate_arxml
        import tempfile, os

        for template_name in [
            "Fls_Config.arxml.j2",
            "Fee_Config.arxml.j2",
            "MemIf_Config.arxml.j2",
            "NvM_Config.arxml.j2",
        ]:
            _, text = render_and_parse(jinja_env, template_name, analysis_fee)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".arxml", delete=False
            ) as f:
                f.write(text)
                tmp_path = f.name
            try:
                errors = validate_arxml(tmp_path)
                assert errors == [], f"{template_name} has validation errors: {errors}"
            finally:
                os.unlink(tmp_path)

    def test_full_pipeline_to_files(self, jinja_env, analysis_fee, tmp_path):
        """Full pipeline: render all templates to files, validate all."""
        from validate_arxml import validate_arxml

        templates = [
            ("Fls", "Fls_Config.arxml.j2"),
            ("Fee", "Fee_Config.arxml.j2"),
            ("MemIf", "MemIf_Config.arxml.j2"),
            ("NvM", "NvM_Config.arxml.j2"),
        ]

        generated_files = []
        for module, template_name in templates:
            template = jinja_env.get_template(template_name)
            text = template.render(**analysis_fee)
            out_file = tmp_path / f"{module}_Config.arxml"
            out_file.write_text(text, encoding="utf-8")
            generated_files.append(str(out_file))

        # Validate all generated files
        all_errors = []
        for filepath in generated_files:
            errors = validate_arxml(filepath)
            if errors:
                all_errors.extend([(filepath, e) for e in errors])

        assert all_errors == [], f"Pipeline validation errors: {all_errors}"
        assert len(generated_files) == 4


# ---------------------------------------------------------------------------
# Ea/Eep Variant Tests
# ---------------------------------------------------------------------------

class TestEaVariantPipeline:

    def test_analysis_produces_ea_type(self, analysis_ea):
        assert analysis_ea["memory_type"] == "EA"

    def test_eep_template_renders(self, jinja_env, analysis_ea):
        root, text = render_and_parse(jinja_env, "Eep_Config.arxml.j2", analysis_ea)
        names = find_short_names(root)
        assert "Eep" in names
        assert "EepGeneral" in names

    def test_ea_template_renders(self, jinja_env, analysis_ea):
        root, text = render_and_parse(jinja_env, "Ea_Config.arxml.j2", analysis_ea)
        names = find_short_names(root)
        assert "Ea" in names
        assert "EaGeneral" in names
        assert "EaBlock_VehicleOdometer" in names

    def test_ea_references_eep(self, jinja_env, analysis_ea):
        root, _ = render_and_parse(jinja_env, "Ea_Config.arxml.j2", analysis_ea)
        value_refs = [
            elem.text
            for elem in root.iter(f"{{{NS}}}VALUE-REF")
            if elem.text
        ]
        assert any("/AUTOSAR/Eep/EepGeneral" in ref for ref in value_refs)

    def test_memif_routes_to_ea(self, jinja_env, analysis_ea):
        root, _ = render_and_parse(jinja_env, "MemIf_Config.arxml.j2", analysis_ea)
        names = find_short_names(root)
        assert "MemIfDevice_Ea" in names

    def test_nvm_references_ea_blocks(self, jinja_env, analysis_ea):
        root, _ = render_and_parse(jinja_env, "NvM_Config.arxml.j2", analysis_ea)
        value_refs = [
            elem.text
            for elem in root.iter(f"{{{NS}}}VALUE-REF")
            if elem.text
        ]
        ea_refs = [r for r in value_refs if "EaBlock_" in r]
        assert len(ea_refs) == 5, f"Expected 5 Ea block refs, got: {value_refs}"


# ---------------------------------------------------------------------------
# Budget & Wear Leveling Tests
# ---------------------------------------------------------------------------

class TestBudgetCalculations:

    def test_nv_budget_fits(self, analysis_fee):
        budget = analysis_fee["budget"]
        assert budget["total_nv_bytes"] <= budget["available_nv_bytes"]

    def test_utilization_reasonable(self, analysis_fee):
        budget = analysis_fee["budget"]
        assert 0 < budget["utilization_percent"] < 100

    def test_ram_budget_positive(self, analysis_fee):
        assert analysis_fee["budget"]["total_ram_bytes"] > 0

    def test_fee_sectors_at_least_3(self, analysis_fee):
        assert analysis_fee["fee_layout"]["sector_count"] >= 3

    def test_fee_sector_size_matches_fls(self, analysis_fee):
        assert (
            analysis_fee["fee_layout"]["sector_size"]
            == analysis_fee["fls_config"]["sector_size"]
        )

    def test_wear_leveling_data_present(self, analysis_fee):
        wl = analysis_fee["wear_leveling"]
        assert wl["max_erase_cycles"] > 0
        assert wl["total_available_writes"] > 0


# ---------------------------------------------------------------------------
# Cross-Module Consistency Tests
# ---------------------------------------------------------------------------

class TestCrossModuleConsistency:

    def test_fee_block_numbers_unique(self, analysis_fee):
        fee_nums = [b["fee_block_primary"] for b in analysis_fee["blocks"]]
        assert len(fee_nums) == len(set(fee_nums)), "Duplicate Fee block numbers"

    def test_nvm_ids_consecutive(self, analysis_fee):
        ids = [b["nvm_block_id"] for b in analysis_fee["blocks"]]
        expected = list(range(ids[0], ids[0] + len(ids)))
        assert ids == expected, f"Non-consecutive NvM IDs: {ids}"

    def test_fee_number_formula(self, analysis_fee):
        for block in analysis_fee["blocks"]:
            assert block["fee_block_primary"] == block["nvm_block_id"] * 2
            assert block["fee_block_redundant"] == block["nvm_block_id"] * 2 + 1

    def test_fee_block_size_covers_data(self, analysis_fee):
        for block in analysis_fee["blocks"]:
            minimum = block["size"] + 16 + block["crc_overhead"]  # data + header + CRC
            assert block["fee_block_size"] >= minimum, (
                f"Block {block['name']}: fee_block_size {block['fee_block_size']} "
                f"< minimum {minimum}"
            )

    def test_fee_block_size_aligned(self, analysis_fee):
        page_size = analysis_fee["fls_config"]["page_size"]
        for block in analysis_fee["blocks"]:
            assert block["fee_block_size"] % page_size == 0, (
                f"Block {block['name']}: fee_block_size {block['fee_block_size']} "
                f"not aligned to page_size {page_size}"
            )

    def test_redundant_blocks_have_crc(self, analysis_fee):
        for block in analysis_fee["blocks"]:
            if "REDUNDANT" in block["management_type"]:
                assert block["use_crc"] is True, (
                    f"Block {block['name']}: REDUNDANT without CRC"
                )

    def test_asil_blocks_are_redundant(self, analysis_fee):
        for block in analysis_fee["blocks"]:
            if block["asil"] in ("ASIL_B", "ASIL_C", "ASIL_D"):
                assert "REDUNDANT" in block["management_type"], (
                    f"Block {block['name']}: ASIL {block['asil']} but not REDUNDANT"
                )

    def test_immediate_blocks_have_priority_0(self, analysis_fee):
        for block in analysis_fee["blocks"]:
            if block["write_policy"] == "NVM_BLOCK_WRITE_IMMEDIATE":
                assert block["priority"] == 0, (
                    f"Block {block['name']}: IMMEDIATE write but priority != 0"
                )


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_single_block(self):
        from analyze_input import analyze
        input_data = {"blocks": [{"name": "Single", "size": 4, "type": "NATIVE"}]}
        hw_spec = json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())
        result = analyze(input_data, hw_spec)
        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["nvm_block_id"] == 2

    def test_large_block_crc32(self):
        from analyze_input import analyze
        input_data = {"blocks": [{
            "name": "BigBlock",
            "size": 4096,
            "type": "NATIVE",
            "use_crc": True,
        }]}
        hw_spec = json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())
        result = analyze(input_data, hw_spec)
        assert "CRC32" in result["blocks"][0]["crc_type"]

    def test_dataset_block(self):
        from analyze_input import analyze
        input_data = {"blocks": [{
            "name": "Dataset",
            "size": 128,
            "type": "DATASET",
            "num_datasets": 4,
        }]}
        hw_spec = json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())
        result = analyze(input_data, hw_spec)
        block = result["blocks"][0]
        assert block["copies"] == 4
        assert result["dataset_selection_bits"] == 2  # ceil(log2(4))

    def test_many_blocks_budget(self):
        from analyze_input import analyze
        blocks = [
            {"name": f"Block_{i}", "size": 64, "type": "NATIVE"}
            for i in range(50)
        ]
        input_data = {"blocks": blocks}
        hw_spec = json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())
        result = analyze(input_data, hw_spec)
        assert len(result["blocks"]) == 50
        assert result["budget"]["total_nv_bytes"] > 0

    def test_all_asil_d_blocks(self):
        from analyze_input import analyze
        blocks = [
            {"name": f"Safety_{i}", "size": 16, "type": "NATIVE", "asil": "ASIL_D"}
            for i in range(5)
        ]
        input_data = {"blocks": blocks}
        hw_spec = json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())
        result = analyze(input_data, hw_spec)
        for block in result["blocks"]:
            assert "REDUNDANT" in block["management_type"]
            assert block["use_crc"] is True
        assert len(result["asil_flags"]) == 5
