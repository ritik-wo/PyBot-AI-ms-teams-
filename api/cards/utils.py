from __future__ import annotations

from typing import Any, Optional
import json
import os
import re


def load_card_by_name(card_name: str) -> Optional[dict]:
    """Load an adaptive card template by filename from any subfolder under resources/."""
    import glob
    base_dir = os.path.join(os.getcwd(), "resources")
    pattern = os.path.join(base_dir, "**", card_name)
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        print(f"[ERROR] Card template '{card_name}' not found in resources/.")
        return None
    card_path = matches[0]
    try:
        print(f"[DEBUG] Loading card: {card_path}")
        with open(card_path, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    except Exception as e:
        print(f"[ERROR] Failed to load card '{card_name}': {e}")
        return None


def replace_icon_names(obj: Any, from_name: str, to_name: str) -> Any:
    """Recursively replace Icon name values from from_name to to_name in a card JSON structure."""
    if isinstance(obj, dict):
        if obj.get('type') == 'Icon' and obj.get('name') == from_name:
            obj['name'] = to_name
        for k, v in obj.items():
            obj[k] = replace_icon_names(v, from_name, to_name)
        return obj
    elif isinstance(obj, list):
        return [replace_icon_names(item, from_name, to_name) for item in obj]
    else:
        return obj


def populate_placeholders(template: dict, data: dict) -> dict:
    """Populate {{placeholders}} recursively within a JSON-like structure using provided data."""
    def replace_placeholders(obj):
        if isinstance(obj, dict):
            return {key: replace_placeholders(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [replace_placeholders(item) for item in obj]
        elif isinstance(obj, str):
            def replacer(match):
                placeholder = match.group(1)
                try:
                    # Handle nested properties and array access like tasks[0].title
                    if '[' in placeholder and ']' in placeholder:
                        parts = placeholder.split('.')
                        result = data
                        for part in parts:
                            if '[' in part and ']' in part:
                                array_name = part.split('[')[0]
                                index = int(part.split('[')[1].split(']')[0])
                                result = result[array_name][index]
                            else:
                                result = result[part]
                        return str(result)
                    else:
                        parts = placeholder.split('.')
                        result = data
                        for part in parts:
                            result = result[part]
                        return str(result)
                except (KeyError, IndexError, TypeError):
                    print(f"[WARN] Placeholder not found in data: {placeholder}")
                    return match.group(0)
            return re.sub(r'\{\{([^}]+)\}\}', replacer, obj)
        else:
            return obj

    print(f"[DEBUG] Populating placeholders...")
    populated_card = replace_placeholders(template)

    # Optional normalization
    try:
        populated_card = replace_icon_names(populated_card, from_name='CheckmarkCircle', to_name='Info')
    except Exception as _e:
        print(f"[WARN] Icon normalization skipped due to error: {_e}")

    print(f"[DEBUG] ✅ Placeholders populated successfully")
    return populated_card


def get_icon_for_task_type(task_type: str) -> str:
    """Map task type to an Adaptive Card icon name (robust)."""
    if task_type is None:
        return 'CheckmarkStarburst'
    key = str(task_type).strip().lower()
    mapping = {
        'agreement': 'CheckmarkStarburst',
        'vereinbarung': 'CheckmarkStarburst',
        'decision': 'Diamond',
        'decison': 'Diamond',
        'decisonj': 'Diamond',
        'entscheidung': 'Diamond',
        'issue': 'Info',
        'info': 'Info',
    }
    return mapping.get(key, 'CheckmarkStarburst')
