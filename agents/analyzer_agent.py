"""Analyzer agent for LLM-powered analysis of parsed data."""

import os
import logging
from typing import Any, Dict, Optional

import requests
from langchain_openai import ChatOpenAI

from agents.base_agent import AgentState, BaseAgent

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    """Analyzer node for reasoning over parsed data."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize analyzer agent.

        Args:
            config: Optional configuration dictionary
        """
        super().__init__("AnalyzerNode", config)

        # Get Mediatek API configuration from environment
        endpoint = os.getenv("GAISF_ENDPOINT")
        api_key = os.getenv("GAISF_API_KEY")
        account_id = os.getenv("GAISF_ACCOUNT_ID")

        if not endpoint or not api_key or not account_id:
            raise ValueError(
                "Missing required environment variables: GAISF_ENDPOINT, GAISF_API_KEY, GAISF_ACCOUNT_ID"
            )

        self.endpoint = endpoint
        self.api_key = api_key
        self.account_id = account_id

        llm_config = config.get("llm", {}) if config else {}
        temperature = llm_config.get("temperature", 0.0)
        max_tokens = llm_config.get("max_tokens", 2000)

        # Get model name from config or retrieve available models
        model_name = llm_config.get("model")
        if not model_name:
            model_name = self._get_available_model()
            if not model_name:
                raise ValueError("No model specified and model info retrieval failed")

        # Construct base URL: https://{endpoint}/llm/v3/models/{model_name}
        base_url = f"https://{endpoint}/llm/v3/models/{model_name}"

        # Create custom httpx client with required headers
        import httpx

        http_client = httpx.Client(
            headers={
                "X-User-Id": account_id,
                "api-key": api_key,
            },
            timeout=60.0,
        )

        # Initialize ChatOpenAI with custom base URL and API key
        # ChatOpenAI works with Mediatek API because it's OpenAI-compatible
        # The model name (e.g., "llama3.1-70b-instruct") is just passed as a string to the API
        # Custom headers (X-User-Id, api-key) are handled via the httpx client
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_base=base_url,
            openai_api_key=api_key,
            http_client=http_client,
        )

        self.logger.info(f"Using Mediatek API endpoint: {endpoint}, model: {model_name}")

    def _get_available_model(self) -> Optional[str]:
        """Retrieve available model from Mediatek API.

        Returns:
            First available model name, or None if retrieval fails
        """
        try:
            info_url = f"https://{self.endpoint}/llm/v3/info"
            headers = {
                "Content-Type": "application/json",
                "X-User-Id": self.account_id,
                "api-key": self.api_key,
            }

            response = requests.get(info_url, headers=headers, timeout=10)
            response.raise_for_status()

            info_data = response.json()
            # Parse model info response to get available models
            # Adjust parsing based on actual API response structure
            if isinstance(info_data, dict):
                models = info_data.get("models", [])
                if models and isinstance(models, list) and len(models) > 0:
                    model_name = models[0].get("name") if isinstance(models[0], dict) else models[0]
                    self.logger.info(f"Retrieved available model: {model_name}")
                    return model_name

            self.logger.warning("Model info response format unexpected, using default")
            return None

        except Exception as e:
            self.logger.error(f"Failed to retrieve model info: {str(e)}")
            return None

    def create_analysis_prompt(self, parsed_data: Dict[str, Any]) -> str:
        """Create analysis prompt based on parsed data format.

        Args:
            parsed_data: Parsed data from parser node

        Returns:
            Formatted prompt string
        """
        file_format = parsed_data.get("format", "unknown")
        data = parsed_data.get("data", {})

        if file_format == "log":
            prompt = f"""Analyze this EDA log file and extract key metrics:

Log Data:
{data}

Please provide:
1. Summary of errors and warnings
2. Key metrics or statistics
3. Recommendations or issues found
4. Overall status assessment

Format your response as structured JSON."""
        elif file_format == "netlist":
            prompt = f"""Analyze this netlist and extract design metrics:

Netlist Data:
{data}

Please provide:
1. Module count and hierarchy
2. Estimated gate count
3. Design complexity metrics
4. Potential issues or recommendations

Format your response as structured JSON."""
        else:
            prompt = f"""Analyze this EDA data and extract key insights:

Data Format: {file_format}
Data:
{data}

Please provide:
1. Key metrics and statistics
2. Important findings
3. Recommendations
4. Overall assessment

Format your response as structured JSON."""

        return prompt

    def process(self, state: AgentState) -> AgentState:
        """Analyze parsed data using LLM.

        Args:
            state: Current workflow state

        Returns:
            Updated state with analysis_results
        """
        parsed_data = state.get("parsed_data")
        if not parsed_data:
            raise ValueError("No parsed_data found in state")

        prompt = self.create_analysis_prompt(parsed_data)
        self.logger.info("Sending analysis request to LLM")

        response = self.llm.invoke(prompt)
        analysis_text = response.content

        analysis_results = {
            "prompt": prompt,
            "analysis": analysis_text,
            "format": parsed_data.get("format"),
        }

        state["analysis_results"] = analysis_results
        self.logger.info("Analysis completed successfully")
        return state

