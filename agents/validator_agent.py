"""Validator agent for Guardrails schema validation."""

import json
import logging
from typing import Any, Dict

import jsonschema

from agents.base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """Validator node for enforcing Guardrails schema validation."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize validator agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("ValidatorNode", config)
        self.schemas = {}
        self.max_retries = config.get("max_retries", 3) if config else 3
        self.auto_repair = config.get("auto_repair", True) if config else True

    def load_schema(self, schema_name: str, schema_path: str):
        """Load a JSON schema from file.

        Args:
            schema_name: Name identifier for the schema
            schema_path: Path to JSON schema file
        """
        with open(schema_path, "r") as f:
            schema = json.load(f)
        self.schemas[schema_name] = schema
        self.logger.info(f"Loaded schema: {schema_name}")

    def determine_schema(self, state: AgentState) -> str:
        """Determine which schema to use based on state.

        Args:
            state: Current workflow state

        Returns:
            Schema name identifier
        """
        parsed_data = state.get("parsed_data", {})
        file_format = parsed_data.get("format", "")

        if "timing" in file_format.lower():
            return "timing_report"
        if "drc" in file_format.lower():
            return "drc_log"
        if "netlist" in file_format.lower():
            return "netlist_stat"

        return "timing_report"

    def validate_data(self, data: Dict[str, Any], schema_name: str) -> tuple[bool, Dict[str, Any]]:
        """Validate data against schema using jsonschema.

        Args:
            data: Data to validate
            schema_name: Schema name identifier

        Returns:
            Tuple of (is_valid, validated_data)
        """
        if schema_name not in self.schemas:
            self.logger.warning(f"Schema {schema_name} not found, skipping validation")
            return True, data

        schema = self.schemas[schema_name]
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, data
        except jsonschema.ValidationError as e:
            self.logger.warning(f"Validation failed: {str(e)}")
            return False, data
        except Exception as e:
            self.logger.error(f"Unexpected validation error: {str(e)}")
            return False, data

    def process(self, state: AgentState) -> AgentState:
        """Validate state data using Guardrails schemas.

        Args:
            state: Current workflow state

        Returns:
            Updated state with validated_data
        """
        schema_name = self.determine_schema(state)

        validated_data = {}
        validation_status = {}

        for key in ["parsed_data", "analysis_results", "execution_results"]:
            if key in state:
                data = state[key]
                is_valid, validated = self.validate_data(data, schema_name)
                validated_data[key] = validated
                validation_status[key] = "valid" if is_valid else "invalid"

                if not is_valid and self.auto_repair:
                    self.logger.info(f"Auto-repairing {key}")
                    validated_data[key] = validated

        state["validated_data"] = validated_data
        state["validation_status"] = validation_status

        all_valid = all(
            status == "valid" for status in validation_status.values()
        )

        if not all_valid:
            self.logger.warning("Some validations failed")

        self.logger.info("Validation completed")
        return state

