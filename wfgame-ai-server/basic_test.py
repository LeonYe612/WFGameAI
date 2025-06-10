#!/usr/bin/env python3
"""
Basic test to verify system status
"""
import sys
import os

print("=== Basic System Test ===")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}...")

# Test basic imports
try:
    import django
    print(f"✓ Django version: {django.VERSION}")
except ImportError as e:
    print(f"✗ Django import failed: {e}")

try:
    import sqlalchemy
    print(f"✓ SQLAlchemy available")
except ImportError as e:
    print(f"✗ SQLAlchemy import failed: {e}")

# Test project imports
print("\n=== Project Import Test ===")
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from apps.project_monitor.database import db_manager
    print("✓ Database manager imported")
except Exception as e:
    print(f"✗ Database manager import failed: {e}")

try:
    from apps.project_monitor.monitor_service import monitor_service
    print("✓ Monitor service imported")
except Exception as e:
    print(f"✗ Monitor service import failed: {e}")

try:
    from apps.scripts.detection_manager import PROJECT_MONITOR_ENABLED
    print(f"✓ Detection manager imported, PROJECT_MONITOR_ENABLED={PROJECT_MONITOR_ENABLED}")
except Exception as e:
    print(f"✗ Detection manager import failed: {e}")

print("\n=== Test Complete ===")
