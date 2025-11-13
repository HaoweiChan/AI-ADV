"""OpenSTA adapter for timing analysis."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from tools.base_adapter import BaseAdapter
from tools.utils.subprocess_runner import SubprocessRunner

logger = logging.getLogger(__name__)


class OpenSTAAdapter(BaseAdapter):
    """Adapter for OpenSTA timing analysis tool."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize OpenSTA adapter.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("opensta", config)
        self.sta_path = config.get("sta_path", "sta") if config else "sta"
        self.runner = SubprocessRunner(
            timeout=config.get("timeout", 300) if config else 300
        )

    def parse_timing_report(self, report_text: str) -> Dict[str, Any]:
        """Parse OpenSTA timing report output.

        Args:
            report_text: Raw timing report text

        Returns:
            Parsed timing data dictionary
        """
        violations = []
        setup_violations = 0
        hold_violations = 0
        max_delay = None
        min_delay = None
        critical_path = None

        lines = report_text.split("\n")
        for line in lines:
            if "setup violation" in line.lower() or "max delay" in line.lower():
                setup_violations += 1
                match = re.search(r"(\d+\.\d+)", line)
                if match:
                    max_delay = float(match.group(1))
            elif "hold violation" in line.lower() or "min delay" in line.lower():
                hold_violations += 1
                match = re.search(r"(\d+\.\d+)", line)
                if match:
                    min_delay = float(match.group(1))
            elif "critical path" in line.lower():
                critical_path = line.strip()

        return {
            "summary": {
                "setup_violations": setup_violations,
                "hold_violations": hold_violations,
                "max_delay": max_delay,
                "min_delay": min_delay,
                "critical_path": critical_path,
            },
            "violations": violations,
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse OpenSTA output.

        Args:
            output: Raw tool output string

        Returns:
            Parsed output dictionary
        """
        return self.parse_timing_report(output)

    def run(self, content: str, parsed_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run OpenSTA timing analysis.

        Args:
            content: Input file path or content
            parsed_data: Optional parsed data

        Returns:
            Execution results dictionary
        """
        logger.info("Running OpenSTA timing analysis")

        if Path(content).exists():
            input_file = Path(content)
        else:
            input_file = Path.cwd() / "input.timing"
            input_file.write_text(content)

        sta_script = f"""
read_liberty standard.lib
read_verilog {input_file}
link_design top
create_clock -period 10 clk
report_timing
exit
"""

        script_file = Path.cwd() / "sta_script.tcl"
        script_file.write_text(sta_script)

        command = [self.sta_path, "-exit", str(script_file)]
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

