"""Pytest configuration and fixtures."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock
from agents.base_agent import AgentState
from examples.agents.parser_agent import ParserAgent
from examples.agents.analyzer_agent import AnalyzerAgent
from examples.agents.executor_agent import ExecutorAgent
from examples.agents.reporter_agent import ReporterAgent
from examples.agents.validator_agent import ValidatorAgent


@pytest.fixture
def sample_state():
    """Create sample agent state."""
    return {
        "input_data": {
            "content": "module test(input clk, output q); endmodule",
            "filename": "test.v",
        },
        "metadata": {},
    }

@pytest.fixture
def sample_parsed_data():
    """Sample parsed data."""
    return {
        "format": "netlist",
        "filename": "test.v",
        "data": {
            "modules": [{"name": "test", "ports": [], "instances": []}],
            "line_count": 1,
        },
    }

@pytest.fixture
def sample_config():
    """Sample configuration."""
    return {
        "llm": {"model": "llama3.1-70b-instruct", "temperature": 0.0},
        "guardrails": {"max_retries": 3, "auto_repair": True},
        "tools": {"timeout": 300},
        "output": {"format": "markdown"},
    }

@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"analysis": "Test analysis"}'
    mock.invoke.return_value = mock_response
    return mock

@pytest.fixture
def temp_schema_file():
    """Create temporary schema file."""
    schema = {
        "type": "object",
        "properties": {"test": {"type": "string"}},
        "required": ["test"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(schema, f)
        temp_path = Path(f.name)

    yield temp_path

    temp_path.unlink(missing_ok=True)

