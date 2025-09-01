from __future__ import annotations

from typing import Optional, List, Any, Dict
import copy
import json

from api.cards.utils import load_card_by_name, populate_placeholders
from api.cards.utils import get_icon_for_task_type


def build_dynamic_card_with_tasks(data: dict) -> Optional[dict]:
    """Build dynamic 'Tasks Assigned To You' card by injecting task sections into base template."""
    # Load base template (header + footer)
    base_template = load_card_by_name("task_assigning_card_template.json")
    if not base_template:
        print("[ERROR] Failed to load base template")
        return None

    # Load full template to extract task section
    full_template = load_card_by_name("TasksAssignedToUser.json")
    if not full_template:
        print("[ERROR] Failed to load full template for task extraction")
        return None

    tasks = data.get("tasks", [])
    task_count = len(tasks)
    print(f"[DEBUG] Detected {task_count} tasks in data")

    # Extract task section template
    task_section_template = extract_task_section_template(full_template)
    if not task_section_template:
        print("[ERROR] Failed to extract task section template (no fallback by design)")
        return None

    # Build dynamic card
    dynamic_card = copy.deepcopy(base_template)

    # Generate task sections and inject them
    if task_count > 0:
        task_sections = generate_task_sections(task_section_template, task_count, tasks)
        inject_task_sections_into_card(dynamic_card, task_sections)

    # Populate all placeholders
    populated_card = populate_placeholders(dynamic_card, data)

    print(f"[DEBUG] ✅ Dynamic card built successfully with {task_count} tasks")
    return populated_card


def extract_task_section_template(full_template: dict) -> Optional[dict]:
    """Extract the complete task section template including table header and task rows."""
    def find_table_structure(items):
        table_elements = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                # Heuristic: treat a ColumnSet as the header if it is followed by a
                # Container that looks like the first task row (has selectAction and
                # task placeholders like tasks[0] or any {{tasks[...}} pattern).
                if item.get("type") == "ColumnSet":
                    # Look for the first task row container after this ColumnSet
                    for j in range(i + 1, len(items)):
                        next_item = items[j]
                        if isinstance(next_item, dict) and next_item.get("type") == "Container" and "selectAction" in next_item:
                            s = str(next_item)
                            if ("tasks[0]" in s) or ("{{tasks[" in s):
                                table_elements.append(item)  # header
                                table_elements.append(next_item)  # first row
                                # Look for the details container after it
                                for k in range(j + 1, len(items)):
                                    details_item = items[k]
                                    if (
                                        isinstance(details_item, dict)
                                        and details_item.get("type") == "Container"
                                        and (
                                            details_item.get("id") == "details1"
                                            or str(details_item.get("id", "")).startswith("details")
                                        )
                                    ):
                                        table_elements.append(details_item)
                                        break
                                break
                # Recurse into nested structures
                if "items" in item:
                    result = find_table_structure(item["items"])
                    if result:
                        return result
                if "body" in item:
                    result = find_table_structure(item["body"])
                    if result:
                        return result
        return None

    body = full_template.get("body", [])
    table_structure = find_table_structure(body)
    if table_structure and len(table_structure) >= 2:
        return {
            "table_header": table_structure[0],
            "task_row_template": table_structure[1],
            "task_details_template": table_structure[2] if len(table_structure) > 2 else None,
        }
    # Detailed diagnostics
    try:
        template_str = json.dumps(full_template) if isinstance(full_template, (dict, list)) else str(full_template)
    except Exception:
        template_str = str(full_template)

    # Counts and quick checks
    def count_occurrences(s: str, needle: str) -> int:
        try:
            return s.count(needle)
        except Exception:
            return 0

    has_tasks_indexed = ("tasks[0]" in template_str) or ("{{tasks[" in template_str)
    count_tasks0 = count_occurrences(template_str, "tasks[0]")
    count_tasks_brace = count_occurrences(template_str, "{{tasks[")

    # Walk a shallow structure to count ColumnSets and Containers with selectAction
    def shallow_scan(items):
        colsets = 0
        containers = 0
        containers_with_select = 0
        if not isinstance(items, list):
            return colsets, containers, containers_with_select
        for it in items:
            if isinstance(it, dict):
                t = it.get("type")
                if t == "ColumnSet":
                    colsets += 1
                if t == "Container":
                    containers += 1
                    if "selectAction" in it:
                        containers_with_select += 1
        return colsets, containers, containers_with_select

    shallow_colsets, shallow_containers, shallow_containers_with_select = shallow_scan(body)

    print("[ERROR] Could not find complete table structure in template (no header+row+details match)")
    print(f"[DIAG] body_items={len(body)} shallow_colsets={shallow_colsets} shallow_containers={shallow_containers} containers_with_select={shallow_containers_with_select}")
    print(f"[DIAG] placeholders_present={has_tasks_indexed} tasks[0]_count={count_tasks0} double_brace_tasks_prefix_count={count_tasks_brace}")
    print("[DIAG] Hint: header is detected as a ColumnSet immediately followed by a Container with selectAction and task placeholders; details id should start with 'details'.")
    return None


def _set_icons_in_subtree(obj: Any, icon_name: str):
    if isinstance(obj, dict):
        if obj.get("type") == "Icon" and "name" in obj and obj["name"] in [
            "CheckmarkStarburst",
            "Diamond",
            "Info",
        ]:
            obj["name"] = icon_name
        for _, v in obj.items():
            _set_icons_in_subtree(v, icon_name)
    elif isinstance(obj, list):
        for item in obj:
            _set_icons_in_subtree(item, icon_name)


def _fix_row_toggle_action(row_container: dict, details_id: str):
    """Ensure the row's selectAction toggles only its own details container."""
    def visit(obj):
        if isinstance(obj, dict):
            if "selectAction" in obj and isinstance(obj["selectAction"], dict):
                sa = obj["selectAction"]
                if sa.get("type") == "Action.ToggleVisibility":
                    sa["targetElements"] = [{"elementId": details_id}]
            for _, v in obj.items():
                visit(v)
        elif isinstance(obj, list):
            for v in obj:
                visit(v)
    visit(row_container)


def generate_task_sections(task_template: dict, task_count: int, tasks: list) -> list:
    """Generate table header + N task rows based on template structure and set icons per task."""
    if not task_template or not isinstance(task_template, dict):
        print("[ERROR] Invalid task template provided")
        return []

    table_sections = []

    # Add the table header first (only once)
    if "table_header" in task_template:
        table_sections.append(copy.deepcopy(task_template["table_header"]))

    task_row_template = task_template.get("task_row_template")
    task_details_template = task_template.get("task_details_template")
    if not task_row_template:
        print("[ERROR] No task row template found")
        return table_sections

    for i in range(task_count):
        # Row
        task_row = copy.deepcopy(task_row_template)
        row_str = json.dumps(task_row)
        row_str = row_str.replace("tasks[0]", f"tasks[{i}]")
        row_str = row_str.replace("details1", f"details{i+1}")
        try:
            updated_row = json.loads(row_str)
            try:
                icon_name = get_icon_for_task_type(tasks[i].get("type"))
                _set_icons_in_subtree(updated_row, icon_name)
            except Exception:
                pass
            try:
                _fix_row_toggle_action(updated_row, details_id=f"details{i+1}")
            except Exception:
                pass
            table_sections.append(updated_row)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse updated task row: {e}")
            continue

        # Details
        if task_details_template:
            task_details = copy.deepcopy(task_details_template)
            details_str = json.dumps(task_details)
            details_str = details_str.replace("tasks[0]", f"tasks[{i}]")
            details_str = details_str.replace("details1", f"details{i+1}")
            try:
                updated_details = json.loads(details_str)
                try:
                    icon_name = get_icon_for_task_type(tasks[i].get("type"))
                    _set_icons_in_subtree(updated_details, icon_name)
                except Exception:
                    pass
                table_sections.append(updated_details)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse updated task details: {e}")
                continue

    print(
        f"[DEBUG] ✅ Generated table with {len(table_sections)} elements (1 header + {task_count} task rows + details)"
    )
    return table_sections


def inject_task_sections_into_card(card: dict, task_sections: list):
    """Inject task sections into card body before the footer."""
    body = card.get("body", [])
    insertion_index = len(body) - 1  # Default to before last item

    for i, item in enumerate(body):
        if isinstance(item, dict) and item.get("type") == "Container":
            items = item.get("items", [])
            for sub_item in items:
                if isinstance(sub_item, dict) and sub_item.get("type") == "ActionSet":
                    insertion_index = i
                    break

    for i, task_section in enumerate(task_sections):
        body.insert(insertion_index + i, task_section)

    return card
