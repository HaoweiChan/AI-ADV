"""Command-line interface for EDA Agent Template."""

import sys
import json
import yaml
import click
import logging
from dotenv import load_dotenv
from typing import Optional
from pathlib import Path
from examples.agents.workflow import EDAWorkflow
from examples.tools.yosys_adapter import YosysAdapter
from examples.tools.opensta_adapter import OpenSTAAdapter
from examples.tools.openroad_adapter import OpenROADAdapter

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from file.

    Args:
        config_path: Optional path to config file

    Returns:
        Configuration dictionary
    """
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    default_config_path = Path(__file__).parent.parent / "configs" / "config.yml"
    if default_config_path.exists():
        with open(default_config_path, "r") as f:
            return yaml.safe_load(f)

    return {}


@click.group()
def cli():
    """EDA Agent Template CLI."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", "-f", type=click.Choice(["markdown", "html", "cli"]), default="markdown", help="Output format")
def run(input_file: str, config: Optional[str], output: Optional[str], format: str):
    """Run EDA workflow on input file."""
    logger.info(f"Running workflow on {input_file}")

    config_dict = load_config(Path(config) if config else None)
    if format:
        config_dict.setdefault("output", {})["format"] = format

    workflow = EDAWorkflow(config_dict)

    opensta_adapter = OpenSTAAdapter(config_dict.get("tools", {}))
    openroad_adapter = OpenROADAdapter(config_dict.get("tools", {}))
    yosys_adapter = YosysAdapter(config_dict.get("tools", {}))

    workflow.register_tool("opensta", opensta_adapter)
    workflow.register_tool("openroad", openroad_adapter)
    workflow.register_tool("yosys", yosys_adapter)

    input_path = Path(input_file)
    with open(input_path, "r") as f:
        content = f.read()

    input_data = {
        "content": content,
        "filename": input_path.name,
    }

    try:
        result = workflow.run(input_data)

        if result.get("errors"):
            logger.error("Workflow completed with errors:")
            for error in result["errors"]:
                logger.error(f"  - {error}")

        report = result.get("report", "No report generated")

        if output:
            output_path = Path(output)
            output_path.write_text(report)
            logger.info(f"Report saved to {output_path}")
        else:
            click.echo(report)

        sys.exit(0 if not result.get("errors") else 1)

    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}", exc_info=True)
        sys.exit(1)

@cli.command()
@click.argument("schema_file", type=click.Path(exists=True))
@click.argument("data_file", type=click.Path(exists=True))
def validate(schema_file: str, data_file: str):
    """Validate data file against JSON schema."""
    import jsonschema

    logger.info(f"Validating {data_file} against {schema_file}")

    with open(schema_file, "r") as f:
        schema = json.load(f)

    with open(data_file, "r") as f:
        data = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=schema)
        click.echo("✓ Validation passed")
        sys.exit(0)
    except jsonschema.ValidationError as e:
        click.echo(f"✗ Validation failed: {e.message}")
        sys.exit(1)

@cli.command()
def list_examples():
    """List available example workflows."""
    examples_dir = Path(__file__).parent.parent / "examples"

    if not examples_dir.exists():
        click.echo("No examples directory found")
        return

    click.echo("Available examples:")
    for example_dir in sorted(examples_dir.iterdir()):
        if example_dir.is_dir():
            main_file = example_dir / "main.py"
            readme_file = example_dir / "README.md"

            description = ""
            if readme_file.exists():
                with open(readme_file, "r") as f:
                    description = f.read().split("\n")[0]

            click.echo(f"  • {example_dir.name}")
            if description:
                click.echo(f"    {description}")

def main():
    """Main entry point."""
    cli()

if __name__ == "__main__":
    main()

