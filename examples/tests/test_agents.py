"""Unit tests for agent nodes."""

import pytest
from unittest.mock import MagicMock
from .conftest import mock_llm, sample_config, sample_parsed_data, sample_state
from agents.base_agent import AgentState
from examples.agents.parser_agent import ParserAgent
from examples.agents.analyzer_agent import AnalyzerAgent
from examples.agents.executor_agent import ExecutorAgent
from examples.agents.reporter_agent import ReporterAgent
from examples.agents.validator_agent import ValidatorAgent


class TestParserAgent:
    """Tests for ParserAgent."""

    def test_parse_json(self):
        """Test JSON parsing."""
        agent = ParserAgent()
        content = '{"test": "value"}'
        result = agent.parse_json(content)
        assert result == {"test": "value"}

    def test_parse_csv(self):
        """Test CSV parsing."""
        agent = ParserAgent()
        content = "col1,col2\nval1,val2"
        result = agent.parse_csv(content)
        assert len(result) == 1
        assert result[0]["col1"] == "val1"

    def test_parse_netlist(self):
        """Test netlist parsing."""
        agent = ParserAgent()
        content = "module test(input clk); endmodule"
        result = agent.parse_netlist(content)
        assert "modules" in result
        assert len(result["modules"]) > 0

    def test_parse_log(self):
        """Test log parsing."""
        agent = ParserAgent()
        content = "INFO: Test message\nERROR: Test error"
        result = agent.parse_log(content)
        assert len(result["errors"]) > 0
        assert len(result["warnings"]) == 0

    def test_detect_format(self):
        """Test format detection."""
        agent = ParserAgent()
        assert agent.detect_format('{"test": "value"}') == "json"
        assert agent.detect_format("col1,col2\nval1,val2") == "csv"
        assert agent.detect_format("module test; endmodule") == "netlist"

    def test_process(self, sample_state):
        """Test parser processing."""
        agent = ParserAgent()
        result = agent.process(sample_state)
        assert "parsed_data" in result
        assert result["parsed_data"]["format"] in ["netlist", "log"]

class TestAnalyzerAgent:
    """Tests for AnalyzerAgent."""

    def test_create_analysis_prompt(self, sample_parsed_data, monkeypatch):
        """Test prompt creation."""
        # Mock environment variables required by AnalyzerAgent
        monkeypatch.setenv("GAISF_ENDPOINT", "mlop-azure-gateway.mediatek.inc")
        monkeypatch.setenv("GAISF_API_KEY", "test_api_key")
        monkeypatch.setenv("GAISF_ACCOUNT_ID", "test_account_id")
        monkeypatch.setattr("examples.agents.analyzer_agent.AnalyzerAgent._get_available_model", lambda self: "llama3.1-70b-instruct")
        
        agent = AnalyzerAgent({"llm": {"model": "llama3.1-70b-instruct", "temperature": 0.0}})
        prompt = agent.create_analysis_prompt(sample_parsed_data)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_process(self, sample_state, mock_llm, monkeypatch):
        """Test analyzer processing."""
        # Mock environment variables required by AnalyzerAgent
        monkeypatch.setenv("GAISF_ENDPOINT", "mlop-azure-gateway.mediatek.inc")
        monkeypatch.setenv("GAISF_API_KEY", "test_api_key")
        monkeypatch.setenv("GAISF_ACCOUNT_ID", "test_account_id")
        monkeypatch.setattr("examples.agents.analyzer_agent.AnalyzerAgent._get_available_model", lambda self: "llama3.1-70b-instruct")
        
        agent = AnalyzerAgent({"llm": {"model": "llama3.1-70b-instruct", "temperature": 0.0}})
        sample_state["parsed_data"] = sample_parsed_data

        monkeypatch.setattr(agent, "llm", mock_llm)
        result = agent.process(sample_state)
        assert "analysis_results" in result

class TestExecutorAgent:
    """Tests for ExecutorAgent."""

    def test_register_tool(self):
        """Test tool registration."""
        agent = ExecutorAgent()
        mock_tool = MagicMock()
        agent.register_tool("test_tool", mock_tool)
        assert "test_tool" in agent.tool_registry

    def test_determine_tool(self, sample_parsed_data):
        """Test tool determination."""
        agent = ExecutorAgent()
        tool = agent.determine_tool(sample_parsed_data)
        assert tool in ["opensta", "openroad", "yosys"]

    def test_process_no_tool(self, sample_state, sample_parsed_data):
        """Test executor when tool not registered."""
        agent = ExecutorAgent()
        sample_state["parsed_data"] = sample_parsed_data
        result = agent.process(sample_state)
        assert "execution_results" in result
        assert result["execution_results"]["status"] == "skipped"

class TestValidatorAgent:
    """Tests for ValidatorAgent."""

    def test_load_schema(self, temp_schema_file):
        """Test schema loading."""
        agent = ValidatorAgent()
        agent.load_schema("test_schema", temp_schema_file)
        assert "test_schema" in agent.schemas

    def test_determine_schema(self, sample_state, sample_parsed_data):
        """Test schema determination."""
        agent = ValidatorAgent()
        sample_state["parsed_data"] = sample_parsed_data
        schema = agent.determine_schema(sample_state)
        assert schema in ["timing_report", "drc_log", "netlist_stat"]

    def test_validate_data(self, temp_schema_file):
        """Test data validation."""
        agent = ValidatorAgent()
        agent.load_schema("test_schema", temp_schema_file)
        valid_data = {"test": "value"}
        is_valid, _ = agent.validate_data(valid_data, "test_schema")
        assert is_valid

class TestReporterAgent:
    """Tests for ReporterAgent."""

    def test_generate_markdown_report(self, sample_state, sample_parsed_data):
        """Test markdown report generation."""
        agent = ReporterAgent()
        sample_state["parsed_data"] = sample_parsed_data
        report = agent.generate_markdown_report(sample_state)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_generate_html_report(self, sample_state, sample_parsed_data):
        """Test HTML report generation."""
        agent = ReporterAgent()
        sample_state["parsed_data"] = sample_parsed_data
        report = agent.generate_html_report(sample_state)
        assert isinstance(report, str)
        assert "<html" in report.lower()

    def test_generate_cli_report(self, sample_state, sample_parsed_data):
        """Test CLI report generation."""
        agent = ReporterAgent()
        sample_state["parsed_data"] = sample_parsed_data
        report = agent.generate_cli_report(sample_state)
        assert isinstance(report, str)
        assert "EDA AGENT REPORT" in report

    def test_process(self, sample_state, sample_parsed_data):
        """Test reporter processing."""
        agent = ReporterAgent()
        sample_state["parsed_data"] = sample_parsed_data
        result = agent.process(sample_state)
        assert "report" in result

