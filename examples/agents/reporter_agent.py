"""Reporter agent for generating human-readable reports."""

import logging
from typing import Any, Dict
from agents.base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)


class ReporterAgent(BaseAgent):
    """Reporter node for aggregating results and generating reports."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize reporter agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ReporterNode", config)
        self.output_format = (
            config.get("output", {}).get("format", "markdown")
            if config and config.get("output")
            else "markdown"
        )

    def generate_markdown_report(self, state: AgentState) -> str:
        """Generate Markdown format report.

        Args:
            state: Current workflow state

        Returns:
            Markdown formatted report string
        """
        report_lines = ["# EDA Agent Report\n"]

        input_data = state.get("input_data", {})
        filename = input_data.get("filename", "unknown")
        report_lines.append(f"**Input File:** {filename}\n")

        parsed_data = state.get("parsed_data")
        if parsed_data:
            report_lines.append("## Parsed Data\n")
            report_lines.append(f"- Format: {parsed_data.get('format', 'unknown')}\n")
            report_lines.append("")

        analysis_results = state.get("analysis_results")
        if analysis_results:
            report_lines.append("## Analysis Results\n")
            analysis_text = analysis_results.get("analysis", "")
            report_lines.append(f"{analysis_text}\n")

        execution_results = state.get("execution_results")
        if execution_results:
            report_lines.append("## Execution Results\n")
            tool = execution_results.get("tool", "unknown")
            status = execution_results.get("status", "unknown")
            report_lines.append(f"- Tool: {tool}\n")
            report_lines.append(f"- Status: {status}\n")
            if "results" in execution_results:
                report_lines.append("### Results\n")
                report_lines.append(f"```json\n{execution_results['results']}\n```\n")

        validated_data = state.get("validated_data")
        if validated_data:
            report_lines.append("## Validation Status\n")
            validation_status = state.get("validation_status", {})
            for key, status in validation_status.items():
                report_lines.append(f"- {key}: {status}\n")

        errors = state.get("errors", [])
        if errors:
            report_lines.append("## Errors\n")
            for error in errors:
                report_lines.append(f"- {error}\n")

        return "\n".join(report_lines)

    def generate_html_report(self, state: AgentState) -> str:
        """Generate HTML format report.

        Args:
            state: Current workflow state

        Returns:
            HTML formatted report string
        """
        markdown = self.generate_markdown_report(state)
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>EDA Agent Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
{markdown.replace('##', '<h2>').replace('</h2>', '</h2>').replace('#', '<h1>').replace('</h1>', '</h1>')}
</body>
</html>"""
        return html

    def generate_cli_report(self, state: AgentState) -> str:
        """Generate CLI-friendly format report.

        Args:
            state: Current workflow state

        Returns:
            CLI formatted report string
        """
        report_lines = ["=" * 80]
        report_lines.append("EDA AGENT REPORT")
        report_lines.append("=" * 80)

        input_data = state.get("input_data", {})
        filename = input_data.get("filename", "unknown")
        report_lines.append(f"\nInput File: {filename}")

        analysis_results = state.get("analysis_results")
        if analysis_results:
            report_lines.append("\n" + "-" * 80)
            report_lines.append("ANALYSIS RESULTS")
            report_lines.append("-" * 80)
            report_lines.append(analysis_results.get("analysis", ""))

        execution_results = state.get("execution_results")
        if execution_results:
            report_lines.append("\n" + "-" * 80)
            report_lines.append("EXECUTION RESULTS")
            report_lines.append("-" * 80)
            report_lines.append(f"Tool: {execution_results.get('tool', 'unknown')}")
            report_lines.append(f"Status: {execution_results.get('status', 'unknown')}")

        errors = state.get("errors", [])
        if errors:
            report_lines.append("\n" + "-" * 80)
            report_lines.append("ERRORS")
            report_lines.append("-" * 80)
            for error in errors:
                report_lines.append(f"  - {error}")

        report_lines.append("\n" + "=" * 80)
        return "\n".join(report_lines)

    def process(self, state: AgentState) -> AgentState:
        """Generate report from aggregated state data.

        Args:
            state: Current workflow state

        Returns:
            Updated state with report
        """
        if self.output_format == "html":
            report = self.generate_html_report(state)
        elif self.output_format == "cli":
            report = self.generate_cli_report(state)
        else:
            report = self.generate_markdown_report(state)

        state["report"] = report
        self.logger.info(f"Report generated in {self.output_format} format")
        return state

