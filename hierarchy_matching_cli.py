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
        description="Match hierarchical paths between target and golden netlists.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command line arguments
  python hierarchy_matching_cli.py \\
    --target /path/to/target.scs \\
    --golden key1:/path/to/golden1.scs \\
    --path "X_ADC/X_AMP/vin"

  # Using JSON config file
  python hierarchy_matching_cli.py --config request.json

  # Interactive mode
  python hierarchy_matching_cli.py \\
    --target /path/to/target.scs \\
    --golden key1:/path/to/golden1.scs \\
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
        "--target",
        type=str,
        help="Path to target netlist file",
    )
    input_group.add_argument(
        "--golden",
        type=str,
        action="append",
        help="Golden netlist in format 'key:path' (can be repeated)",
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
        if not args.target:
            logger.error("Either --config or --target is required")
            parser.print_help()
            sys.exit(1)
        if not args.golden:
            logger.error("Either --config or --golden is required")
            parser.print_help()
            sys.exit(1)

        # Build config from arguments
        golden_dict = {}
        for g in args.golden:
            if ":" not in g:
                logger.error(f"Invalid golden format: {g}. Expected 'key:path'")
                sys.exit(1)
            key, path = g.split(":", 1)
            golden_dict[key] = path

        config = {
            "version": 1,
            "target_netlist": args.target,
            "golden_netlist_dict": golden_dict,
            "instance_paths": args.path or [],
            "options": {"model": args.model},
        }

    # Validate paths
    target_path = config.get("target_netlist")
    if not os.path.exists(target_path):
        logger.error(f"Target netlist not found: {target_path}")
        sys.exit(1)

    for key, path in config.get("golden_netlist_dict", {}).items():
        if not os.path.exists(path):
            logger.error(f"Golden netlist [{key}] not found: {path}")
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
            "target_netlist": config["target_netlist"],
            "golden_netlist_dict": config["golden_netlist_dict"],
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
    print(f"Target Netlist: {config['target_netlist']}")
    print(f"Golden Netlists: {list(config['golden_netlist_dict'].keys())}")

    # Initialize agent with netlists
    agent.llm_client = agent._init_llm_client()
    agent._load_netlists(
        config["target_netlist"],
        config["golden_netlist_dict"],
    )

    # Show available subcircuits
    print(f"\nTarget subcircuits: {list(agent.target_parser.subckts.keys())}")
    for key, parser in agent.golden_parsers.items():
        print(f"Golden [{key}] subcircuits: {list(parser.subckts.keys())}")

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

