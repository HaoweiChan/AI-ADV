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
    """Agent for matching hierarchical paths between target and golden netlists."""

    def __init__(
        self,
        name: str = "hierarchy_matcher",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, config)
        self.llm_client: Optional[LLMClient] = None
        self.target_parser: Optional[SpiceParser] = None
        self.golden_parsers: Dict[str, SpiceParser] = {}

    def _init_llm_client(self) -> LLMClient:
        """Initialize LLM client with config."""
        model = self.config.get("model", "llama3.3-70b-instruct")
        api_key = self.config.get("api_key")
        api_url = self.config.get("api_url")
        return LLMClient(model=model, api_key=api_key, api_url=api_url)

    def _load_netlists(
        self,
        target_netlist_path: str,
        golden_netlist_dict: Dict[str, str],
    ) -> None:
        """Load and parse netlist files."""
        if not os.path.exists(target_netlist_path):
            raise FileNotFoundError(f"Target netlist not found: {target_netlist_path}")
        self.target_parser = SpiceParser(target_netlist_path)
        logger.info(f"Loaded target netlist: {target_netlist_path}")
        logger.info(f"Found {len(self.target_parser.subckts)} subcircuits in target")

        self.golden_parsers = {}
        for key, path in golden_netlist_dict.items():
            if not os.path.exists(path):
                raise FileNotFoundError(f"Golden netlist not found: {path}")
            self.golden_parsers[key] = SpiceParser(path)
            logger.info(f"Loaded golden netlist [{key}]: {path}")
            logger.info(
                f"Found {len(self.golden_parsers[key].subckts)} subcircuits in [{key}]"
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
        golden_key: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Step 2: Collect matching cell blocks from target and golden netlists.

        Args:
            component_path: Hierarchical path to search
            golden_key: Specific golden netlist key (uses first if None)

        Returns:
            Tuple of (target_blocks, golden_blocks) as concatenated strings
        """
        path_parts = component_path.strip().split("/")
        target_blocks = []
        golden_blocks = []

        if not path_parts or not path_parts[0]:
            return "ERROR: Path empty", "ERROR: Path empty"

        # Get golden parser
        if golden_key and golden_key in self.golden_parsers:
            golden_parser = self.golden_parsers[golden_key]
        elif self.golden_parsers:
            golden_parser = list(self.golden_parsers.values())[0]
        else:
            return "ERROR: No target parser", "ERROR: No golden parser"

        # Match path parts with cell names
        for part in path_parts:
            # Target netlist
            for cell_name in self.target_parser.subckts.keys():
                if part == cell_name:
                    cell_content = self.target_parser.get_subckt_content(cell_name)
                    if cell_content:
                        target_blocks.append(cell_content)

            # Golden netlist
            for cell_name in golden_parser.subckts.keys():
                if part == cell_name:
                    cell_content = golden_parser.get_subckt_content(cell_name)
                    if cell_content:
                        golden_blocks.append(cell_content)

        target_text = "\n\n".join(target_blocks)
        golden_text = "\n\n".join(golden_blocks)
        return target_text, golden_text

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
        golden_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full 3-step pipeline for path resolution.

        Args:
            instance_path: Target netlist instance path to resolve
            golden_key: Specific golden netlist key

        Returns:
            Dict with resolution results
        """
        result = {
            "input_path": instance_path,
            "golden_key": golden_key,
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
        target_blocks, golden_blocks = self.step2_netlist_blocks(
            component_path, golden_key
        )
        result["steps"]["step2"] = {
            "target_blocks": target_blocks,
            "golden_blocks": golden_blocks,
        }
        logger.info(f"[Step2] Target blocks length: {len(target_blocks)}")
        logger.info(f"[Step2] Golden blocks length: {len(golden_blocks)}")

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
        - target_netlist: str (path to target netlist)
        - golden_netlist_dict: Dict[str, str] (key -> path mapping)
        - instance_paths: List[str] (paths to resolve)
        - model: str (optional, LLM model name)
        - api_key: str (optional)
        - api_url: str (optional)
        """
        logger.info("Starting hierarchy matching process")
        input_data = state["input_data"]

        # Validate required fields
        target_netlist = input_data.get("target_netlist")
        golden_netlist_dict = input_data.get("golden_netlist_dict", {})
        instance_paths = input_data.get("instance_paths", [])

        if not target_netlist:
            return self.handle_error(
                ValueError("target_netlist is required"), state
            )
        if not golden_netlist_dict:
            return self.handle_error(
                ValueError("golden_netlist_dict is required"), state
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
            self._load_netlists(target_netlist, golden_netlist_dict)

            # Process each instance path
            results = []
            for path in instance_paths:
                for golden_key in golden_netlist_dict.keys():
                    result = self.resolve_path(path, golden_key)
                    results.append(result)

            state["analysis_results"] = {
                "resolutions": results,
                "target_subcircuits": list(self.target_parser.subckts.keys()),
                "golden_subcircuits": {
                    k: list(v.subckts.keys())
                    for k, v in self.golden_parsers.items()
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
            f"Target Netlist: {input_data.get('target_netlist')}",
            f"Golden Netlists: {list(input_data.get('golden_netlist_dict', {}).keys())}",
            "",
            "Results:",
            "-" * 50,
        ]

        for i, res in enumerate(results, 1):
            lines.append(f"\n[{i}] Input: {res['input_path']}")
            lines.append(f"    Golden: {res.get('golden_key', 'default')}")
            lines.append(f"    Resolved: {res.get('resolved_path', 'N/A')}")

        return "\n".join(lines)

