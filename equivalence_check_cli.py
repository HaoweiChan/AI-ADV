
import argparse
import logging
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.equivalence_check_agent import EquivalenceCheckAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run Equivalence Check between two netlists.")
    parser.add_argument("netlist_a", help="Path to the first netlist file")
    parser.add_argument("netlist_b", help="Path to the second netlist file")
    parser.add_argument("--mode", choices=["hash", "match"], default="hash", help="Equivalence check mode (hash or match)")
    parser.add_argument("--no-clean", action="store_true", help="Disable dummy cell cleaning")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.netlist_a):
        logger.error(f"Netlist A not found: {args.netlist_a}")
        sys.exit(1)
        
    if not os.path.exists(args.netlist_b):
        logger.error(f"Netlist B not found: {args.netlist_b}")
        sys.exit(1)
        
    # Read files
    try:
        with open(args.netlist_a, 'r') as f:
            content_a = f.read()
        with open(args.netlist_b, 'r') as f:
            content_b = f.read()
    except Exception as e:
        logger.error(f"Error reading files: {e}")
        sys.exit(1)
        
    agent = EquivalenceCheckAgent()
    state = {
        "input_data": {
            "netlist_a": content_a,
            "netlist_b": content_b,
            "mode": args.mode,
            "clean_dummies": not args.no_clean
        }
    }
    
    logger.info(f"Running equivalence check ({args.mode})...")
    try:
        result = agent.process(state)
        
        print("\n" + "="*40)
        print("RESULTS")
        print("="*40)
        print(result.get("report", "No report generated"))
        
        if args.mode == "hash":
            is_equiv = result.get("analysis_results", {}).get("equivalent", False)
            sys.exit(0 if is_equiv else 1)
            
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

