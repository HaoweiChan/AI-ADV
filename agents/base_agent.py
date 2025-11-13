"""Base agent framework for LangGraph nodes."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypedDict

from typing_extensions import NotRequired

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Shared state structure for LangGraph workflow."""

    input_data: Dict[str, Any]
    parsed_data: NotRequired[Dict[str, Any]]
    analysis_results: NotRequired[Dict[str, Any]]
    execution_results: NotRequired[Dict[str, Any]]
    validated_data: NotRequired[Dict[str, Any]]
    report: NotRequired[str]
    errors: NotRequired[list[str]]
    metadata: NotRequired[Dict[str, Any]]


class BaseAgent(ABC):
    """Abstract base class for all agent nodes in the LangGraph workflow."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize base agent.

        Args:
            name: Agent name identifier
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def process(self, state: AgentState) -> AgentState:
        """Process state and return updated state.

        Args:
            state: Current workflow state

        Returns:
            Updated state with agent's output
        """
        pass

    def validate_input(self, state: AgentState) -> bool:
        """Validate input state before processing.

        Args:
            state: Current workflow state

        Returns:
            True if input is valid, False otherwise
        """
        return True

    def handle_error(self, error: Exception, state: AgentState) -> AgentState:
        """Handle errors during processing.

        Args:
            error: Exception that occurred
            state: Current workflow state

        Returns:
            Updated state with error information
        """
        error_msg = f"{self.name} error: {str(error)}"
        self.logger.error(error_msg, exc_info=True)

        if "errors" not in state:
            state["errors"] = []

        state["errors"].append(error_msg)
        return state

    def execute_with_retry(
        self, func: callable, state: AgentState, max_retries: int = 3
    ) -> AgentState:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            state: Current workflow state
            max_retries: Maximum number of retry attempts

        Returns:
            Updated state
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return func(state)
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                )
                if attempt == max_retries - 1:
                    return self.handle_error(last_error, state)

        return self.handle_error(last_error, state)

    def __call__(self, state: AgentState) -> AgentState:
        """Make agent callable for LangGraph.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        self.logger.info(f"Executing {self.name}")

        if not self.validate_input(state):
            error_msg = f"Input validation failed for {self.name}"
            self.logger.error(error_msg)
            return self.handle_error(ValueError(error_msg), state)

        try:
            return self.process(state)
        except Exception as e:
            return self.handle_error(e, state)

