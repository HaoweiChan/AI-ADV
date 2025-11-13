"""LangGraph workflow assembly connecting all agent nodes."""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from agents.analyzer_agent import AnalyzerAgent
from agents.base_agent import AgentState
from agents.executor_agent import ExecutorAgent
from agents.parser_agent import ParserAgent
from agents.reporter_agent import ReporterAgent
from agents.validator_agent import ValidatorAgent

logger = logging.getLogger(__name__)


class EDAWorkflow:
    """Main LangGraph workflow for EDA agent template."""

    def __init__(self, config: dict = None):
        """Initialize workflow with agents.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.parser = ParserAgent(config)
        self.analyzer = AnalyzerAgent(config)
        self.executor = ExecutorAgent(config)
        self.validator = ValidatorAgent(config)
        self.reporter = ReporterAgent(config)

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow graph.

        Returns:
            Configured StateGraph instance
        """
        workflow = StateGraph(AgentState)

        workflow.add_node("parser", self.parser)
        workflow.add_node("analyzer", self.analyzer)
        workflow.add_node("executor", self.executor)
        workflow.add_node("validator", self.validator)
        workflow.add_node("reporter", self.reporter)

        workflow.add_edge(START, "parser")
        workflow.add_edge("parser", "analyzer")
        workflow.add_edge("analyzer", "executor")
        workflow.add_edge("executor", "validator")

        workflow.add_conditional_edges(
            "validator",
            self._should_continue,
            {
                "continue": "reporter",
                "retry": "analyzer",
                "end": END,
            },
        )

        workflow.add_edge("reporter", END)

        return workflow.compile()

    def _should_continue(self, state: AgentState) -> Literal["continue", "retry", "end"]:
        """Determine next step after validation.

        Args:
            state: Current workflow state

        Returns:
            Next step identifier
        """
        errors = state.get("errors", [])
        if len(errors) > 5:
            logger.error("Too many errors, ending workflow")
            return "end"

        validation_status = state.get("validation_status", {})
        if not validation_status:
            return "continue"

        all_valid = all(
            status == "valid" for status in validation_status.values()
        )

        if not all_valid:
            retry_count = state.get("metadata", {}).get("retry_count", 0)
            max_retries = self.config.get("guardrails", {}).get("max_retries", 3)
            if self.config.get("guardrails", {}).get("auto_repair", True):
                if retry_count < max_retries:
                    if "metadata" not in state:
                        state["metadata"] = {}
                    state["metadata"]["retry_count"] = retry_count + 1
                    logger.info(f"Retrying analysis (attempt {retry_count + 1})")
                    return "retry"

        return "continue"

    def run(self, input_data: dict) -> AgentState:
        """Execute workflow with input data.

        Args:
            input_data: Input data dictionary

        Returns:
            Final workflow state
        """
        initial_state: AgentState = {
            "input_data": input_data,
            "metadata": {},
        }

        logger.info("Starting EDA workflow")
        result = self.graph.invoke(initial_state)
        logger.info("Workflow completed")

        return result

    def register_tool(self, tool_name: str, tool_adapter):
        """Register a tool adapter with executor.

        Args:
            tool_name: Tool name identifier
            tool_adapter: Tool adapter instance
        """
        self.executor.register_tool(tool_name, tool_adapter)

