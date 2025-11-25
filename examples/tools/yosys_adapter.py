"""Yosys adapter for synthesis and netlist analysis."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from tools.base_adapter import BaseAdapter
from .utils.subprocess_runner import SubprocessRunner

logger = logging.getLogger(__name__)


class YosysAdapter(BaseAdapter):
    """Adapter for Yosys synthesis tool."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Yosys adapter.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("yosys", config)
        self.yosys_path = (
            config.get("yosys_path", "yosys") if config else "yosys"
        )
        self.runner = SubprocessRunner(
            timeout=config.get("timeout", 300) if config else 300
        )

    def parse_statistics(self, stat_text: str) -> Dict[str, Any]:
        """Parse Yosys statistics output.

        Args:
            stat_text: Raw statistics text

        Returns:
            Parsed statistics dictionary
        """
        design_name = "unknown"
        module_count = 0
        instance_count = 0
        net_count = 0
        total_gates = 0
        gates_by_type = {}

        lines = stat_text.split("\n")
        for line in lines:
            if "Number of modules:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    module_count = int(match.group(1))
            elif "Number of cells:" in line or "Number of instances:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    instance_count = int(match.group(1))
            elif "Number of wires:" in line or "Number of nets:" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    net_count = int(match.group(1))
            elif "Chip area:" in line or "Total area:" in line:
                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    area = float(match.group(1))
            elif any(gate in line.lower() for gate in ["and", "or", "not", "xor", "nand", "nor"]):
                parts = line.split()
                if len(parts) >= 2:
                    gate_type = parts[0].lower()
                    count = int(parts[1]) if parts[1].isdigit() else 0
                    gates_by_type[gate_type] = count
                    total_gates += count

        return {
            "design": {
                "name": design_name,
                "module_count": module_count,
                "instance_count": instance_count,
                "net_count": net_count,
            },
            "gates": {
                "total_count": total_gates,
                "by_type": gates_by_type,
            },
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Yosys output.

        Args:
            output: Raw tool output string

        Returns:
            Parsed output dictionary
        """
        return self.parse_statistics(output)

    def run(self, content: str, parsed_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run Yosys synthesis and analysis.

        Args:
            content: Input file path or netlist content
            parsed_data: Optional parsed data

        Returns:
            Execution results dictionary
        """
        logger.info("Running Yosys synthesis")

        if Path(content).exists():
            input_file = Path(content)
        else:
            input_file = Path.cwd() / "input.v"
            input_file.write_text(content)

        yosys_script = f"""
read_verilog {input_file}
hierarchy -check
proc
stat
show
exit
"""

        script_file = Path.cwd() / "yosys_script.ys"
        script_file.write_text(yosys_script)

        command = [self.yosys_path, str(script_file)]
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

