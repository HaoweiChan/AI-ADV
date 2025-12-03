#!/usr/bin/env python3
"""CLI for hierarchy matching between netlists."""

import argparse
import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.hierarchy_matching_agent import HierarchyMatchingAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Match hierarchical paths between golden and target netlists.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command line arguments
  python hierarchy_matching_cli.py \\
    --golden /path/to/golden.scs \\
    --target key1:/path/to/target1.scs \\
    --path "X_ADC/X_AMP/vin"

  # Using JSON config file
  python hierarchy_matching_cli.py --config request.json

  # Interactive mode
  python hierarchy_matching_cli.py \\
    --golden /path/to/golden.scs \\
    --target key1:/path/to/target1.scs \\
    --interactive
        """,
    )

    # Input options
    input_group = parser.add_argument_group("Input Options")
    input_group.add_argument(
        "--config",
        type=str,
        help="Path to JSON config file (overrides other options)",
    )
    input_group.add_argument(
        "--golden",
        type=str,
        help="Path to golden netlist file",
    )
    input_group.add_argument(
        "--target",
        type=str,
        action="append",
        help="Target netlist in format 'key:path' (can be repeated)",
    )
    input_group.add_argument(
        "--path",
        type=str,
        action="append",
        help="Instance path to resolve (can be repeated)",
    )

    # Mode options
    mode_group = parser.add_argument_group("Mode Options")
    mode_group.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )

    # LLM options
    llm_group = parser.add_argument_group("LLM Options")
    llm_group.add_argument(
        "--model",
        type=str,
        default="llama3.3-70b-instruct",
        help="LLM model name (default: llama3.3-70b-instruct)",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output",
        type=str,
        help="Output file path for results (JSON format)",
    )
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse configuration
    config = {}
    if args.config:
        if not os.path.exists(args.config):
            logger.error(f"Config file not found: {args.config}")
            sys.exit(1)
        with open(args.config, "r") as f:
            config = json.load(f)
    else:
        if not args.golden:
            logger.error("Either --config or --golden is required")
            parser.print_help()
            sys.exit(1)
        if not args.target:
            logger.error("Either --config or --target is required")
            parser.print_help()
            sys.exit(1)

        # Build config from arguments
        target_dict = {}
        for t in args.target:
            if ":" not in t:
                logger.error(f"Invalid target format: {t}. Expected 'key:path'")
                sys.exit(1)
            key, path = t.split(":", 1)
            target_dict[key] = path

        config = {
            "version": 1,
            "golden_netlist": args.golden,
            "target_netlist_dict": target_dict,
            "instance_paths": args.path or [],
            "options": {"model": args.model},
        }

    # Validate paths
    golden_path = config.get("golden_netlist")
    if not os.path.exists(golden_path):
        logger.error(f"Golden netlist not found: {golden_path}")
        sys.exit(1)

    for key, path in config.get("target_netlist_dict", {}).items():
        if not os.path.exists(path):
            logger.error(f"Target netlist [{key}] not found: {path}")
            sys.exit(1)

    # Initialize agent
    agent_config = config.get("options", {})
    agent = HierarchyMatchingAgent(config=agent_config)

    if args.interactive:
        run_interactive(agent, config)
    else:
        run_batch(agent, config, args.output)


def run_batch(agent: HierarchyMatchingAgent, config: dict, output_path: str = None):
    """Run batch processing mode."""
    instance_paths = config.get("instance_paths", [])
    if not instance_paths:
        logger.warning("No instance paths provided. Use --path or add to config.")
        return

    state = {
        "input_data": {
            "golden_netlist": config["golden_netlist"],
            "target_netlist_dict": config["target_netlist_dict"],
            "instance_paths": instance_paths,
            "model": config.get("options", {}).get("model", "llama3.3-70b-instruct"),
        }
    }

    logger.info("Running hierarchy matching...")
    try:
        result = agent.process(state)

        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(result.get("report", "No report generated"))

        if result.get("errors"):
            print("\nErrors:")
            for err in result["errors"]:
                print(f"  - {err}")

        if output_path:
            output_data = {
                "config": config,
                "results": result.get("analysis_results"),
                "report": result.get("report"),
                "errors": result.get("errors"),
            }
            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Results saved to: {output_path}")

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        sys.exit(1)


def run_interactive(agent: HierarchyMatchingAgent, config: dict):
    """Run interactive mode."""
    print("\n=== Hierarchy Matching Interactive Mode ===")
    print(f"Golden Netlist: {config['golden_netlist']}")
    print(f"Target Netlists: {list(config['target_netlist_dict'].keys())}")

    # Initialize agent with netlists
    agent.llm_client = agent._init_llm_client()
    agent._load_netlists(
        config["golden_netlist"],
        config["target_netlist_dict"],
    )

    # Show available subcircuits
    print(f"\nGolden subcircuits: {list(agent.golden_parser.subckts.keys())}")
    for key, parser in agent.target_parsers.items():
        print(f"Target [{key}] subcircuits: {list(parser.subckts.keys())}")

    print("\nEnter instance paths to resolve (type 'exit' to quit):")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            break

        if not user_input:
            continue

        print("\n[Processing...]")
        try:
            result = agent.resolve_path(user_input)
            print(f"\n>> INPUT: {user_input}")
            print(f">> RESOLVED: {result.get('resolved_path', 'N/A')}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

