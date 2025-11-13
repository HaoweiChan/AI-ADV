# DRC Log Parser Example

This example demonstrates parsing and categorizing DRC (Design Rule Check) violations from OpenROAD logs.

## Usage

```bash
python examples/drc_log_parser/main.py
```

## Input

The example uses a sample DRC log that includes:
- Spacing violations
- Width violations
- Area violations
- Warnings and errors

## Output

The workflow generates a markdown report categorizing:
- Error types and counts
- Violation locations
- Recommendations for fixing DRC issues

