#!/usr/bin/env python3
"""Test script to verify agents can use LLM correctly through settings."""

import os
import sys
import yaml
import httpx
import requests
import urllib3
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path

# Disable SSL warnings for company internal certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import AgentState
from examples.agents.analyzer_agent import AnalyzerAgent



def print_test(name: str, status: bool, message: str = ""):
    """Print test result."""
    status_symbol = "✓" if status else "✗"
    status_text = "PASS" if status else "FAIL"
    print(f"{status_symbol} [{status_text}] {name}")
    if message:
        print(f"    {message}")
    return status

def test_environment_variables():
    """Test if required environment variables are set."""
    print("\n=== Testing Environment Variables ===")
    
    endpoint = os.getenv("GAISF_ENDPOINT")
    api_key = os.getenv("GAISF_API_KEY")
    account_id = os.getenv("GAISF_ACCOUNT_ID")
    
    results = []
    
    results.append(print_test(
        "GAISF_ENDPOINT",
        endpoint is not None and endpoint != "",
        f"Value: {endpoint if endpoint else 'NOT SET'}"
    ))
    
    results.append(print_test(
        "GAISF_API_KEY",
        api_key is not None and api_key != "",
        f"Value: {'*' * min(len(api_key), 20) if api_key else 'NOT SET'}"
    ))
    
    results.append(print_test(
        "GAISF_ACCOUNT_ID",
        account_id is not None and account_id != "",
        f"Value: {account_id if account_id else 'NOT SET'}"
    ))
    
    return all(results)

def test_config_loading():
    """Test if config file can be loaded."""
    print("\n=== Testing Config File Loading ===")
    
    config_path = Path(__file__).parent.parent / "configs" / "config.yml"
    
    if not config_path.exists():
        print_test("Config file exists", False, f"File not found: {config_path}")
        return False
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        print_test("Config file exists", True, f"Found: {config_path}")
        print_test("Config file parsing", config is not None, "YAML parsed successfully")
        
        if config:
            llm_config = config.get("llm", {})
            print(f"    LLM Config: temperature={llm_config.get('temperature')}, "
                  f"max_tokens={llm_config.get('max_tokens')}")
            if "model" in llm_config:
                print(f"    Model: {llm_config['model']}")
            else:
                print("    Model: Will be retrieved from API")
        
        return True
    except Exception as e:
        print_test("Config file parsing", False, f"Error: {str(e)}")
        return False

def test_analyzer_agent_initialization():
    """Test if AnalyzerAgent can be initialized."""
    print("\n=== Testing AnalyzerAgent Initialization ===")
    
    config_path = Path(__file__).parent.parent / "configs" / "config.yml"
    config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    
    try:
        analyzer = AnalyzerAgent(config)
        model_info = getattr(analyzer.llm, 'model_name', None) or getattr(analyzer.llm, 'model', 'unknown')
        print_test("AnalyzerAgent initialization", True, f"Model: {model_info}")
        return True, analyzer
    except ValueError as e:
        print_test("AnalyzerAgent initialization", False, f"ValueError: {str(e)}")
        return False, None
    except Exception as e:
        print_test("AnalyzerAgent initialization", False, f"Error: {str(e)}")
        return False, None


def test_llm_api_call(analyzer: AnalyzerAgent):
    """Test if LLM can make a simple API call."""
    print("\n=== Testing LLM API Call ===")
    
    if analyzer is None:
        print_test("LLM API call", False, "AnalyzerAgent not initialized")
        return False
    
    try:
        test_prompt = "Say 'Hello, LLM test successful!' and nothing else."
        print(f"    Sending test prompt: {test_prompt}")
        
        response = analyzer.llm.invoke(test_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        print_test("LLM API call", True, f"Response received: {response_text[:100]}...")
        return True
    except Exception as e:
        print_test("LLM API call", False, f"Error: {str(e)}")
        return False

def test_analyzer_agent_process():
    """Test if AnalyzerAgent can process data."""
    print("\n=== Testing AnalyzerAgent Process Method ===")
    
    config_path = Path(__file__).parent.parent / "configs" / "config.yml"
    config = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    
    try:
        analyzer = AnalyzerAgent(config)
        
        # Create sample parsed data
        sample_state: AgentState = {
            "input_data": {},
            "parsed_data": {
                "format": "log",
                "data": {
                    "errors": ["Sample error 1", "Sample error 2"],
                    "warnings": ["Sample warning 1"],
                }
            }
        }
        
        print("    Processing sample parsed data...")
        result_state = analyzer.process(sample_state)
        
        if "analysis_results" in result_state:
            analysis = result_state["analysis_results"].get("analysis", "")
            print_test("AnalyzerAgent process", True, f"Analysis generated ({len(analysis)} chars)")
            print(f"    Analysis preview: {analysis[:150]}...")
            return True
        else:
            print_test("AnalyzerAgent process", False, "No analysis_results in state")
            return False
    except Exception as e:
        print_test("AnalyzerAgent process", False, f"Error: {str(e)}")
        import traceback
        print(f"    Traceback: {traceback.format_exc()}")
        return False

def test_chat_completions_api():
    """Test chat completions API endpoint."""
    print("\n=== Testing Chat Completions API ===")
    
    endpoint = os.getenv("GAISF_ENDPOINT")
    api_key = os.getenv("GAISF_API_KEY")
    account_id = os.getenv("GAISF_ACCOUNT_ID")
    
    if not endpoint:
        print_test("Chat completions API", False, "GAISF_ENDPOINT not set")
        return False
    if not api_key:
        print_test("Chat completions API", False, "GAISF_API_KEY not set")
        return False
    if not account_id:
        print_test("Chat completions API", False, "GAISF_ACCOUNT_ID not set")
        return False
        
    model_name = "llama3.3-70b-instruct"
    
    # Construct base_url as per Mediatek GAI documentation
    # Format: https://{endpoint}/llm/v3/models/{model_name}
    base_url = f"https://{endpoint}/llm/v3/models/{model_name}"
    print(f"    Using base_url: {base_url}")
    
    try:
        # Configure OpenAI client with custom HTTP client for SSL verification bypass
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(verify=False)
        )
        
        print("    Sending chat completion request...")
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "hi, my name is Mike, say hi to me"
                }
            ],
            max_tokens=32,
            temperature=1,
            stream=False,
            model=model_name,
            extra_headers={
                "X-User-Id": account_id
            }
        )
        
        content = response.choices[0].message.content
        print_test("Chat completions API", True, "Response received")
        print(f"    Response preview: {content[:200]}...")
        return True
        
    except Exception as e:
        print_test("Chat completions API", False, f"Error: {str(e)}")
        return False

def test_rag_query_api():
    """Test RAG query API endpoint."""
    print("\n=== Testing RAG Query API ===")
    
    endpoint = os.getenv("GAISF_ENDPOINT")
    api_key = os.getenv("GAISF_API_KEY")
    
    if not endpoint:
        print_test("RAG query API", False, "GAISF_ENDPOINT not set")
        return False
    if not api_key:
        print_test("RAG query API", False, "GAISF_API_KEY not set")
        return False
    
    # Keep the original URL for reference (not used)
    _original_url = "https://appgw-it-hwrd.mediatek.inc/IT/GAIA/ragquery/rag/v1/agentic/query"
    
    # RAG query service is on a different host (appgw-it-hwrd) than the LLM service (mlop-gateway-hwrd)
    # So we must use the specific hostname, not GAISF_ENDPOINT
    url = "https://appgw-it-hwrd.mediatek.inc/IT/GAIA/ragquery/rag/v3/agentic/query"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-APP-NAME": "mtkoa-digaide.spec-assistant"
    }
    
    payload = {
        "service_app": "DiGaIDE",
        "channel": "Obsidian",
        "question": "請對這份文件取出chunnk資訊",
        "scope_list": [],
        "language": "None",
        "hybrid_parm_list": [
            {
                "elk_source": "rag",
                "elk_type": "rrf",
                "elk_filter_dict": {
                    "filter": {
                        "terms": {
                            "metadata.id": [
                                "8b6c8846-2714-4eb0-832e-b86d86bd84df"
                            ]
                        }
                    }
                },
                "elk_top": 5,
                "elk_detail_top": 10
            }
        ],
        "summary_parm": {
            "need_summary": False,
            "stream": False
        },
        "need_check_content_parm": {
            "need_check_greeting": True,
            "need_check_input": True,
            "need_check_output": False
        },
        "trigger_bot_name": "Document Chat Bot"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)
        response.raise_for_status()
        
        print_test("RAG query API", True, f"Status: {response.status_code}")
        try:
            response_json = response.json()
            print(f"    Response keys: {list(response_json.keys()) if isinstance(response_json, dict) else 'N/A'}")
        except:
            print(f"    Response preview: {response.text[:200]}...")
        return True
    except requests.exceptions.SSLError as e:
        print_test("RAG query API", False, f"SSL Error: {str(e)}")
        return False
    except requests.exceptions.RequestException as e:
        print_test("RAG query API", False, f"Request Error: {str(e)}")
        return False
    except Exception as e:
        print_test("RAG query API", False, f"Error: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("LLM Configuration Test Script")
    print("=" * 60)
    
    results = []
    
    # Test 1: Environment variables
    results.append(test_environment_variables())
    
    # Test 2: Config loading
    results.append(test_config_loading())
    
    # Test 3: AnalyzerAgent initialization
    init_success, analyzer = test_analyzer_agent_initialization()
    results.append(init_success)
    
    # Test 4: LLM API call (only if initialization succeeded)
    if init_success and analyzer:
        results.append(test_llm_api_call(analyzer))
    
    # Test 5: AnalyzerAgent process method
    if init_success:
        results.append(test_analyzer_agent_process())
    
    # Test 6: Chat completions API
    results.append(test_chat_completions_api())
    
    # Test 7: RAG query API
    results.append(test_rag_query_api())
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if all(results):
        print("\n✓ All tests passed! LLM configuration is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

