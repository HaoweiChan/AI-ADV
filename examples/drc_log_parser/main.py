"""DRC log parser example workflow."""

import sys
import yaml
import logging
from dotenv import load_dotenv
from pathlib import Path
from examples.agents.workflow import EDAWorkflow
from examples.tools.openroad_adapter import OpenROADAdapter

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run DRC log parser example."""
    logger.info("Running DRC log parser example")

    config_path = Path(__file__).parent.parent.parent / "configs" / "config.yml"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    workflow = EDAWorkflow(config)

    openroad_adapter = OpenROADAdapter(config.get("tools", {}))
    workflow.register_tool("openroad", openroad_adapter)

    sample_drc_log = """
[INFO] Starting DRC check...
[ERROR] DRC violation: Spacing violation at layer M1
  Location: (1000, 2000)
  Rule: min_spacing 0.14um
  Actual: 0.10um
[ERROR] DRC violation: Width violation at layer M2
  Location: (1500, 3000)
  Rule: min_width 0.15um
  Actual: 0.12um
[WARNING] DRC warning: Area violation at layer POLY
  Location: (2000, 4000)
  Rule: min_area 0.05um^2
  Actual: 0.04um^2
[INFO] DRC check completed.
Total violations: 2
Total warnings: 1
"""

    input_data = {
        "content": sample_drc_log,
        "filename": "drc.log",
    }

    try:
        result = workflow.run(input_data)

        if result.get("errors"):
            logger.error("Workflow completed with errors:")
            for error in result["errors"]:
                logger.error(f"  - {error}")

        report = result.get("report", "No report generated")
        print("\n" + "=" * 80)
        print("DRC LOG PARSER")
        print("=" * 80)
        print(report)

        output_file = Path(__file__).parent / "output.md"
        output_file.write_text(report)
        logger.info(f"Report saved to {output_file}")

        return 0 if not result.get("errors") else 1

    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())

