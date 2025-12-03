"""Hierarchy matching agent for netlist path resolution."""

import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import AgentState, BaseAgent
from agents.prompts.hierarchy_prompts import (
    STEP1_PATH_EXTRACT_SYSTEM_PROMPT,
    STEP1_PATH_EXTRACT_USER_PROMPT,
    STEP3_FINAL_SYSTEM_PROMPT,
    STEP3_FINAL_USER_PROMPT,
)

# Add adv_agent to path to import its modules without modifying them
ADV_AGENT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "adv_agent")
if ADV_AGENT_PATH not in sys.path:
    sys.path.insert(0, ADV_AGENT_PATH)

from src.llm_client import LLMClient
from src.netlist_parser import SpiceParser

logger = logging.getLogger(__name__)


class HierarchyMatchingAgent(BaseAgent):
    """Agent for matching hierarchical paths between golden and target netlists."""

    def __init__(
        self,
        name: str = "hierarchy_matcher",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, config)
        self.llm_client: Optional[LLMClient] = None
        self.golden_parser: Optional[SpiceParser] = None
        self.target_parsers: Dict[str, SpiceParser] = {}

    def _init_llm_client(self) -> LLMClient:
        """Initialize LLM client with config."""
        model = self.config.get("model", "llama3.3-70b-instruct")
        api_key = self.config.get("api_key")
        api_url = self.config.get("api_url")
        return LLMClient(model=model, api_key=api_key, api_url=api_url)

    def _load_netlists(
        self,
        golden_netlist_path: str,
        target_netlist_dict: Dict[str, str],
    ) -> None:
        """Load and parse netlist files."""
        if not os.path.exists(golden_netlist_path):
            raise FileNotFoundError(f"Golden netlist not found: {golden_netlist_path}")
        self.golden_parser = SpiceParser(golden_netlist_path)
        logger.info(f"Loaded golden netlist: {golden_netlist_path}")
        logger.info(f"Found {len(self.golden_parser.subckts)} subcircuits in golden")

        self.target_parsers = {}
        for key, path in target_netlist_dict.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Target netlist not found: {path}")
            self.target_parsers[key] = SpiceParser(path)
            logger.info(f"Loaded target netlist [{key}]: {path}")
            logger.info(
                f"Found {len(self.target_parsers[key].subckts)} subcircuits in [{key}]"
            )

    def step1_llm_filter_path(self, instance_path: str) -> Tuple[str, str]:
        """
        Step 1: Send instance_path to LLM and filter meaningful slash path.

        Returns:
            Tuple of (component_path, step1_conversation)
        """
        prompt = STEP1_PATH_EXTRACT_USER_PROMPT.format(instance_path=instance_path)
        response = self.llm_client.complete(STEP1_PATH_EXTRACT_SYSTEM_PROMPT, prompt)
        match = re.search(r"([A-Za-z0-9_\/\-]+)", response)
        component_path = match.group(1) if match else instance_path.strip()
        step1_conversation = f"Prompt: {prompt}\nResponse: {response}"
        return component_path, step1_conversation

    def step2_netlist_blocks(
        self,
        component_path: str,
        target_key: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Step 2: Collect matching cell blocks from golden and target netlists.

        Args:
            component_path: Hierarchical path to search
            target_key: Specific target netlist key (uses first if None)

        Returns:
            Tuple of (golden_blocks, target_blocks) as concatenated strings
        """
        path_parts = component_path.strip().split("/")
        golden_blocks = []
        target_blocks = []

        if not path_parts or not path_parts[0]:
            return "ERROR: Path empty", "ERROR: Path empty"

        # Get target parser
        if target_key and target_key in self.target_parsers:
            target_parser = self.target_parsers[target_key]
        elif self.target_parsers:
            target_parser = list(self.target_parsers.values())[0]
        else:
            return "ERROR: No golden parser", "ERROR: No target parser"

        # Match path parts with cell names
        for part in path_parts:
            # Golden netlist
            for cell_name in self.golden_parser.subckts.keys():
                if part == cell_name:
                    cell_content = self.golden_parser.get_subckt_content(cell_name)
                    if cell_content:
                        golden_blocks.append(cell_content)

            # Target netlist
            for cell_name in target_parser.subckts.keys():
                if part == cell_name:
                    cell_content = target_parser.get_subckt_content(cell_name)
                    if cell_content:
                        target_blocks.append(cell_content)

        golden_text = "\n\n".join(golden_blocks)
        target_text = "\n\n".join(target_blocks)
        return golden_text, target_text

    def step3_llm_final(
        self,
        instance_path: str,
        component_path: str,
        golden_blocks: str,
        target_blocks: str,
        step1_conversation: str,
    ) -> str:
        """
        Step 3: Send paths and blocks to LLM for final matching result.
        """
        prompt = STEP3_FINAL_USER_PROMPT.format(
            instance_path=instance_path,
            component_path=component_path,
            golden_blocks=golden_blocks,
            target_blocks=target_blocks,
            step1_conversation=step1_conversation,
        )
        response = self.llm_client.complete(STEP3_FINAL_SYSTEM_PROMPT, prompt)
        return response.strip()

    def resolve_path(
        self,
        instance_path: str,
        target_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full 3-step pipeline for path resolution.

        Args:
            instance_path: Golden netlist instance path to resolve
            target_key: Specific target netlist key

        Returns:
            Dict with resolution results
        """
        result = {
            "input_path": instance_path,
            "target_key": target_key,
            "steps": {},
        }

        # Step 1: Filter path using LLM
        component_path, step1_conversation = self.step1_llm_filter_path(instance_path)
        result["steps"]["step1"] = {
            "component_path": component_path,
            "conversation": step1_conversation,
        }
        logger.info(f"[Step1] Component Path: {component_path}")

        # Step 2: Extract netlist cell blocks
        golden_blocks, target_blocks = self.step2_netlist_blocks(
            component_path, target_key
        )
        result["steps"]["step2"] = {
            "golden_blocks": golden_blocks,
            "target_blocks": target_blocks,
        }
        logger.info(f"[Step2] Golden blocks length: {len(golden_blocks)}")
        logger.info(f"[Step2] Target blocks length: {len(target_blocks)}")

        # Step 3: LLM final matching
        final_result = self.step3_llm_final(
            instance_path,
            component_path,
            golden_blocks,
            target_blocks,
            step1_conversation,
        )
        result["steps"]["step3"] = {"llm_response": final_result}
        result["resolved_path"] = final_result
        logger.info(f"[Step3] Final result: {final_result}")

        return result

    def process(self, state: AgentState) -> AgentState:
        """
        Process hierarchy matching request.

        Expected input_data:
        - golden_netlist: str (path to golden netlist)
        - target_netlist_dict: Dict[str, str] (key -> path mapping)
        - instance_paths: List[str] (paths to resolve)
        - model: str (optional, LLM model name)
        - api_key: str (optional)
        - api_url: str (optional)
        """
        logger.info("Starting hierarchy matching process")
        input_data = state["input_data"]

        # Validate required fields
        golden_netlist = input_data.get("golden_netlist")
        target_netlist_dict = input_data.get("target_netlist_dict", {})
        instance_paths = input_data.get("instance_paths", [])

        if not golden_netlist:
            return self.handle_error(
                ValueError("golden_netlist is required"), state
            )
        if not target_netlist_dict:
            return self.handle_error(
                ValueError("target_netlist_dict is required"), state
            )

        try:
            # Update config with input params
            if "model" in input_data:
                self.config["model"] = input_data["model"]
            if "api_key" in input_data:
                self.config["api_key"] = input_data["api_key"]
            if "api_url" in input_data:
                self.config["api_url"] = input_data["api_url"]

            # Initialize components
            self.llm_client = self._init_llm_client()
            self._load_netlists(golden_netlist, target_netlist_dict)

            # Process each instance path
            results = []
            for path in instance_paths:
                for target_key in target_netlist_dict.keys():
                    result = self.resolve_path(path, target_key)
                    results.append(result)

            state["analysis_results"] = {
                "resolutions": results,
                "golden_subcircuits": list(self.golden_parser.subckts.keys()),
                "target_subcircuits": {
                    k: list(v.subckts.keys())
                    for k, v in self.target_parsers.items()
                },
            }

            # Generate report
            report = self._generate_report(results, input_data)
            state["report"] = report

            return state

        except Exception as e:
            return self.handle_error(e, state)

    def _generate_report(
        self,
        results: List[Dict[str, Any]],
        input_data: Dict[str, Any],
    ) -> str:
        """Generate human-readable report."""
        lines = [
            "Hierarchy Matching Report",
            "=" * 50,
            f"Golden Netlist: {input_data.get('golden_netlist')}",
            f"Target Netlists: {list(input_data.get('target_netlist_dict', {}).keys())}",
            "",
            "Results:",
            "-" * 50,
        ]

        for i, res in enumerate(results, 1):
            lines.append(f"\n[{i}] Input: {res['input_path']}")
            lines.append(f"    Target: {res.get('target_key', 'default')}")
            lines.append(f"    Resolved: {res.get('resolved_path', 'N/A')}")

        return "\n".join(lines)

