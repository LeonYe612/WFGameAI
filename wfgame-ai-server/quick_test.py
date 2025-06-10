import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("Testing project monitor components...")

try:
    print("1. Testing database manager...")
    from apps.project_monitor.database import db_manager
    print(f"   Database manager: {db_manager}")

    print("2. Testing monitor service...")
    from apps.project_monitor.monitor_service import monitor_service
    print(f"   Monitor service: {monitor_service}")

    print("3. Testing database connection...")
    connection_ok = db_manager.check_connection()
    print(f"   Connection OK: {connection_ok}")

    if connection_ok:
        print("4. Initializing database...")
        init_ok = db_manager.init_database()
        print(f"   Database initialized: {init_ok}")

        if init_ok:
            print("5. Getting projects...")
            projects = monitor_service.get_projects()
            print(f"   Projects count: {len(projects) if projects else 0}")

    print("SUCCESS: All components working")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
