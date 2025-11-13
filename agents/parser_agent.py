"""Parser agent for normalizing EDA artifacts."""

import csv
import json
import logging
from typing import Any, Dict

from agents.base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)


class ParserAgent(BaseAgent):
    """Parser node for ingesting and normalizing EDA artifacts."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize parser agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ParserNode", config)

    def parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON content.

        Args:
            content: JSON string content

        Returns:
            Parsed JSON dictionary
        """
        return json.loads(content)

    def parse_csv(self, content: str) -> list[Dict[str, Any]]:
        """Parse CSV content.

        Args:
            content: CSV string content

        Returns:
            List of dictionaries representing rows
        """
        reader = csv.DictReader(content.splitlines())
        return list(reader)

    def parse_netlist(self, content: str) -> Dict[str, Any]:
        """Parse netlist file (simplified parser).

        Args:
            content: Netlist file content

        Returns:
            Parsed netlist structure
        """
        lines = content.split("\n")
        modules = []
        current_module = None

        for line in lines:
            line = line.strip()
            if line.startswith("module "):
                if current_module:
                    modules.append(current_module)
                module_name = line.split()[1].split("(")[0]
                current_module = {"name": module_name, "ports": [], "instances": []}
            elif line.startswith("endmodule"):
                if current_module:
                    modules.append(current_module)
                    current_module = None

        return {"modules": modules, "line_count": len(lines)}

    def parse_log(self, content: str) -> Dict[str, Any]:
        """Parse log file content.

        Args:
            content: Log file content

        Returns:
            Parsed log structure with errors, warnings, info
        """
        lines = content.split("\n")
        errors = []
        warnings = []
        info = []

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if "error" in line_lower or "err" in line_lower:
                errors.append({"line": i, "message": line.strip()})
            elif "warning" in line_lower or "warn" in line_lower:
                warnings.append({"line": i, "message": line.strip()})
            elif line.strip():
                info.append({"line": i, "message": line.strip()})

        return {
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "total_lines": len(lines),
        }

    def detect_format(self, content: str, filename: str = "") -> str:
        """Detect file format from content or filename.

        Args:
            content: File content
            filename: Optional filename

        Returns:
            Detected format string
        """
        if filename:
            ext = filename.lower().split(".")[-1]
            if ext in ["json"]:
                return "json"
            if ext in ["csv"]:
                return "csv"
            if ext in ["v", "vh", "sv"]:
                return "netlist"
            if ext in ["log", "rpt"]:
                return "log"

        content_lower = content[:100].lower()
        if content.strip().startswith("{") or content.strip().startswith("["):
            return "json"
        if "," in content_lower and "\n" in content_lower:
            return "csv"
        if "module" in content_lower or "endmodule" in content_lower:
            return "netlist"

        return "log"

    def process(self, state: AgentState) -> AgentState:
        """Process input data and parse into structured format.

        Args:
            state: Current workflow state

        Returns:
            Updated state with parsed_data
        """
        input_data = state.get("input_data", {})

        if "content" not in input_data:
            raise ValueError("No content found in input_data")

        content = input_data["content"]
        filename = input_data.get("filename", "")

        file_format = self.detect_format(content, filename)
        self.logger.info(f"Detected format: {file_format}")

        parsed_data = {"format": file_format, "filename": filename}

        if file_format == "json":
            parsed_data["data"] = self.parse_json(content)
        elif file_format == "csv":
            parsed_data["data"] = self.parse_csv(content)
        elif file_format == "netlist":
            parsed_data["data"] = self.parse_netlist(content)
        else:
            parsed_data["data"] = self.parse_log(content)

        state["parsed_data"] = parsed_data
        self.logger.info("Parsing completed successfully")
        return state

