"""Subprocess runner utilities for safe tool execution."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SubprocessRunner:
    """Utility for safely executing subprocess commands."""

    def __init__(self, timeout: int = 300, max_memory_mb: int = 4096):
        """Initialize subprocess runner.

        Args:
            timeout: Execution timeout in seconds.
            max_memory_mb: Maximum memory limit in MB.
        """
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

    def run(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        input_data: Optional[str] = None,
        capture_output: bool = True,
    ) -> Dict[str, Any]:
        """Run subprocess command safely.

        Args:
            command: Command to execute as list of strings.
            cwd: Working directory for command.
            input_data: Optional input data to pipe to command.
            capture_output: Whether to capture stdout/stderr.

        Returns:
            Dictionary with stdout, stderr, returncode, and success status.
        """
        try:
            logger.info(f"Running command: {' '.join(command)}")

            kwargs = {
                "args": command,
                "timeout": self.timeout,
                "text": True,
                "capture_output": capture_output,
            }

            if cwd:
                kwargs["cwd"] = cwd

            if input_data:
                kwargs["input"] = input_data

            result = subprocess.run(**kwargs)

            output = {
                "stdout": result.stdout if capture_output else "",
                "stderr": result.stderr if capture_output else "",
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }

            if not output["success"]:
                logger.warning(
                    f"Command failed with return code {result.returncode}: {result.stderr}"
                )

            return output

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {self.timeout} seconds")
            return {
                "stdout": "",
                "stderr": f"Command timed out after {self.timeout} seconds",
                "returncode": -1,
                "success": False,
            }
        except Exception as e:
            logger.error(f"Subprocess execution error: {str(e)}")
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False,
            }

    def run_with_tempfile(
        self,
        command: list[str],
        input_content: str,
        suffix: str = ".tmp",
    ) -> Dict[str, Any]:
        """Run command with temporary input file.

        Args:
            command: Command to execute (may include `{input_file}` placeholder).
            input_content: Content to write to temporary file.
            suffix: File suffix for temporary file.

        Returns:
            Dictionary with execution results.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            temp_path = Path(f.name)
            f.write(input_content)

        try:
            command_str = " ".join(command)
            command_str = command_str.replace("{input_file}", str(temp_path))
            command_list = command_str.split()

            result = self.run(command_list, capture_output=True)
            return result
        finally:
            temp_path.unlink(missing_ok=True)