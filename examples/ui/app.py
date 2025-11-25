"""Streamlit web UI for EDA Agent Template."""

import json
import yaml
import logging
import streamlit as st
from dotenv import load_dotenv
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


def load_config():
    """Load configuration."""
    config_path = Path(__file__).parent.parent / "configs" / "config.yml"
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}


def initialize_workflow():
    """Initialize workflow with tool adapters."""
    if "workflow" not in st.session_state:
        config = load_config()
        workflow = EDAWorkflow(config)

        opensta_adapter = OpenSTAAdapter(config.get("tools", {}))
        openroad_adapter = OpenROADAdapter(config.get("tools", {}))
        yosys_adapter = YosysAdapter(config.get("tools", {}))

        workflow.register_tool("opensta", opensta_adapter)
        workflow.register_tool("openroad", openroad_adapter)
        workflow.register_tool("yosys", yosys_adapter)

        st.session_state.workflow = workflow
        st.session_state.config = config

    return st.session_state.workflow


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="EDA Agent Template",
        page_icon="🔧",
        layout="wide",
    )

    st.title("🔧 EDA Agent Template")
    st.markdown("AI-assisted EDA workflow automation using LangGraph")

    workflow = initialize_workflow()

    st.sidebar.header("Configuration")
    output_format = st.sidebar.selectbox(
        "Output Format", ["markdown", "html", "cli"], index=0
    )

    st.header("Input")
    input_method = st.radio("Input Method", ["Upload File", "Paste Text"])

    input_content = None
    filename = "input.txt"

    if input_method == "Upload File":
        uploaded_file = st.file_uploader("Choose a file", type=["txt", "log", "v", "json", "csv"])
        if uploaded_file:
            input_content = uploaded_file.read().decode("utf-8")
            filename = uploaded_file.name
    else:
        input_content = st.text_area("Paste file content", height=200)
        filename = st.text_input("Filename", value="input.txt")

    if st.button("Run Workflow", type="primary") and input_content:
        with st.spinner("Running workflow..."):
            config = st.session_state.config.copy()
            config.setdefault("output", {})["format"] = output_format

            workflow_instance = EDAWorkflow(config)
            workflow_instance.register_tool("opensta", OpenSTAAdapter(config.get("tools", {})))
            workflow_instance.register_tool("openroad", OpenROADAdapter(config.get("tools", {})))
            workflow_instance.register_tool("yosys", YosysAdapter(config.get("tools", {})))

            input_data = {
                "content": input_content,
                "filename": filename,
            }

            try:
                result = workflow_instance.run(input_data)

                st.success("Workflow completed!")

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Workflow Status")
                    if result.get("errors"):
                        st.error(f"Errors: {len(result['errors'])}")
                        for error in result["errors"]:
                            st.error(error)
                    else:
                        st.success("No errors")

                with col2:
                    st.subheader("Execution Info")
                    parsed_data = result.get("parsed_data", {})
                    if parsed_data:
                        st.info(f"Format: {parsed_data.get('format', 'unknown')}")

                    execution_results = result.get("execution_results", {})
                    if execution_results:
                        st.info(f"Tool: {execution_results.get('tool', 'none')}")
                        st.info(f"Status: {execution_results.get('status', 'unknown')}")

                st.subheader("Results")
                tabs = st.tabs(["Report", "Parsed Data", "Analysis", "Validation"])

                with tabs[0]:
                    report = result.get("report", "No report generated")
                    st.markdown(report)
                    st.download_button(
                        "Download Report",
                        report,
                        file_name=f"report.{output_format}",
                        mime="text/plain" if output_format != "html" else "text/html",
                    )

                with tabs[1]:
                    parsed_data = result.get("parsed_data", {})
                    if parsed_data:
                        st.json(parsed_data)

                with tabs[2]:
                    analysis_results = result.get("analysis_results", {})
                    if analysis_results:
                        st.json(analysis_results)

                with tabs[3]:
                    validation_status = result.get("validation_status", {})
                    if validation_status:
                        st.json(validation_status)
                    else:
                        st.info("No validation status available")

            except Exception as e:
                st.error(f"Workflow failed: {str(e)}")
                logger.exception("Workflow execution error")

    st.sidebar.markdown("---")
    st.sidebar.header("About")
    st.sidebar.markdown(
        """
        EDA Agent Template provides a reusable framework
        for building AI-assisted EDA workflows.

        **Features:**
        - LangGraph orchestration
        - Guardrails validation
        - EDA tool integration
        - Multiple output formats
        """
    )

if __name__ == "__main__":
    main()

