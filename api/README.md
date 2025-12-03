# Hierarchy Matching API

FastAPI-based REST API for matching hierarchical paths between golden and target netlists.

## Quick Start

### Start the API Server

```bash
# Using the script
./scripts/run_hierarchy_matching_api.sh

# Or directly with uvicorn
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Hierarchy Matching
```bash
curl -X POST http://localhost:8000/api/v1/hierarchy-matching \
  -H "Content-Type: application/json" \
  -d @examples/hierarchy_matching_request.json
```

#### List Subcircuits
```bash
curl "http://localhost:8000/api/v1/subcircuits?netlist_path=/path/to/netlist.scs"
```

## Request Format

```json
{
  "version": 1,
  "golden_netlist": "/path/to/golden/input.scs",
  "golden_bench_path": "/path/to/golden/bench/maestro",
  "target_netlist_dict": {
    "key1": "/path/to/target/input1.scs",
    "key2": "/path/to/target/input2.scs"
  },
  "target_bench_path": "/path/to/output/bench/maestro",
  "bench_type": "maestro",
  "simulator": "spectre",
  "instance_paths": [
    "X_ADC/X_AMP/vin",
    "scm_demo/SIMTR_SB_TX/out"
  ],
  "options": {
    "model": "llama3.3-70b-instruct",
    "verbose": false,
    "dry_run": false
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | int | Yes | API version (currently 1) |
| `golden_netlist` | string | Yes | Path to golden/reference netlist file (.scs) |
| `golden_bench_path` | string | No | Path to golden testbench directory |
| `target_netlist_dict` | object | Yes | Dictionary mapping target IDs to netlist paths |
| `target_bench_path` | string | No | Output path for new testbench |
| `bench_type` | string | No | Testbench type (maestro, ade_xl, custom) |
| `simulator` | string | No | Simulator type (spectre, hspice, xcelium) |
| `instance_paths` | array | No | List of hierarchical paths to resolve |
| `options` | object | No | Additional processing options |

## Response Format

```json
{
  "success": true,
  "message": "Hierarchy matching completed successfully",
  "data": {
    "analysis_results": {
      "resolutions": [...],
      "golden_subcircuits": [...],
      "target_subcircuits": {...}
    },
    "report": "...",
    "metadata": {...}
  }
}
```

## CLI Usage

```bash
# Using config file
python hierarchy_matching_cli.py --config examples/hierarchy_matching_request.json

# Using command line arguments
python hierarchy_matching_cli.py \
  --golden /path/to/golden.scs \
  --target key1:/path/to/target1.scs \
  --path "X_ADC/X_AMP/vin" \
  --model llama3.3-70b-instruct

# Interactive mode
python hierarchy_matching_cli.py \
  --golden /path/to/golden.scs \
  --target key1:/path/to/target1.scs \
  --interactive
```

## Environment Variables

Set these in a `.env` file or export them:

```bash
export API_KEY="your-api-key"
export BASE_URL="https://mlop-azure-rddmz.mediatek.inc"
export X_USER_ID="mtkxxxxx"
export MODEL_NAME="llama3.3-70b-instruct"
```

## OpenAPI Documentation

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

