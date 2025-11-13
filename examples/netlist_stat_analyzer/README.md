# Netlist Statistics Analyzer Example

This example demonstrates analyzing a Verilog netlist to extract design statistics using Yosys.

## Usage

```bash
python examples/netlist_stat_analyzer/main.py
```

## Input

The example uses a sample Verilog netlist that includes:
- Module definitions
- Instance hierarchies
- Gate-level structures

## Output

The workflow generates a markdown report with:
- Module count and hierarchy
- Gate count by type
- Design area estimates
- Complexity metrics

