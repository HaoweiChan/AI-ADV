"""Executor agent for orchestrating external EDA tool execution."""

import logging
from typing import Any, Dict
from agents.base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """Executor node for running external EDA tools."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize executor agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ExecutorNode", config)
        self.tool_registry = {}

    def register_tool(self, tool_name: str, tool_adapter: Any):
        """Register a tool adapter for execution.

        Args:
            tool_name: Name identifier for the tool
            tool_adapter: Tool adapter instance with run() method
        """
        self.tool_registry[tool_name] = tool_adapter
        self.logger.info(f"Registered tool: {tool_name}")

    def determine_tool(self, parsed_data: Dict[str, Any]) -> str:
        """Determine which tool to use based on parsed data.

        Args:
            parsed_data: Parsed data from parser node

        Returns:
            Tool name identifier
        """
        file_format = parsed_data.get("format", "")

        if "timing" in file_format.lower() or "sta" in file_format.lower():
            return "opensta"
        if "drc" in file_format.lower() or "layout" in file_format.lower():
            return "openroad"
        if "netlist" in file_format.lower() or "synthesis" in file_format.lower():
            return "yosys"

        return "yosys"

    def process(self, state: AgentState) -> AgentState:
        """Execute external EDA tool based on parsed data.

        Args:
            state: Current workflow state

        Returns:
            Updated state with execution_results
        """
        parsed_data = state.get("parsed_data")
        if not parsed_data:
            raise ValueError("No parsed_data found in state")

        tool_name = self.determine_tool(parsed_data)
        self.logger.info(f"Selected tool: {tool_name}")

        if tool_name not in self.tool_registry:
            self.logger.warning(f"Tool {tool_name} not registered, skipping execution")
            state["execution_results"] = {
                "tool": tool_name,
                "status": "skipped",
                "reason": "Tool not registered",
            }
            return state

        tool_adapter = self.tool_registry[tool_name]
        input_data = state.get("input_data", {})

        try:
            execution_results = tool_adapter.run(
                input_data.get("content", ""), parsed_data
            )

            state["execution_results"] = {
                "tool": tool_name,
                "status": "success",
                "results": execution_results,
            }
            self.logger.info(f"Tool {tool_name} executed successfully")
        except Exception as e:
            self.logger.error(f"Tool execution failed: {str(e)}")
            state["execution_results"] = {
                "tool": tool_name,
                "status": "failed",
                "error": str(e),
            }

        return state

