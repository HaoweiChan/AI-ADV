"""Netlist statistics analyzer example workflow."""

import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agents.workflow import EDAWorkflow
from tools.yosys_adapter import YosysAdapter

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run netlist statistics analyzer example."""
    logger.info("Running netlist statistics analyzer example")

    config_path = Path(__file__).parent.parent.parent / "configs" / "config.yml"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    workflow = EDAWorkflow(config)

    yosys_adapter = YosysAdapter(config.get("tools", {}))
    workflow.register_tool("yosys", yosys_adapter)

    sample_netlist = """
module counter(
    input clk,
    input rst,
    output reg [7:0] count
);

always @(posedge clk) begin
    if (rst)
        count <= 8'b0;
    else
        count <= count + 1;
end

endmodule

module top(
    input clk,
    input rst,
    output [7:0] count
);

counter u_counter (
    .clk(clk),
    .rst(rst),
    .count(count)
);

endmodule
"""

    input_data = {
        "content": sample_netlist,
        "filename": "counter.v",
    }

    try:
        result = workflow.run(input_data)

        if result.get("errors"):
            logger.error("Workflow completed with errors:")
            for error in result["errors"]:
                logger.error(f"  - {error}")

        report = result.get("report", "No report generated")
        print("\n" + "=" * 80)
        print("NETLIST STATISTICS ANALYZER")
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

