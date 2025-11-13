"""OpenROAD adapter for P&R workflows."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from tools.base_adapter import BaseAdapter
from tools.utils.subprocess_runner import SubprocessRunner

logger = logging.getLogger(__name__)


class OpenROADAdapter(BaseAdapter):
    """Adapter for OpenROAD P&R tool."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize OpenROAD adapter.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("openroad", config)
        self.openroad_path = (
            config.get("openroad_path", "openroad") if config else "openroad"
        )
        self.runner = SubprocessRunner(
            timeout=config.get("timeout", 300) if config else 300
        )

    def parse_drc_log(self, log_text: str) -> Dict[str, Any]:
        """Parse OpenROAD DRC log output.

        Args:
            log_text: Raw DRC log text

        Returns:
            Parsed DRC data dictionary
        """
        errors = []
        error_categories = {}
        total_errors = 0
        total_warnings = 0

        lines = log_text.split("\n")
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            if "error" in line_lower or "violation" in line_lower:
                total_errors += 1
                category = "unknown"
                if "spacing" in line_lower:
                    category = "spacing"
                elif "width" in line_lower:
                    category = "width"
                elif "area" in line_lower:
                    category = "area"

                error_categories[category] = error_categories.get(category, 0) + 1

                errors.append(
                    {
                        "id": f"ERR_{i:04d}",
                        "category": category,
                        "severity": "error",
                        "message": line.strip(),
                        "rule": category,
                    }
                )
            elif "warning" in line_lower:
                total_warnings += 1

        return {
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "error_categories": error_categories,
            },
            "errors": errors,
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse OpenROAD output.

        Args:
            output: Raw tool output string

        Returns:
            Parsed output dictionary
        """
        return self.parse_drc_log(output)

    def run(self, content: str, parsed_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run OpenROAD P&R workflow.

        Args:
            content: Input file path or content
            parsed_data: Optional parsed data

        Returns:
            Execution results dictionary
        """
        logger.info("Running OpenROAD P&R workflow")

        if Path(content).exists():
            input_file = Path(content)
        else:
            input_file = Path.cwd() / "input.def"
            input_file.write_text(content)

        openroad_script = f"""
read_lef standard.lef
read_def {input_file}
detailed_placement
detailed_routing
report_drc
exit
"""

        script_file = Path.cwd() / "openroad_script.tcl"
        script_file.write_text(openroad_script)

        command = [self.openroad_path, "-exit", str(script_file)]
        result = self.runner.run(command, capture_output=True)

        if result["success"]:
            parsed = self.parse_output(result["stdout"])
            return {
                "status": "success",
                "raw_output": result["stdout"],
                "parsed": parsed,
            }

        return {
            "status": "failed",
            "error": result["stderr"],
            "raw_output": result["stdout"],
        }

