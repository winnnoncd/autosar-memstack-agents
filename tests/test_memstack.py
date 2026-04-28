#!/usr/bin/env python3
"""
Unit tests for the memory stack configuration pipeline.

Run: python -m pytest tests/ -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add scripts and mcp-server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "vector-davinci-mcp"))

import pytest


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_input():
    return json.loads((FIXTURES_DIR / "memstack_input_5blocks.json").read_text())


@pytest.fixture
def sample_hw_spec():
    return json.loads((FIXTURES_DIR / "memory_hw_s32k.json").read_text())


# ---------------------------------------------------------------------------
# Input Analysis Tests
# ---------------------------------------------------------------------------

class TestInputAnalysis:

    def test_block_count(self, sample_input, sample_hw_spec):
        from analyze_input import analyze
        result = analyze(sample_input, sample_hw_spec)
        assert len(result["blocks"]) == 5

    def test_block_ids_start_at_2(self, sample_input, sample_hw_spec):
        from analyze_input import analyze
        result = analyze(sample_input, sample_hw_spec)
        ids = [b["nvm_block_id"] for b in result["blocks"]]
        assert ids[0] == 2
        assert ids == list(range(2, 2 + len(ids)))

    def test_fee_block_numbers(self, sample_input, sample_hw_spec):
        from analyze_input import analyze
        result = analyze(sample_input, sample_hw_spec)
        for block in result["blocks"]:
            assert block["fee_block_primary"] == block["nvm_block_id"] * 2
            assert block["fee_block_redundant"] == block["nvm_block_id"] * 2 + 1

    def test_memory_type_fee(self, sample_hw_spec):
        from analyze_input import analyze
        input_data = {"blocks": [{"name": "Test", "size": 8, "type": "NATIVE"}]}
        result = analyze(input_data, sample_hw_spec)
        assert result["memory_type"] == "FEE"

    def test_memory_type_ea(self, sample_hw_spec):
        from analyze_input import analyze
        hw = {**sample_hw_spec, "memory_type": "EEPROM"}
        input_data = {"blocks": [{"name": "Test", "size": 8, "type": "NATIVE"}]}
        result = analyze(input_data, hw)
        assert result["memory_type"] == "EA"

    def test_asil_upgrade_to_redundant(self, sample_hw_spec):
        from analyze_input import analyze
        input_data = {"blocks": [{
            "name": "Safety",
            "size": 16,
            "type": "NATIVE",
            "asil": "ASIL_B",
        }]}
        result = analyze(input_data, sample_hw_spec)
        block = result["blocks"][0]
        assert "REDUNDANT" in block["management_type"]
        assert block["use_crc"] is True
        assert "Safety" in result["asil_flags"]

    def test_crc_auto_type_small_block(self, sample_hw_spec):
        from analyze_input import analyze
        input_data = {"blocks": [{
            "name": "Small",
            "size": 4,
            "type": "NATIVE",
            "use_crc": True,
        }]}
        result = analyze(input_data, sample_hw_spec)
        assert "CRC16" in result["blocks"][0]["crc_type"]

    def test_crc_auto_type_large_block(self, sample_hw_spec):
        from analyze_input import analyze
        input_data = {"blocks": [{
            "name": "Large",
            "size": 512,
            "type": "NATIVE",
            "use_crc": True,
        }]}
        result = analyze(input_data, sample_hw_spec)
        assert "CRC32" in result["blocks"][0]["crc_type"]

    def test_fee_block_size_alignment(self, sample_hw_spec):
        from analyze_input import analyze
        input_data = {"blocks": [{
            "name": "Align",
            "size": 10,
            "type": "NATIVE",
            "use_crc": True,
            "crc_type": "CRC16",
        }]}
        result = analyze(input_data, sample_hw_spec)
        fee_size = result["blocks"][0]["fee_block_size"]
        page_size = sample_hw_spec["page_size"]
        assert fee_size % page_size == 0  # Must be page-aligned
        assert fee_size >= 10 + 16 + 2     # data + header + CRC

    def test_budget_calculation(self, sample_input, sample_hw_spec):
        from analyze_input import analyze
        result = analyze(sample_input, sample_hw_spec)
        assert result["budget"]["total_ram_bytes"] > 0
        assert result["budget"]["total_nv_bytes"] > 0
        assert result["budget"]["utilization_percent"] > 0

    def test_fee_sector_minimum_3(self, sample_hw_spec):
        from analyze_input import analyze
        input_data = {"blocks": [{"name": "Tiny", "size": 4, "type": "NATIVE"}]}
        result = analyze(input_data, sample_hw_spec)
        assert result["fee_layout"]["sector_count"] >= 3

    def test_priority_detection(self, sample_input, sample_hw_spec):
        from analyze_input import analyze
        result = analyze(sample_input, sample_hw_spec)
        # CrashData has priority 0
        assert result["has_priority_blocks"] is True


# ---------------------------------------------------------------------------
# ARXML Pre-Validation Tests
# ---------------------------------------------------------------------------

class TestARXMLValidation:

    def test_valid_arxml(self, tmp_path):
        from validate_arxml import validate_arxml
        arxml = tmp_path / "test.arxml"
        arxml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>Test</SHORT-NAME>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>''')
        errors = validate_arxml(str(arxml))
        assert errors == []

    def test_malformed_xml(self, tmp_path):
        from validate_arxml import validate_arxml
        arxml = tmp_path / "bad.arxml"
        arxml.write_text("<AUTOSAR><unclosed>")
        errors = validate_arxml(str(arxml))
        assert len(errors) > 0
        assert "syntax" in errors[0].lower()

    def test_duplicate_short_name(self, tmp_path):
        from validate_arxml import validate_arxml
        arxml = tmp_path / "dupe.arxml"
        arxml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<AUTOSAR xmlns="http://autosar.org/schema/r4.0">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>Dupe</SHORT-NAME>
    </AR-PACKAGE>
    <AR-PACKAGE>
      <SHORT-NAME>Dupe</SHORT-NAME>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>''')
        errors = validate_arxml(str(arxml))
        assert any("Duplicate" in e for e in errors)

    def test_missing_file(self):
        from validate_arxml import validate_arxml
        errors = validate_arxml("/nonexistent/file.arxml")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Validation Parser Tests
# ---------------------------------------------------------------------------

class TestValidationParser:

    def test_parse_xml_report(self, tmp_path):
        from validation_parser import parse_validation_report_xml
        report = tmp_path / "report.xml"
        report.write_text('''<?xml version="1.0"?>
<ValidationReport>
  <ValidationEntry>
    <Module>NvM</Module>
    <RuleId>ECUC_NvM_00123</RuleId>
    <Severity>ERROR</Severity>
    <Message>Unresolved reference to Fee block</Message>
    <ParameterPath>/AUTOSAR/NvM/NvMBlockDescriptor_Test/NvMTargetBlockReference</ParameterPath>
  </ValidationEntry>
  <ValidationEntry>
    <Module>Fee</Module>
    <RuleId>ECUC_Fee_00012</RuleId>
    <Severity>WARNING</Severity>
    <Message>FeeBlockSize smaller than required</Message>
  </ValidationEntry>
</ValidationReport>''')
        errors = parse_validation_report_xml(str(report))
        assert len(errors) == 2
        assert errors[0].module == "NvM"
        assert errors[0].severity == "ERROR"
        assert errors[1].module == "Fee"
        assert errors[1].severity == "WARNING"

    def test_parse_empty_report(self, tmp_path):
        from validation_parser import parse_validation_report_xml
        report = tmp_path / "empty.xml"
        report.write_text('<?xml version="1.0"?><ValidationReport/>')
        errors = parse_validation_report_xml(str(report))
        assert errors == []

    def test_parse_missing_file(self):
        from validation_parser import parse_validation_report_xml
        errors = parse_validation_report_xml("/nonexistent/report.xml")
        assert errors == []
