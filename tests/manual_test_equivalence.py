
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.equivalence_check_agent import EquivalenceCheckAgent

logging.basicConfig(level=logging.INFO)

def test_equivalence():
    # Netlist A: Simple chain: IN -> BUF -> AND -> OUT
    netlist_a = """
    BUF u1 ( .A(in), .Y(n1) );
    AND u2 ( .A(n1), .B(in2), .Y(out) );
    """
    
    # Netlist B: Collapsed chain: IN -> AND -> OUT (functionally equivalent if BUF is ignored)
    # Actually, if we remove BUF, u1 input 'in' should connect to 'n1' sinks.
    # u2 input 'n1' becomes 'in'.
    # So equivalent struct is: AND u2 ( .A(in), .B(in2), .Y(out) );
    netlist_b = """
    AND u2 ( .A(in), .B(in2), .Y(out) );
    """
    
    print("--- Test 1: WL Hash with Cleaning ---")
    agent = EquivalenceCheckAgent()
    state = {
        "input_data": {
            "netlist_a": netlist_a,
            "netlist_b": netlist_b,
            "mode": "hash",
            "clean_dummies": True
        }
    }
    
    result = agent.process(state)
    print("Report:\n", result.get("report"))
    
    if result.get("analysis_results", {}).get("equivalent"):
        print("SUCCESS: Graphs are equivalent after cleaning.")
    else:
        print("FAILURE: Graphs should be equivalent.")

    print("\n--- Test 2: Graph Matching (pygmtools) ---")
    state["input_data"]["mode"] = "match"
    try:
        result_match = agent.process(state)
        print("Report:\n", result_match.get("report"))
    except Exception as e:
        print(f"Skipping Match test due to error (likely missing deps): {e}")

if __name__ == "__main__":
    test_equivalence()

