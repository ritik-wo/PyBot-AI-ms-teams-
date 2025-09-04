"""Card template loading utilities for Microsoft Teams bot."""
import json
import os
import glob
from typing import Optional, Dict, Any


def load_tasks_assigned_card() -> Dict[str, Any]:
    """Load the TasksAssignedToUser adaptive card template"""
    card_path = os.path.join(os.getcwd(), "resources", "post-meeting-cards", "TasksAssignedToUser.json")
    try:
        print(f"[DEBUG] ===== LOADING ADAPTIVE CARD =====")
        print(f"[DEBUG] Card path: {card_path}")
        
        with open(card_path, "r", encoding="utf-8") as f:
            card_content = f.read()
            print(f"[DEBUG] Raw file content length: {len(card_content)} characters")
            print(f"[DEBUG] First 200 characters: {card_content[:200]}")
            
            # Try to parse JSON
            adaptive_card = json.loads(card_content)
            print(f"[DEBUG] ✅ JSON parsing successful")
            print(f"[DEBUG] Card type: {adaptive_card.get('type', 'unknown')}")
            print(f"[DEBUG] Card version: {adaptive_card.get('version', 'unknown')}")
            print(f"[DEBUG] Body items count: {len(adaptive_card.get('body', []))}")
            
            # Check for problematic properties
            problematic_props = []
            def check_properties(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        if key in ['rtl', 'bleed', 'minHeight', 'backgroundImage', '$schema', 'speak']:
                            problematic_props.append(f"{current_path}: {value}")
                        if isinstance(value, (dict, list)):
                            check_properties(value, current_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        current_path = f"{path}[{i}]"
                        check_properties(item, current_path)
            
            check_properties(adaptive_card)
            if problematic_props:
                print(f"[DEBUG] ⚠️ Found potentially problematic properties:")
                for prop in problematic_props:
                    print(f"[DEBUG]   - {prop}")
            else:
                print(f"[DEBUG] ✅ No problematic properties found")
            
            return adaptive_card
            
    except json.JSONDecodeError as e:
        print(f"[ERROR] ❌ JSON parsing failed: {e}")
        print(f"[ERROR] Error at line {e.lineno}, column {e.colno}")
        print(f"[ERROR] Error message: {e.msg}")
        # Show the problematic line
        lines = card_content.split('\n')
        if e.lineno <= len(lines):
            print(f"[ERROR] Problematic line {e.lineno}: {lines[e.lineno-1]}")
        raise
    except Exception as e:
        print(f"[ERROR] ❌ Failed to load adaptive card template: {e}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        # Fallback to a simple card if template loading fails
        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "New Progress items assigned to you",
                    "weight": "Bolder",
                    "size": "Large"
                },
                {
                    "type": "TextBlock",
                    "text": "Tasks have been assigned to you. Please check your items.",
                    "wrap": True
                }
            ]
        }


def load_card_by_name(card_name: str) -> Optional[Dict[str, Any]]:
    """Load an adaptive card template by name from any subfolder in resources/"""
    base_dir = os.path.join(os.getcwd(), "resources")
    # Search for the card in all subfolders
    pattern = os.path.join(base_dir, "**", card_name)
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        print(f"[ERROR] Card template '{card_name}' not found in resources/.")
        return None
    card_path = matches[0]
    try:
        print(f"[DEBUG] Loading card: {card_path}")
        with open(card_path, "r", encoding="utf-8") as f:
            card_content = f.read()
            adaptive_card = json.loads(card_content)
            return adaptive_card
    except Exception as e:
        print(f"[ERROR] Failed to load card '{card_name}': {e}")
        return None


def load_updated_tasks_card(default_name: str = "TasksAssignedToUserUpdated.json") -> Optional[Dict[str, Any]]:
    """Convenience loader for the updated TasksAssigned card template."""
    return load_card_by_name(default_name)


def load_sample_data() -> Optional[Dict[str, Any]]:
    """Load sample data for populating card templates"""
    primary = os.path.join(os.getcwd(), "resources", "sampleData.json")
    fallback = os.path.join(os.getcwd(), "resources", "sampleData-taskAssigned.json")
    for path in (primary, fallback):
        try:
            print(f"[DEBUG] Loading sample data from: {path}")
            if not os.path.exists(path):
                print(f"[DEBUG] Sample data not found at: {path}")
                continue
            with open(path, "r", encoding="utf-8") as f:
                sample_data = json.loads(f.read())
                print(f"[DEBUG] ✅ Sample data loaded successfully from: {path}")
                return sample_data
        except Exception as e:
            print(f"[WARN] Could not load sample data from {path}: {e}")
            continue
    print("[ERROR] No sample data file found (looked for resources/sampleData.json and resources/sampleData-taskAssigned.json)")
    return None


def load_task_status_template() -> Optional[Dict[str, Any]]:
    """Load the pre-meeting task status template taskStatus.json"""
    return load_card_by_name("taskStatus.json")


def load_deadline_template() -> Optional[Dict[str, Any]]:
    """Load the pre-meeting deadline template deadline_template.json"""
    return load_card_by_name("deadline_template.json")
