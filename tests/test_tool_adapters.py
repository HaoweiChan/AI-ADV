"""Tests for EDA tool adapters."""

from unittest.mock import MagicMock, patch

import pytest

from tools.base_adapter import BaseAdapter
from tools.openroad_adapter import OpenROADAdapter
from tools.opensta_adapter import OpenSTAAdapter
from tools.yosys_adapter import YosysAdapter


class TestBaseAdapter:
    """Tests for base adapter interface."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = BaseAdapter("test", {"test": "config"})
        assert adapter.name == "test"
        assert adapter.config == {"test": "config"}

    def test_validate_config(self):
        """Test configuration validation."""
        adapter = BaseAdapter("test")
        assert adapter.validate_config() is True


class TestOpenSTAAdapter:
    """Tests for OpenSTA adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = OpenSTAAdapter({"timeout": 600})
        assert adapter.name == "opensta"
        assert adapter.runner.timeout == 600

    def test_parse_timing_report(self):
        """Test timing report parsing."""
        adapter = OpenSTAAdapter()
        report = "Setup violation: 1.5\nHold violation: 0.8"
        result = adapter.parse_timing_report(report)
        assert "summary" in result
        assert result["summary"]["setup_violations"] > 0

    def test_parse_output(self):
        """Test output parsing."""
        adapter = OpenSTAAdapter()
        output = "Timing report\nSetup violation found"
        result = adapter.parse_output(output)
        assert "summary" in result


class TestOpenROADAdapter:
    """Tests for OpenROAD adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = OpenROADAdapter({"timeout": 600})
        assert adapter.name == "openroad"
        assert adapter.runner.timeout == 600

    def test_parse_drc_log(self):
        """Test DRC log parsing."""
        adapter = OpenROADAdapter()
        log = "ERROR: Spacing violation\nWARNING: Width issue"
        result = adapter.parse_drc_log(log)
        assert "summary" in result
        assert result["summary"]["total_errors"] > 0

    def test_parse_output(self):
        """Test output parsing."""
        adapter = OpenROADAdapter()
        output = "ERROR: DRC violation found"
        result = adapter.parse_output(output)
        assert "summary" in result


class TestYosysAdapter:
    """Tests for Yosys adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = YosysAdapter({"timeout": 600})
        assert adapter.name == "yosys"
        assert adapter.runner.timeout == 600

    def test_parse_statistics(self):
        """Test statistics parsing."""
        adapter = YosysAdapter()
        stats = "Number of modules: 5\nNumber of cells: 100"
        result = adapter.parse_statistics(stats)
        assert "design" in result
        assert "gates" in result

    def test_parse_output(self):
        """Test output parsing."""
        adapter = YosysAdapter()
        output = "Number of modules: 3"
        result = adapter.parse_output(output)
        assert "design" in result

