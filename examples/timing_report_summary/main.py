"""Timing report summary example workflow."""

import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agents.workflow import EDAWorkflow
from tools.opensta_adapter import OpenSTAAdapter

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run timing report summary example."""
    logger.info("Running timing report summary example")

    config_path = Path(__file__).parent.parent.parent / "configs" / "config.yml"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    workflow = EDAWorkflow(config)

    opensta_adapter = OpenSTAAdapter(config.get("tools", {}))
    workflow.register_tool("opensta", opensta_adapter)

    sample_timing_report = """
Startpoint: reg1
Endpoint: reg2
Path Group: clk
Path Type: max

Point                                    Incr       Path
----------------------------------------------------------
clock clk (rise edge)                    0.00       0.00
reg1 (DFF)                               0.10       0.10
net (wire)                               1.50       1.60
reg2 (DFF)                               0.10       1.70
----------------------------------------------------------
data arrival time                                   1.70

clock clk (rise edge)                    10.00      10.00
clock network delay (ideal)               0.00      10.00
reg2 (DFF) setup                         0.50       9.50
----------------------------------------------------------
data required time                                  9.50
----------------------------------------------------------
slack (MET)                                           7.80

Setup violation found: -0.30
Hold violation found: 0.20
"""

    input_data = {
        "content": sample_timing_report,
        "filename": "timing_report.rpt",
    }

    try:
        result = workflow.run(input_data)

        if result.get("errors"):
            logger.error("Workflow completed with errors:")
            for error in result["errors"]:
                logger.error(f"  - {error}")

        report = result.get("report", "No report generated")
        print("\n" + "=" * 80)
        print("TIMING REPORT SUMMARY")
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

