import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("Testing Django integration fix...")

try:
    from apps.scripts.detection_manager import PROJECT_MONITOR_ENABLED
    print(f"SUCCESS: PROJECT_MONITOR_ENABLED = {PROJECT_MONITOR_ENABLED}")
except Exception as e:
    print(f"ERROR: {e}")
