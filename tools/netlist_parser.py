
import logging
import re
from typing import Dict, List, Set, Tuple, Any, Optional

import networkx as nx

logger = logging.getLogger(__name__)

class NetlistParser:
    """Parser for converting Verilog and SCS/Spice netlists to Graph representations."""

    @staticmethod
    def parse_to_graph(netlist_content: str) -> nx.DiGraph:
        """
        Parses a netlist string into a NetworkX DiGraph.
        Auto-detects format (Verilog vs SCS).
        """
        # Simple heuristic: check for '{' or 'subckt' or specific SCS syntax vs 'module'
        # Or just try one then the other.
        
        if "module " in netlist_content or "endmodule" in netlist_content or ";" in netlist_content:
            logger.info("Detected Verilog format")
            return NetlistParser.parse_verilog(netlist_content)
        else:
            logger.info("Assuming SCS/Spice format")
            return NetlistParser.parse_scs(netlist_content)

    @staticmethod
    def parse_verilog(netlist_content: str) -> nx.DiGraph:
        """
        Parses a Verilog netlist string into a NetworkX DiGraph.
        """
        G = nx.DiGraph()
        
        # Regex for simple instance: Type Name ( ... );
        instance_pattern = re.compile(r'^\s*([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*\((.*)\)\s*;')
        
        lines = netlist_content.split('\n')
        net_connections: Dict[str, List[Tuple[str, str]]] = {}
        output_pins = {'Y', 'Q', 'Z', 'O', 'OUT', 'ZN', 'QN'}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('module') or line.startswith('endmodule'):
                continue
                
            match = instance_pattern.match(line)
            if match:
                cell_type = match.group(1)
                inst_name = match.group(2)
                conn_str = match.group(3)
                
                G.add_node(inst_name, type=cell_type, label=cell_type)
                
                conns = [c.strip() for c in conn_str.split(',') if c.strip()]
                for conn in conns:
                    if '(' in conn and ')' in conn:
                        try:
                            parts = conn.split('(')
                            pin = parts[0].replace('.', '').strip()
                            net = parts[1].replace(')', '').strip()
                            direction = 'source' if pin in output_pins else 'sink'
                            
                            if net not in net_connections:
                                net_connections[net] = []
                            net_connections[net].append((inst_name, direction))
                        except IndexError:
                            pass
        
        NetlistParser._build_edges_from_nets(G, net_connections)
        return G

    @staticmethod
    def parse_scs(netlist_content: str) -> nx.DiGraph:
        """
        Parses SCS/Spice format based on tools/utils/parser.py logic.
        Format: InstanceName ( Net1 Net2 ... ) CellName Param=Val
        """
        G = nx.DiGraph()
        
        # Merge lines ending with \
        lines = netlist_content.split('\n')
        merged_lines = []
        merge_buffer = ""
        
        for line in lines:
            line = line.rstrip('\n')
            if line.endswith('\\'):
                merge_buffer += line[:-1].strip() + " "
            else:
                merge_buffer += line
                merged_lines.append(merge_buffer)
                merge_buffer = ""
                
        # Parse merged lines
        net_connections: Dict[str, List[Tuple[str, str]]] = {}
        
        for line in merged_lines:
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('*'):
                continue
            
            # Ignore cell name definitions or subckt for graph building (simplified)
            if "cell name" in line or "subckt" in line or "ends" in line:
                continue
                
            # Instance line: inst_name (nets) cell_name params
            if '(' in line and ')' in line:
                try:
                    pre_paren = line.split('(')[0].strip()
                    inside_paren = line.split('(')[1].split(')')[0].strip()
                    post_paren = line.split(')')[1].strip()
                    
                    inst_name = pre_paren.replace('\\', '') # Remove escaped chars if any
                    
                    # Nets are space separated inside parens
                    nets = inside_paren.split()
                    
                    # Cell name is first token after parens
                    parts_post = post_paren.split()
                    cell_name = parts_post[0].replace('\\', '') if parts_post else "Unknown"
                    
                    # Add node
                    G.add_node(inst_name, type=cell_name, label=cell_name)
                    
                    # Map nets
                    # In Spice, order determines pin. Without library, we don't know direction.
                    # We will treat ALL as 'undirected' or assume first is output?
                    # SCS/Spice usually: D Q CLK ... depends on cell.
                    # For now, we connect all nets to the instance.
                    # Direction is 'unknown' unless we have a map.
                    # WL Hash works with directed or undirected.
                    # We will treat them as 'sink' for generic connectivity, 
                    # but to form edges we need 'source'.
                    # If we assume undirected graph for SCS? 
                    # Or convert to undirected before hashing if needed.
                    # Let's stick to the previous pattern: create 'net' groups.
                    
                    for net in nets:
                        if net not in net_connections:
                            net_connections[net] = []
                        # For SCS without pin names, direction is hard.
                        # We'll mark as 'connected'.
                        net_connections[net].append((inst_name, 'connected'))
                        
                except Exception as e:
                    logger.warning(f"Failed to parse SCS line: {line} | Error: {e}")
                    
        # Build edges
        # Since direction is unknown, we create a Clique or Star topology?
        # Or create Net nodes?
        # Creating Net nodes makes it a bipartite graph (Instance - Net).
        # WL Hash works on bipartite graphs too.
        # Let's try Bipartite for SCS to be safe.
        
        for net, items in net_connections.items():
            # Add net node
            net_node = f"NET_{net}"
            G.add_node(net_node, type='NET', label='NET')
            
            for inst, _ in items:
                # Add edge Instance <-> Net
                G.add_edge(inst, net_node)
                G.add_edge(net_node, inst) # Undirected-like (bidirectional)
                
        return G

    @staticmethod
    def _build_edges_from_nets(G: nx.DiGraph, net_connections: Dict[str, List[Tuple[str, str]]]):
        """Helper to build directed edges for Verilog where direction is known."""
        for net, items in net_connections.items():
            sources = [inst for inst, dir in items if dir == 'source']
            sinks = [inst for inst, dir in items if dir == 'sink']
            
            if not sources:
                port_name = f"PIN_{net}"
                if not G.has_node(port_name):
                    G.add_node(port_name, type='PIN', label='PIN')
                sources = [port_name]
                
            for src in sources:
                for snk in sinks:
                    if src != snk:
                        G.add_edge(src, snk, net_name=net)

    @staticmethod
    def collapse_dummy_cells(G: nx.Graph, dummy_types: Set[str] = None) -> nx.Graph:
        """
        Removes dummy nodes.
        """
        if dummy_types is None:
            dummy_types = {'BUF', 'INV', 'DUMMY'}
            
        clean_G = G.copy()
        dummies = [n for n, attr in clean_G.nodes(data=True) 
                   if attr.get('type') in dummy_types]
        
        for node in dummies:
            if isinstance(clean_G, nx.DiGraph):
                preds = list(clean_G.predecessors(node))
                succs = list(clean_G.successors(node))
                # For Bipartite (SCS), predecessors/successors might be NET nodes.
                # If Inst1 -> Net1 -> BUF -> Net2 -> Inst2
                # Removing BUF: Net1 and Net2 should merge?
                # This is complex for Bipartite.
                # For now, we skip cleaning for SCS/Bipartite graphs or handle standard DiGraph logic.
                
                if len(preds) == 1 and len(succs) == 1:
                    u = preds[0]
                    v = succs[0]
                    
                    # If u and v are NETs (in bipartite), we merge the nets?
                    # If u is a Net and v is a Net.
                    if clean_G.nodes[u].get('type') == 'NET' and clean_G.nodes[v].get('type') == 'NET':
                        # Merge nets u and v
                        # Move all edges from v to u
                        for nbr in list(clean_G.neighbors(v)): # successors in digraph if bidirectional?
                             # In bidirectional bipartite, neighbors are same.
                             pass
                             
                    # Fallback: standard collapse
                    clean_G.add_edge(u, v, collapsed=True)
                    clean_G.remove_node(node)
            else:
                # Undirected
                nbrs = list(clean_G.neighbors(node))
                if len(nbrs) == 2:
                    u, v = nbrs[0], nbrs[1]
                    clean_G.add_edge(u, v, collapsed=True)
                    clean_G.remove_node(node)
                    
        return clean_G
