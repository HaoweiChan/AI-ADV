#!/bin/bash
# Run the Hierarchy Matching CLI

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Pass all arguments to the CLI
python hierarchy_matching_cli.py "$@"

