import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LLMClient:
    def __init__(self, model=None, api_key=None, api_url=None):
        # Configurations
        # Please NOTE that API_KEY and BASE_URL are different in each domains.
        # Users can refer to internal documentation to find the most suitable BASE_URL.
        
        # Load from environment variables or use defaults
        self.api_key = api_key if api_key else os.getenv("API_KEY", "__MY_SUPER_KEY__")
        self.gateway_url = api_url if api_url else os.getenv("BASE_URL", "https://mlop-azure-rddmz.mediatek.inc")
        self.x_user_id = os.getenv("X_USER_ID", "mtkxxxxx")
        
        # Model priority: argument > env var > default
        self.model = model if model else os.getenv("MODEL_NAME", "llama3.3-70b-instruct")
        
        # Need to handle cert issues,
        # the implementation way is a little complicated.
        # Not recommended, generally it should be set to a valid cert path.
        self.http_client = httpx.Client(verify=False)
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=f"{self.gateway_url}/llm/v3/models",    # The API path is set here.
            http_client=self.http_client,
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a prompt to the LLM and returns the response text using Chat Completion.
        """
        # print(user_prompt)
        # Here use the streaming mode as the example.
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # The max_tokens is unnecessary, will automatically set to model context-size - input token count.
                # max_tokens=4096,
                stream=True,    # Remember to set this flag to enable streaming mode.
                extra_headers={
                    "x-user-id": self.x_user_id,
                },
                # Optional sampling parameters.
                # temperature=0.5, 
            )

            # Will show the output token by token.
            # We accumulate the content to return a full string.
            full_response = []
            for chunk in response:
                # Defensive check for chunk structure
                try:
                    if (
                        hasattr(chunk, "choices") and
                        isinstance(chunk.choices, list) and
                        len(chunk.choices) > 0 and
                        hasattr(chunk.choices[0], "delta") and
                        hasattr(chunk.choices[0].delta, "content")
                    ):
                        content = chunk.choices[0].delta.content
                        if content:
                            full_response.append(content)
                    else:
                        print(f"Malformed chunk or missing choices/delta/content: {chunk}")
                except Exception as chunk_error:
                    print(f"Error parsing chunk: {chunk_error} | chunk: {chunk}")
            
            return "".join(full_response)

        except Exception as e:
            print(f"Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
            # Return empty string or handle error appropriately
            return ""

