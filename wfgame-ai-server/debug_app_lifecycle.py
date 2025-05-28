import sys
import os
import json
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("app_debug")

# Add the current directory to the path so we can import from there
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from app_lifecycle_manager import AppLifecycleManager

def debug_app_lifecycle():
    """Debug function to check app lifecycle management functionality"""

    # Initialize the app lifecycle manager
    app_manager = AppLifecycleManager()

    # Define the app name and device ID
    app_name = "card2prepare"
    device_ids = []

    # Get device IDs
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip the "List of devices attached" line
            for line in lines:
                if line.strip():
                    device_id = line.split()[0]
                    device_ids.append(device_id)
                    logger.info(f"Found device: {device_id}")

        if not device_ids:
            logger.error("No devices connected!")
            return
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return

    # Check template details
    logger.info("Checking template details...")
    template = app_manager._load_template(app_name)

    if template:
        logger.info(f"Template found: {json.dumps(template, indent=2)}")
        logger.info(f"Package name: {template.get('package_name')}")
    else:
        logger.error(f"Template not found for app: {app_name}")
        # Try direct file access to check if the file exists
        try:
            script_template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "apps", "scripts", "app_templates"
            )
            template_path = os.path.join(script_template_dir, f"{app_name}.json")

            if os.path.exists(template_path):
                logger.info(f"Found template file using direct path: {template_path}")
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    logger.info(f"Template contents: {json.dumps(template_data, indent=2)}")
            else:
                logger.error(f"Template file does not exist at: {template_path}")

            # Also try the original app_templates directory
            root_template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "app_templates"
            )
            root_template_path = os.path.join(root_template_dir, f"{app_name}.json")

            if os.path.exists(root_template_path):
                logger.info(f"Found template file in root app_templates: {root_template_path}")
            else:
                logger.error(f"Template file does not exist at root path: {root_template_path}")

        except Exception as e:
            logger.error(f"Error accessing template file: {e}")

    # Test on each connected device
    for device_id in device_ids:
        logger.info(f"Testing with device {device_id}")

        # Check if the app is running
        package_name = template.get('package_name') if template else None
        if not package_name:
            logger.error("Unable to test: no package name found")
            continue

        logger.info(f"Testing with package name: {package_name}")

        # Check if app is currently running
        is_running = app_manager.check_app_running(package_name, device_id)
        logger.info(f"Is app running? {is_running}")

        # If running, try to stop it
        if is_running:
            logger.info(f"Attempting to stop app using app_name: {app_name}")
            stop_result = app_manager.stop_app(app_name, device_id)
            logger.info(f"Stop app result: {stop_result}")

            # Verify app was stopped
            time.sleep(2)
            is_still_running = app_manager.check_app_running(package_name, device_id)
            logger.info(f"Is app still running after stop? {is_still_running}")

            # If still running, try direct force-stop
            if is_still_running:
                logger.info(f"App still running, trying direct force-stop with package name")
                force_stop_result = app_manager.force_stop_by_package(package_name, device_id)
                logger.info(f"Force stop result: {force_stop_result}")

                time.sleep(2)
                is_still_running = app_manager.check_app_running(package_name, device_id)
                logger.info(f"Is app still running after force-stop? {is_still_running}")
        else:
            # If not running, try to start it
            logger.info(f"App not running, attempting to start it")
            start_result = app_manager.start_app(app_name, device_id)
            logger.info(f"Start app result: {start_result}")

            # Verify app was started
            time.sleep(3)
            is_now_running = app_manager.check_app_running(package_name, device_id)
            logger.info(f"Is app running after start? {is_now_running}")

            # Now try stopping it
            if is_now_running:
                logger.info(f"Now stopping the started app")
                stop_result = app_manager.stop_app(app_name, device_id)
                logger.info(f"Stop app result: {stop_result}")

                time.sleep(2)
                is_still_running = app_manager.check_app_running(package_name, device_id)
                logger.info(f"Is app still running after stop? {is_still_running}")

if __name__ == "__main__":
    debug_app_lifecycle()
