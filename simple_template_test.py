#!/usr/bin/env python3
"""
Simple standalone test for templating functionality
"""
import json
import re
import os

def load_json_file(file_path):
    """Load JSON file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def populate_template(template, data):
    """Populate template with data"""
    def replace_placeholders(obj):
        if isinstance(obj, dict):
            return {key: replace_placeholders(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [replace_placeholders(item) for item in obj]
        elif isinstance(obj, str):
            def replacer(match):
                placeholder = match.group(1)
                try:
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
                    print(f"Placeholder not found: {placeholder}")
                    return match.group(0)
            return re.sub(r'\{\{([^}]+)\}\}', replacer, obj)
        else:
            return obj
    
    return replace_placeholders(template)

def main():
    print("=== Testing Adaptive Card Templating ===")
    
    # Load template
    template_path = os.path.join("resources", "post-meeting-cards", "TasksAssignedToUser.json")
    template = load_json_file(template_path)
    if not template:
        print("❌ Failed to load template")
        return
    print("✅ Template loaded")
    
    # Load sample data
    data_path = os.path.join("resources", "sampleData.json")
    sample_data = load_json_file(data_path)
    if not sample_data:
        print("❌ Failed to load sample data")
        return
    print("✅ Sample data loaded")
    
    # Test templating
    try:
        populated_card = populate_template(template, sample_data)
        print("✅ Template populated successfully")
        
        # Check for remaining placeholders
        card_json = json.dumps(populated_card)
        remaining_placeholders = len(re.findall(r'\{\{([^}]+)\}\}', card_json))
        
        if remaining_placeholders > 0:
            print(f"⚠️ {remaining_placeholders} placeholders remain")
        else:
            print("✅ All placeholders replaced")
        
        # Save result
        with open("test_populated_card.json", "w", encoding="utf-8") as f:
            json.dump(populated_card, f, indent=2, ensure_ascii=False)
        print("✅ Result saved to test_populated_card.json")
        
    except Exception as e:
        print(f"❌ Templating failed: {e}")

if __name__ == "__main__":
    main()
