import requests
import json
import sys
import os

# Server URL
BASE_URL = "http://localhost:8000/api/scripts"

def test_debug_script():
    """Test the debug_script function"""
    print("\n=== Testing debug_script function ===")

    url = f"{BASE_URL}/debug/"
    payload = {
        "command": "record_script.py"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✓ Debug script test passed!")
            return True
        else:
            print("✗ Debug script test failed!")
            return False
    except Exception as e:
        print(f"Error testing debug_script: {e}")
        return False

def test_replay_script():
    """Test the replay_script function"""
    print("\n=== Testing replay_script function ===")

    # Create a test JSON file if it doesn't exist
    test_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "wfgame-ai-server", "testcase", "test_script.json")
    if not os.path.exists(test_json_path):
        os.makedirs(os.path.dirname(test_json_path), exist_ok=True)
        with open(test_json_path, 'w') as f:
            json.dump({"test": "data"}, f)

    url = f"{BASE_URL}/replay/"
    payload = {
        "scripts": [
            {
                "path": "test_script.json",
                "loop_count": 1
            }
        ],
        "show_screens": True
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✓ Replay script test passed!")
            return True
        else:
            print("✗ Replay script test failed!")
            return False
    except Exception as e:
        print(f"Error testing replay_script: {e}")
        return False

def test_start_record():
    """Test the start_record function"""
    print("\n=== Testing start_record function ===")

    url = f"{BASE_URL}/record/"

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code == 200:
            print("✓ Start record test passed!")
            return True
        else:
            print("✗ Start record test failed!")
            return False
    except Exception as e:
        print(f"Error testing start_record: {e}")
        return False

if __name__ == "__main__":
    print("Starting script management functions tests...\n")

    # Make sure the Django server is running first

    debug_result = test_debug_script()
    replay_result = test_replay_script()
    record_result = test_start_record()

    print("\n=== Test Summary ===")
    print(f"Debug script test: {'Passed' if debug_result else 'Failed'}")
    print(f"Replay script test: {'Passed' if replay_result else 'Failed'}")
    print(f"Start record test: {'Passed' if record_result else 'Failed'}")

    # Return non-zero exit code if any test failed
    if not all([debug_result, replay_result, record_result]):
        sys.exit(1)
