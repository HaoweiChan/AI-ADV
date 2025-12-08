# ADV-Agent Code Integration

This document details the process and changes made to integrate the code from `ADV-Agent/` into the main project structure. The goal was to remove the dependency on the `ADV-Agent/` submodule/folder and `sys.path` modifications.

## Summary of Changes

The functionality previously provided by `ADV-Agent` has been moved to `tools/` and `tests/`.

### 1. File Migration

The following files were copied from `ADV-Agent/` to their new locations:

| Source (ADV-Agent) | Destination (Main Project) | Description |
| ------------------ | -------------------------- | ----------- |
| `src/llm_client.py` | `tools/llm_client.py` | LLM client wrapper (OpenAI/Azure). |
| `src/netlist_parser.py` | `tools/spice_parser.py` | Regex-based SPICE/SCS parser. Kept as a separate file to avoid conflicts with `tools/netlist_parser.py`. |
| `test_scs_parser.py` | `tests/test_spice_parser.py` | Unit tests for the parser. Updated to use project data. |

### 2. Code Updates

Files in the main project were updated to import from the new locations instead of relying on `import src` or `sys.path` hacking.

#### `agents/hierarchy_matching_agent.py`
*   **Removed:** Code that added `ADV-Agent` to `sys.path`.
*   **Updated Imports:**
    *   From: `from src.llm_client import LLMClient`
    *   To: `from tools.llm_client import LLMClient`
    *   From: `from src.netlist_parser import SpiceParser`
    *   To: `from tools.spice_parser import SpiceParser`

#### `api/server.py`
*   **Removed:** Code that added `ADV-Agent` to `sys.path`.
*   **Updated Imports:**
    *   From: `from src.netlist_parser import SpiceParser`
    *   To: `from tools.spice_parser import SpiceParser`

#### Shell Scripts (`scripts/`)
*   **Cleaned:** Removed temporary `PYTHONPATH` adjustments.

### 3. Verification

The integration can be verified by running the tests and the API server:

1.  **Run Tests:**
    ```bash
    python3 tests/test_spice_parser.py
    ```

2.  **Run API Server:**
    ```bash
    scripts/run_hierarchy_matching_api.sh
    ```

### 4. Cleanup

The `ADV-Agent/` directory is now redundant and can be safely deleted.
