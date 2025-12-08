import requests
import json
import argparse
import sys
import os

def test_api(url, payload_path):
    print(f"Loading payload from {payload_path}...")
    try:
        with open(payload_path, 'r') as f:
            payload = json.load(f)
    except Exception as e:
        print(f"Error loading payload: {e}")
        return

    # Check if files referenced in payload exist (client-side check, optional but helpful)
    if "target_netlist" in payload and not os.path.exists(payload["target_netlist"]):
        print(f"Warning: Target netlist '{payload['target_netlist']}' not found locally.")
    
    print(f"Sending POST request to {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        print("\nResponse Status Code:", response.status_code)
        print("\nResponse Body:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print("Response content:", e.response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Hierarchy Matching API")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/hierarchy-matching", help="API URL")
    parser.add_argument("--payload", default="tests/test_api_payload.json", help="Path to JSON payload")
    
    args = parser.parse_args()
    
    # Resolve payload path relative to current dir or script dir if needed
    if not os.path.exists(args.payload):
         # Try looking in tests/ if run from root
         alt_path = os.path.join("tests", os.path.basename(args.payload))
         if os.path.exists(alt_path):
             args.payload = alt_path
    
    test_api(args.url, args.payload)

