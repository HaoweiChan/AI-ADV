# EDA Agent Template

A reusable, modular agentic framework for building AI-assisted EDA (Electronic Design Automation) workflows using LangGraph, Guardrails, and external EDA tool integrations.

## Features

- **LangGraph Orchestration**: Multi-step reasoning workflows with conditional edges and error recovery
- **Guardrails Validation**: Structured output validation using JSON schemas
- **EDA Tool Integration**: Adapters for OpenSTA, OpenROAD, and Yosys
- **Multiple Interfaces**: CLI and Streamlit web UI
- **Extensible Architecture**: Easy to add new agents, tools, and schemas

## Quick Start

### Installation

```bash
# Clone the repository from Gitea
git clone <gitea-repository-url>
cd Agentic-Template

# Install dependencies from company mirror
# Set PIP_INDEX_URL to your company's PyPI mirror
export PIP_INDEX_URL=<your-company-pypi-mirror>
pip install -r requirements.txt

# Set up environment variables
# Copy .env.example to .env and update with your credentials
cp .env.example .env
# Edit .env and set:
# - GAISF_ENDPOINT (e.g., mlop-azure-gateway.mediatek.inc)
# - GAISF_API_KEY (your API key)
# - GAISF_ACCOUNT_ID (your account ID, e.g., mtk10671)
```

### Running Examples

```bash
# Run timing report summary example
python examples/timing_report_summary/main.py

# Run DRC log parser example
python examples/drc_log_parser/main.py

# Run netlist statistics analyzer
python examples/netlist_stat_analyzer/main.py
```

### Using the CLI

```bash
# Run workflow on a file
eda-agent run input.txt --output report.md --format markdown

# Validate data against schema
eda-agent validate schema.json data.json

# List available examples
eda-agent list-examples
```

### Using the Web UI

```bash
# Start Streamlit app
streamlit run ui/app.py
```

Then open your browser to `http://localhost:8501`

## Architecture

The template follows a modular architecture with five core agent nodes:

1. **ParserNode**: Normalizes EDA artifacts (netlists, logs, JSON, CSV)
2. **AnalyzerNode**: LLM-powered analysis of parsed data
3. **ExecutorNode**: Orchestrates external EDA tool execution
4. **ValidatorNode**: Enforces Guardrails schema validation
5. **ReporterNode**: Generates human-readable reports

### Workflow Graph

```
Input File → Parser → Analyzer → Executor → Validator → Reporter → Output
```

Each node validates its output and can trigger retry loops if validation fails.

## Project Structure

```
eda-agent-template/
├── agents/              # LangGraph node implementations
├── tools/              # EDA tool adapters
├── schemas/            # Guardrails JSON schemas
├── ui/                 # CLI and Streamlit interfaces
├── tests/              # Unit and integration tests
├── examples/           # Example workflows
├── configs/            # Configuration files
└── README.md           # This file
```

## Configuration

### Environment Variables

The framework uses Mediatek GAI API (in-house only). Required environment variables:

1. **GAISF_ENDPOINT**: API endpoint (e.g., `mlop-azure-gateway.mediatek.inc` or `mlop-gateway-hwrd.mediatek.inc`)
   - See GAI Service Endpoint List for available endpoints
2. **GAISF_API_KEY**: Your API key
3. **GAISF_ACCOUNT_ID**: Your account ID (e.g., `mtk10671`)

Copy `.env.example` to `.env` and fill in these values.

**Model Selection**: 
- If model name is specified in `configs/config.yml`, it will be used
- Otherwise, the system will retrieve available models via the model info API and use the first available model

### Configuration File

Edit `configs/config.yml` to customize:

- Model name (optional - will be auto-retrieved if not specified)
- Temperature and max_tokens settings
- Guardrails validation parameters
- Tool execution timeouts
- Output format preferences

## Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`:

```python
from agents.base_agent import BaseAgent, AgentState

class MyAgent(BaseAgent):
    def process(self, state: AgentState) -> AgentState:
        # Your processing logic
        return state
```

2. Register it in the workflow:

```python
workflow.add_node("my_agent", MyAgent())
```

## Adding New Tools

1. Create an adapter inheriting from `BaseAdapter`:

```python
from tools.base_adapter import BaseAdapter

class MyToolAdapter(BaseAdapter):
    def run(self, content: str, parsed_data: dict = None) -> dict:
        # Tool execution logic
        return results
    
    def parse_output(self, output: str) -> dict:
        # Output parsing logic
        return parsed_data
```

2. Register it with the executor:

```python
workflow.register_tool("my_tool", MyToolAdapter())
```

## Adding New Schemas

1. Create a JSON schema file in `schemas/`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "my_field": {"type": "string"}
  }
}
```

2. Load it in the validator:

```python
validator.load_schema("my_schema", "schemas/my_schema.json")
```

## Testing

```bash
# Install test dependencies from company mirror
export PIP_INDEX_URL=<your-company-pypi-mirror>
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=tools --cov=ui

# Run specific test file
pytest tests/test_agents.py
```

## Docker

```bash
# Build Docker image with company PyPI mirror
docker build --build-arg PIP_INDEX_URL=<your-company-pypi-mirror> -t eda-agent-template .

# Run with docker-compose
docker-compose up

# Or run directly
docker run -p 8501:8501 eda-agent-template
```

**Note**: EDA tools (OpenSTA, OpenROAD, Yosys) must be pre-installed in the base image or available via pip install from your company mirror.

## Examples

### Timing Report Summary

Analyzes OpenSTA timing reports to extract violations and critical paths.

### DRC Log Parser

Parses OpenROAD DRC logs to categorize violations by type and location.

### Netlist Statistics Analyzer

Uses Yosys to analyze Verilog netlists and extract design metrics.

## Contributing

1. Fork the repository on Gitea
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a merge request