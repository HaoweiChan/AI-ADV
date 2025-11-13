"""Tests for Guardrails integration."""

import json
import tempfile
from pathlib import Path

import pytest

from agents.validator_agent import ValidatorAgent


class TestGuardrailsIntegration:
    """Tests for Guardrails schema validation."""

    def test_load_schema(self):
        """Test loading JSON schema."""
        schema = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
            "required": ["test"],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(schema, f)
            temp_path = Path(f.name)

        agent = ValidatorAgent()
        agent.load_schema("test", temp_path)
        assert "test" in agent.schemas

        temp_path.unlink()

    def test_validate_valid_data(self):
        """Test validation with valid data."""
        schema = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
            "required": ["test"],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(schema, f)
            temp_path = Path(f.name)

        agent = ValidatorAgent()
        agent.load_schema("test", temp_path)
        valid_data = {"test": "value"}
        is_valid, _ = agent.validate_data(valid_data, "test")
        assert is_valid

        temp_path.unlink()

    def test_validate_invalid_data(self):
        """Test validation with invalid data."""
        schema = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
            "required": ["test"],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(schema, f)
            temp_path = Path(f.name)

        agent = ValidatorAgent()
        agent.load_schema("test", temp_path)
        invalid_data = {"wrong": "value"}
        is_valid, _ = agent.validate_data(invalid_data, "test")
        assert not is_valid

        temp_path.unlink()

    def test_auto_repair_enabled(self):
        """Test auto-repair functionality."""
        agent = ValidatorAgent({"auto_repair": True, "max_retries": 3})
        assert agent.auto_repair is True

    def test_auto_repair_disabled(self):
        """Test auto-repair when disabled."""
        agent = ValidatorAgent({"auto_repair": False})
        assert agent.auto_repair is False

