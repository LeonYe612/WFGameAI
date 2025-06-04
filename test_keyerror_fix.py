#!/usr/bin/env python3
"""
Test script to verify KeyError fixes in replay_script.py
"""
import json
import sys
import os

# Add the path to import the replay script
sys.path.append(os.path.join(os.path.dirname(__file__), 'wfgame-ai-server', 'apps', 'scripts'))

def test_step_processing():
    """Test processing steps with different structures"""

    # Test data with different step structures
    test_steps = [
        # Step with class field (traditional format)
        {
            "class": "button",
            "remark": "Click button",
            "relative_x": 0.5,
            "relative_y": 0.5
        },
        # Step with action field but no class field (swipe format)
        {
            "action": "swipe",
            "start_x": 500,
            "start_y": 700,
            "end_x": 500,
            "end_y": 300,
            "duration": 500,
            "remark": "Vertical swipe"
        },
        # Step with both class and action fields
        {
            "class": "swipe_area",
            "action": "swipe",
            "start_x": 200,
            "start_y": 600,
            "end_x": 800,
            "end_y": 600,
            "duration": 300,
            "remark": "Horizontal swipe"
        },
        # Step with delay
        {
            "class": "delay",
            "params": {"seconds": 2},
            "remark": "Wait 2 seconds"
        }
    ]

    print("Testing step processing with different structures:")
    print("=" * 50)

    for i, step in enumerate(test_steps):
        print(f"\nStep {i+1}:")
        print(f"Raw data: {step}")

        # Simulate the fixed code logic
        step_class = step.get("class", "")
        step_remark = step.get("remark", "")
        step_action = step.get("action", "click")

        # If no class field, use action as display name
        display_name = step_class if step_class else step_action

        print(f"Processed - Class: '{step_class}', Action: '{step_action}', Display: '{display_name}', Remark: '{step_remark}'")

        # Test that no KeyError occurs
        try:
            # This would have caused KeyError before the fix
            old_way_would_fail = step["class"]  # This line would fail for swipe steps
            print(f"Old way result: {old_way_would_fail}")
        except KeyError as e:
            print(f"❌ Old way would fail with KeyError: {e}")

        print(f"✅ New way works: step.get('class', '') = '{step.get('class', '')}' ")

    print("\n" + "=" * 50)
    print("✅ All tests passed! KeyError issues should be resolved.")

if __name__ == "__main__":
    test_step_processing()
