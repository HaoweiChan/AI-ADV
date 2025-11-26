
import logging
from typing import Any, Dict, List, Optional, Set

import networkx as nx
import numpy as np

from tools.base_adapter import BaseAdapter
from tools.netlist_parser import NetlistParser

logger = logging.getLogger(__name__)

# Optional imports for pygmtools
try:
    import pygmtools
    HAS_PYGMTOOLS = True
    try:
        import torch
        HAS_TORCH = True
    except ImportError:
        HAS_TORCH = False
except ImportError:
    HAS_PYGMTOOLS = False
    HAS_TORCH = False
    logger.warning("pygmtools not installed. Option 2 (Graph Matching) will not be available.")


class GraphMatchingAdapter(BaseAdapter):
    """Adapter for Graph Matching and Equivalence Checking using NetworkX and pygmtools."""

    def __init__(self, name: str = "graph_matcher", config: Dict[str, Any] = None):
        super().__init__(name, config)
        if HAS_PYGMTOOLS:
            if HAS_TORCH:
                pygmtools.BACKEND = 'pytorch'
            else:
                pygmtools.BACKEND = 'numpy'
                logger.info("Using pygmtools with numpy backend (torch not found)")

    def run(self, content: str, parsed_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute graph operation.
        
        Expected parsed_data to contain:
        - 'action': 'hash' | 'match' | 'clean'
        - 'graph_a': (optional) NetworkX graph or netlist content
        - 'graph_b': (optional) NetworkX graph or netlist content for matching
        - 'dummy_types': (optional) list of dummy cell types to collapse
        """
        action = parsed_data.get('action', 'hash') if parsed_data else 'hash'
        
        try:
            if action == 'hash':
                return self._handle_hash(content, parsed_data)
            elif action == 'match':
                return self._handle_match(parsed_data)
            elif action == 'clean':
                return self._handle_clean(content, parsed_data)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Error in GraphMatchingAdapter: {e}", exc_info=True)
            return {"error": str(e)}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse generic output."""
        return {"raw_output": output}

    def _netlist_to_graph(self, netlist_content: str) -> nx.DiGraph:
        """Legacy wrapper using the shared parser."""
        return NetlistParser.parse_to_graph(netlist_content)

    def collapse_dummy_cells(self, G: nx.Graph, dummy_types: Set[str] = None) -> nx.Graph:
        """Legacy wrapper using the shared parser utility."""
        return NetlistParser.collapse_dummy_cells(G, dummy_types)

    def get_wl_hash(self, G: nx.Graph, iterations: int = 3) -> str:
        """
        Compute Weisfeiler-Lehman Graph Hash.
        """
        return nx.weisfeiler_lehman_graph_hash(
            G, 
            edge_attr=None, 
            node_attr='type',
            iterations=iterations
        )

    def _handle_hash(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Load Graph
        G = self._resolve_graph(content, parsed_data)
        
        # 2. Compute Hash
        h = self.get_wl_hash(G)
        
        return {
            "hash": h,
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges()
        }

    def _handle_clean(self, content: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        G = self._resolve_graph(content, parsed_data)
        dummy_types = parsed_data.get('dummy_types')
        if dummy_types:
            dummy_types = set(dummy_types)
            
        clean_G = self.collapse_dummy_cells(G, dummy_types)
        
        return {
            "original_nodes": G.number_of_nodes(),
            "clean_nodes": clean_G.number_of_nodes(),
            "status": "cleaned"
        }

    def _handle_match(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match two graphs using pygmtools.
        parsed_data must contain 'graph_a' and 'graph_b' (NetworkX objects or content).
        """
        if not HAS_PYGMTOOLS:
            return {"error": "pygmtools not installed"}

        G1 = self._resolve_graph(parsed_data.get('netlist_a'), {'graph': parsed_data.get('graph_a')})
        G2 = self._resolve_graph(parsed_data.get('netlist_b'), {'graph': parsed_data.get('graph_b')})

        # Convert to pygmtools format
        # 1. Build Adjacency Matrices
        n1 = G1.number_of_nodes()
        n2 = G2.number_of_nodes()
        
        adj1 = nx.to_numpy_array(G1)
        adj2 = nx.to_numpy_array(G2)
        
        # 2. Build Node Features (e.g. one-hot encoding of types)
        types1 = set(nx.get_node_attributes(G1, 'type').values())
        types2 = set(nx.get_node_attributes(G2, 'type').values())
        all_types = sorted(list(types1.union(types2)))
        type_to_idx = {t: i for i, t in enumerate(all_types)}
        
        feat1 = np.zeros((n1, len(all_types)))
        for i, node in enumerate(G1.nodes()):
            t = G1.nodes[node].get('type', 'unknown')
            if t in type_to_idx:
                feat1[i, type_to_idx[t]] = 1
                
        feat2 = np.zeros((n2, len(all_types)))
        for i, node in enumerate(G2.nodes()):
            t = G2.nodes[node].get('type', 'unknown')
            if t in type_to_idx:
                feat2[i, type_to_idx[t]] = 1
                
        # Convert to Backend Tensors
        if pygmtools.BACKEND == 'pytorch' and HAS_TORCH:
            conn1 = torch.from_numpy(adj1).float()
            conn2 = torch.from_numpy(adj2).float()
            F1 = torch.from_numpy(feat1).float()
            F2 = torch.from_numpy(feat2).float()
        else:
            # Numpy backend
            conn1 = adj1
            conn2 = adj2
            F1 = feat1
            F2 = feat2
        
        # 3. Run Matching using Learning-Free Solver (RRWM/SM)
        try:
            # Ensure pygmtools.utils is available
            from pygmtools import utils as pygm_utils
            
            if hasattr(pygm_utils, 'build_affinity_matrix'):
                K = pygm_utils.build_affinity_matrix(conn1, conn2, F1, F2)
                
                # Use RRWM or SM
                if hasattr(pygmtools, 'rrwm'):
                    X = pygmtools.rrwm(K, n1, n2)
                elif hasattr(pygmtools, 'sm'):
                    X = pygmtools.sm(K, n1, n2)
                else:
                     raise NotImplementedError("No learning-free solver (rrwm/sm) found.")
            elif hasattr(pygmtools, 'sm'):
                 # Fallback if build_affinity_matrix is missing but sm exists
                 raise NotImplementedError("build_affinity_matrix not found in pygmtools.utils")
            else:
                 raise NotImplementedError("Graph Matching tools incomplete in installed pygmtools version.")

            # X is the matching matrix (permutation matrix)
            if pygmtools.BACKEND == 'pytorch' and HAS_TORCH and torch.is_tensor(X):
                X = X.detach().cpu().numpy()
            
            # Calculate similarity / matching score
            score = np.sum(X * (adj1 @ X @ adj2.T)) # Simplified score
            
            return {
                "matching_matrix_shape": X.shape,
                "score": float(score),
                "matched_pairs": self._extract_matches(X, list(G1.nodes()), list(G2.nodes()))
            }
        except Exception as e:
            return {"error": f"Matching failed: {str(e)}"}

    def _extract_matches(self, X: np.ndarray, nodes1: List[str], nodes2: List[str]) -> List[Dict[str, Any]]:
        # Greedy assignment from soft assignment matrix X
        matches = []
        # linear_sum_assignment for optimal hard matching
        from scipy.optimize import linear_sum_assignment
        row_ind, col_ind = linear_sum_assignment(X, maximize=True)
        
        for r, c in zip(row_ind, col_ind):
            matches.append({
                "node_a": nodes1[r],
                "node_b": nodes2[c],
                "confidence": float(X[r, c])
            })
        return matches

    def _resolve_graph(self, content: str, parsed_data: Dict[str, Any] = None) -> nx.Graph:
        """Helper to get graph from content or parsed_data."""
        if parsed_data and 'graph' in parsed_data and isinstance(parsed_data['graph'], (nx.Graph, nx.DiGraph)):
            return parsed_data['graph']
        if content:
            return self._netlist_to_graph(content)
        if parsed_data and 'graph_content' in parsed_data:
            return self._netlist_to_graph(parsed_data['graph_content'])
            
        # Fallback empty
        return nx.DiGraph()
