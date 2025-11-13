"""Base adapter interface for EDA tool integrations."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """Abstract base class for EDA tool adapters."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        """Initialize adapter.

        Args:
            name: Adapter name identifier
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def run(self, content: str, parsed_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute tool and return results.

        Args:
            content: Input content or file path
            parsed_data: Optional parsed data from parser node

        Returns:
            Dictionary containing tool execution results
        """
        pass

    @abstractmethod
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse tool output into structured format.

        Args:
            output: Raw tool output string

        Returns:
            Parsed output dictionary
        """
        pass

    def validate_config(self) -> bool:
        """Validate adapter configuration.

        Returns:
            True if configuration is valid
        """
        return True

