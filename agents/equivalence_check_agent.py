
import logging
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentState, BaseAgent
from tools.graph_matching_adapter import GraphMatchingAdapter

logger = logging.getLogger(__name__)


class EquivalenceCheckAgent(BaseAgent):
    """Agent for checking equivalence between two netlists using Graph Matching."""

    def __init__(self, name: str = "equivalence_checker", config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.graph_tool = GraphMatchingAdapter(name="graph_matcher", config=config)

    def process(self, state: AgentState) -> AgentState:
        """
        Process the equivalence check.
        
        Expected input_data:
        - netlist_a: str (content or path)
        - netlist_b: str (content or path)
        - mode: 'hash' | 'match' (default 'hash')
        - clean_dummies: bool (default True)
        """
        logger.info(f"Starting equivalence check with mode: {state['input_data'].get('mode', 'hash')}")
        
        input_data = state["input_data"]
        netlist_a = input_data.get("netlist_a")
        netlist_b = input_data.get("netlist_b")
        
        if not netlist_a or not netlist_b:
            return self.handle_error(ValueError("Both netlist_a and netlist_b are required"), state)

        # Load and (optionally) clean graphs
        # We can do this by calling the tool with 'clean' action if we want to inspect the cleaned graph stats
        # OR we can just let the matching step handle it if we build that logic.
        # But the tool is granular.
        
        # Strategy: Load -> Clean -> (Hash/Match)
        # Since the tool methods take 'content', we might need to keep the graphs in memory 
        # if we want to pass objects.
        # The Tool runs in the same process, so we can pass objects in parsed_data.
        
        try:
            # 1. Load and Clean Graph A
            graph_a = self._load_and_clean(netlist_a, input_data)
            
            # 2. Load and Clean Graph B
            graph_b = self._load_and_clean(netlist_b, input_data)
            
            mode = input_data.get("mode", "hash")
            
            results = {}
            
            if mode == "hash":
                # Compute Hashes
                res_a = self.graph_tool.run("", {"action": "hash", "graph": graph_a})
                res_b = self.graph_tool.run("", {"action": "hash", "graph": graph_b})
                
                is_match = (res_a["hash"] == res_b["hash"])
                
                results = {
                    "equivalent": is_match,
                    "graph_a_stats": res_a,
                    "graph_b_stats": res_b,
                    "method": "WL_Hash"
                }
                
            elif mode == "match":
                # Run Graph Matching
                match_res = self.graph_tool.run("", {
                    "action": "match",
                    "graph_a": graph_a,
                    "graph_b": graph_b
                })
                
                if "error" in match_res:
                    raise RuntimeError(match_res["error"])
                    
                # Interpret score or matching
                # If score is close to number of nodes (and nodes are equal), it's a match
                # Normalized score?
                n_a = graph_a.number_of_nodes()
                n_b = graph_b.number_of_nodes()
                score = match_res.get("score", 0)
                
                # Heuristic: perfect match usually sums to N (if isomorphic)
                # But depends on edge weights. For unweighted, it's roughly edge overlaps?
                # Actually, typical GM score is X^T K X.
                
                results = {
                    "matching_details": match_res,
                    "method": "pygmtools_matching",
                    "equivalent": "See score" # Hard to say binary yes/no without threshold
                }
                if n_a == n_b:
                     results["node_count_match"] = True
            
            state["analysis_results"] = results
            
            # Generate Report
            report = f"Equivalence Check Report ({mode})\n"
            report += "=" * 30 + "\n"
            if mode == "hash":
                report += f"Equivalent: {results['equivalent']}\n"
                report += f"Graph A Hash: {results['graph_a_stats']['hash']}\n"
                report += f"Graph B Hash: {results['graph_b_stats']['hash']}\n"
            else:
                report += f"Matching Score: {results['matching_details'].get('score')}\n"
                report += f"Pairs found: {len(results['matching_details'].get('matched_pairs', []))}\n"
            
            state["report"] = report
            
            return state

        except Exception as e:
            return self.handle_error(e, state)

    def _load_and_clean(self, content: str, config: Dict[str, Any]):
        """Helper to load and optionally clean a graph."""
        # Parse (implicitly handled by tool if we pass content, but we need object)
        # We expose a private method or use the tool to parse?
        # The tool's run method returns dict.
        # We need the actual graph object for stateful processing between steps.
        # Accessing tool internals (tool._netlist_to_graph) is acceptable if they are in same package,
        # but cleaner to have a public method.
        
        # Let's allow accessing the helper method on the tool directly since we instantiated it.
        G = self.graph_tool._netlist_to_graph(content)
        
        if config.get("clean_dummies", True):
            G = self.graph_tool.collapse_dummy_cells(G)
            
        return G


