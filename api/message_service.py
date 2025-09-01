from aiohttp.web import json_response
import json
import os
import requests
from api.graph_api import (
    get_fresh_graph_access_token, 
    find_user_by_email, 
    get_or_create_chat_with_user, 
    send_card_message_to_chat
)
from api.bot_framework_api import send_message_via_bot_framework
from typing import List, Optional, Tuple, Any
from api.cards.upcoming_deadline import (
    load_upcoming_deadline_template as _ud_load_template,
    build_upcoming_deadline_card as _ud_build_card,
)
from api.cards.tasks_assigned import (
    build_dynamic_card_with_tasks as _ta_build_card,
    extract_task_section_template as _ta_extract_section,
    generate_task_sections as _ta_generate_sections,
    inject_task_sections_into_card as _ta_inject_sections,
)
from api.cards.utils import (
    populate_placeholders as _cards_populate_placeholders,
)

def load_tasks_assigned_card():
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

def load_card_by_name(card_name: str) -> Optional[dict]:
    """Load an adaptive card template by name from any subfolder in resources/"""
    import glob
    import os
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

def load_updated_tasks_card(default_name: str = "TasksAssignedToUserUpdated.json") -> Optional[dict]:
    """Convenience loader for the updated TasksAssigned card template."""
    return load_card_by_name(default_name)

def load_sample_data() -> Optional[dict]:
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

def build_dynamic_card_with_tasks(data: dict) -> dict:
    """Thin wrapper delegating to api.cards.tasks_assigned.build_dynamic_card_with_tasks"""
    return _ta_build_card(data)

def extract_task_section_template(full_template: dict) -> dict:
    """Thin wrapper delegating to api.cards.tasks_assigned.extract_task_section_template"""
    return _ta_extract_section(full_template)

def generate_task_sections(task_template: dict, task_count: int, tasks: list) -> list:
    """Thin wrapper delegating to api.cards.tasks_assigned.generate_task_sections"""
    return _ta_generate_sections(task_template, task_count, tasks)

def inject_task_sections_into_card(card: dict, task_sections: list):
    """Thin wrapper delegating to api.cards.tasks_assigned.inject_task_sections_into_card"""
    return _ta_inject_sections(card, task_sections)

def populate_placeholders(template: dict, data: dict) -> dict:
    """Thin wrapper delegating to api.cards.utils.populate_placeholders"""
    return _cards_populate_placeholders(template, data)

def get_icon_for_task_type(task_type: str) -> str:
    """Map task type to an Adaptive Card icon name.
    - Case-insensitive, trims whitespace
    - Handles common typos/synonyms
    """
    if task_type is None:
        return 'CheckmarkStarburst'
    key = str(task_type).strip().lower()
    # Common variants
    mapping = {
        'agreement': 'CheckmarkStarburst',
        'vereinbarung': 'CheckmarkStarburst',  # de
        'decision': 'Diamond',
        'decison': 'Diamond',  # typo
        'decisonj': 'Diamond',  # reported typo
        'entscheidung': 'Diamond',  # de
        'issue': 'Info',
        'info': 'Info',
    }
    return mapping.get(key, 'CheckmarkStarburst')

def _set_icons_in_subtree(obj, icon_name: str):
    """Update Icon elements within a given subtree."""
    if isinstance(obj, dict):
        if obj.get('type') == 'Icon' and 'name' in obj and obj['name'] in ['CheckmarkStarburst', 'Diamond', 'Info']:
            old = obj['name']
            obj['name'] = icon_name
            print(f"[DEBUG]   Icon updated: {old} -> {icon_name}")
        for _, v in obj.items():
            _set_icons_in_subtree(v, icon_name)
    elif isinstance(obj, list):
        for item in obj:
            _set_icons_in_subtree(item, icon_name)

def _fix_row_toggle_action(row_container: dict, details_id: str):
    """Ensure the row's selectAction toggles only its own details container.
    Rewrites any Action.ToggleVisibility targetElements to only target details_id.
    """
    def visit(obj):
        if isinstance(obj, dict):
            # If this dict is a container with selectAction, normalize it
            if 'selectAction' in obj and isinstance(obj['selectAction'], dict):
                sa = obj['selectAction']
                if sa.get('type') == 'Action.ToggleVisibility':
                    # Use single target so it toggles only its own details
                    sa['targetElements'] = [ { 'elementId': details_id } ]
            # Recurse
            for _, v in obj.items():
                visit(v)
        elif isinstance(obj, list):
            for v in obj:
                visit(v)
    visit(row_container)

def replace_icon_names(obj, from_name: str, to_name: str):
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

def populate_card_template(template: dict, data: dict) -> dict:
    """Legacy function - kept for backward compatibility"""
    return populate_placeholders(template, data)

# ===== DEADLINE CARD (pre-meeting sample-exm.json) UTILITIES =====
def load_task_status_template() -> Optional[dict]:
    """Load the pre-meeting task status template taskStatus.json"""
    return load_card_by_name("taskStatus.json")

def build_task_status_card(data: dict) -> Optional[dict]:
    """Build the task status card using taskStatus.json and placeholder population.
    This ensures the first column (Progress item) binds to tasks[i].title exactly as the template defines.
    """
    template = load_task_status_template()
    if not template:
        print("[ERROR] taskStatus.json template not found")
        return None
    try:
        return populate_placeholders(template, data)
    except Exception as e:
        print(f"[ERROR] Failed to populate taskStatus template: {e}")
        return None
def load_deadline_template() -> Optional[dict]:
    """Load the pre-meeting deadline template sample-exm.json"""
    return load_card_by_name("sample-exm.json")

# ===== UPCOMING DEADLINE (dynamic rows) =====
def load_upcoming_deadline_template() -> Optional[dict]:
    """Thin wrapper delegating to api.cards.upcoming_deadline.load_upcoming_deadline_template"""
    return _ud_load_template()

def _build_task_row_from_reference(task: dict, details_id: str) -> dict:
    """Delegates to api.cards.upcoming_deadline._build_task_row_from_reference"""
    from api.cards.upcoming_deadline import _build_task_row_from_reference as _impl
    return _impl(task, details_id)

def _build_task_details_from_reference(task: dict, details_id: str) -> dict:
    """Delegates to api.cards.upcoming_deadline._build_task_details_from_reference"""
    from api.cards.upcoming_deadline import _build_task_details_from_reference as _impl
    return _impl(task, details_id)

def build_upcoming_deadline_card(data: dict) -> Optional[dict]:
    """Thin wrapper delegating to api.cards.upcoming_deadline.build_upcoming_deadline_card"""
    return _ud_build_card(data)

def _find_first_task_row_and_details(card: dict):
    """Locate the first task row Container and its details Container (id=details1) in sample-exm.json.
    Returns (row_template, details_template, insertion_parent_index, insertion_index_start)
    where insertion indices refer to the parent 'items' list that contains the table header and subsequent rows.
    """
    body = card.get('body', [])
    # Card structure: body[0]=header, body[1]=meeting title, body[2]=table+rows containers...
    # We need to find the container that holds the table header ColumnSet and after it, the first row container.
    table_container = None
    for item in body:
        if isinstance(item, dict) and item.get('type') == 'Container':
            items = item.get('items', [])
            for sub in items:
                if isinstance(sub, dict) and sub.get('type') == 'ColumnSet':
                    # Header row has text: Progress item, Type, Due date
                    if 'Progress item' in str(sub) and 'Due date' in str(sub):
                        table_container = item
                        break
            if table_container:
                break

    if not table_container:
        return None, None, None, None

    items = table_container.get('items', [])
    # The header ColumnSet is at items[0], first task row Container is items[1], then details1 is items[2]
    row_template = None
    details_template = None
    insertion_index_start = 1  # after header
    for i in range(1, len(items)):
        it = items[i]
        if isinstance(it, dict) and it.get('type') == 'Container' and it.get('selectAction'):
            row_template = it
            # Next visible details container 'id': 'details1'
            if i + 1 < len(items):
                maybe_details = items[i+1]
                if isinstance(maybe_details, dict) and maybe_details.get('type') == 'Container' and maybe_details.get('id', '').startswith('details'):
                    details_template = maybe_details
            break

    if not row_template or not details_template:
        return None, None, None, None

    return row_template, details_template, body.index(table_container), insertion_index_start

def _set_text_in_obj(obj: dict, predicate, value: str):
    """Find first TextBlock matching predicate and set its text"""
    found = False
    def visit(o):
        nonlocal found
        if found:
            return
        if isinstance(o, dict):
            if o.get('type') == 'TextBlock' and predicate(o):
                o['text'] = value
                found = True
            else:
                for _, v in o.items():
                    visit(v)
        elif isinstance(o, list):
            for v in o:
                visit(v)
    visit(obj)
    return found

def _set_toggle_in_subtree(obj, value: bool):
    """Set 'value' on any Input.Toggle elements within the given subtree.
    This aligns with the behavior defined in resources/pre-meeting-cards/taskStatus.json.
    """
    if isinstance(obj, dict):
        if obj.get('type') == 'Input.Toggle':
            # Adaptive Cards Input.Toggle uses boolean or string "true"/"false"
            obj['value'] = True if value else False
        for _, v in obj.items():
            _set_toggle_in_subtree(v, value)
    elif isinstance(obj, list):
        for item in obj:
            _set_toggle_in_subtree(item, value)

def _is_task_completed(task: dict) -> bool:
    """Infer completion from task fields.
    Supports either a boolean 'completed'/'isDone' or a string 'status' with values like 'done', 'completed', 'closed'.
    """
    if not isinstance(task, dict):
        return False
    if isinstance(task.get('completed'), bool):
        return task['completed']
    if isinstance(task.get('isDone'), bool):
        return task['isDone']
    status = str(task.get('status', '')).strip().lower()
    return status in {'done', 'completed', 'closed', 'resolved'}

def _set_progress_item_in_row(row: dict, value: str) -> bool:
    """Set the first column's TextBlock (the 'Progress item' column) in a task row.
    We locate the top-level ColumnSet inside the row Container and update the first
    Column's first TextBlock, avoiding accidental matches in other columns.
    """
    try:
        if not isinstance(row, dict):
            return False
        # Row container typically has one top-level ColumnSet in its items
        for item in row.get('items', []) or []:
            if isinstance(item, dict) and item.get('type') == 'ColumnSet':
                cols = item.get('columns', []) or []
                if not cols:
                    continue
                first_col = cols[0]
                # Update ALL TextBlocks in the first column to be safe (template may have sample date)
                updated_any = False
                stack = [first_col]
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        if node.get('type') == 'TextBlock':
                            node['text'] = str(value)
                            updated_any = True
                        for k in ('items', 'columns'):
                            if k in node and isinstance(node[k], list):
                                stack.extend(reversed(node[k]))
                if updated_any:
                    return True
                # If no TextBlock found in first column, keep searching next items
        return False
    except Exception:
        return False
def _set_text_by_label_section(container: dict, label_text: str, value: str) -> bool:
    """In a details container, find a ColumnSet section whose left label TextBlock equals
    label_text (e.g., 'Meeting origin', 'Meeting date', 'Agenda item', 'Relation'), then set
    the primary TextBlock on the right side to value. Returns True if set.

    Relies on template labels remaining constant, but not on any example data values.
    """
    try:
        items = container.get('items', [])
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get('type') != 'ColumnSet':
                continue
            cols = item.get('columns', [])
            if len(cols) < 2:
                continue
            # Left label column
            left = cols[0]
            left_lbls = [it for it in left.get('items', []) if isinstance(it, dict) and it.get('type') == 'TextBlock']
            if any(tb.get('text') == label_text for tb in left_lbls):
                # Right content column (may be nested ColumnSet)
                right = cols[1]
                # Prefer deepest TextBlock with wrap or Small size
                stack = [right]
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        if node.get('type') == 'TextBlock':
                            node['text'] = str(value)
                            return True
                        for k in ('items', 'columns'):
                            if k in node and isinstance(node[k], list):
                                stack.extend(reversed(node[k]))
        return False
    except Exception:
        return False

def _set_due_date_in_row(row: dict, value: str) -> bool:
    """Find the due date TextBlock in a row by locating the ColumnSet that also contains an
    Input.Toggle (the due date + toggle + info icon cluster) and set its TextBlock text.
    Avoids matching any static example value.
    """
    try:
        # Walk all ColumnSets; look for one having an Input.Toggle somewhere
        stack = [row]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            if node.get('type') == 'ColumnSet':
                # detect which column contains a toggle (directly or in nested ColumnSet)
                columns = node.get('columns', []) or []
                toggle_col_index = None
                def _col_has_toggle(col: dict) -> bool:
                    for it in col.get('items', []) or []:
                        if isinstance(it, dict):
                            if it.get('type') == 'Input.Toggle':
                                return True
                            if it.get('type') == 'ColumnSet':
                                # look into nested ColumnSet columns as well
                                for subcol in it.get('columns', []) or []:
                                    if _col_has_toggle(subcol):
                                        return True
                    return False
                for idx, col in enumerate(columns):
                    if isinstance(col, dict) and _col_has_toggle(col):
                        toggle_col_index = idx
                        break

                if toggle_col_index is not None:
                    # Heuristic: due date TextBlock sits in the column immediately left of the toggle column
                    target_index = toggle_col_index - 1 if toggle_col_index > 0 else toggle_col_index
                    if 0 <= target_index < len(columns):
                        target_col = columns[target_index]
                        # set the first TextBlock in target column (search depth-first)
                        stack2 = [target_col]
                        while stack2:
                            node2 = stack2.pop()
                            if isinstance(node2, dict):
                                if node2.get('type') == 'TextBlock':
                                    node2['text'] = str(value)
                                    return True
                                for k in ('items', 'columns'):
                                    if k in node2 and isinstance(node2[k], list):
                                        stack2.extend(reversed(node2[k]))
                        # fallback: set any TextBlock within the ColumnSet that is likely the due date
                        for col in columns:
                            for it in col.get('items', []) or []:
                                if isinstance(it, dict) and it.get('type') == 'TextBlock' and it.get('size') == 'Small':
                                    it['text'] = str(value)
                                    return True
            # continue walking
            for k in ('items', 'columns'):
                if k in node and isinstance(node[k], list):
                    stack.extend(reversed(node[k]))
        return False
    except Exception:
        return False
    if isinstance(task.get('completed'), bool):
        return task['completed']
    if isinstance(task.get('isDone'), bool):
        return task['isDone']
    status = str(task.get('status', '')).strip().lower()
    return status in {'done', 'completed', 'closed', 'resolved'}

def build_deadline_card_from_sample_exm(data: dict) -> Optional[dict]:
    """Builds a deadline card exactly like sample-exm.json but populated from provided data.
    Expected data shape: { dueDate: string, meeting: { type: string }, tasks: [ {title,type,dueDate,detailsTitle,meetingOrigin,meetingDate,agendaItem,relation} ] }
    Supports N tasks (>=1).
    """
    import copy, json as _json
    template = load_deadline_template()
    if not template:
        print("[ERROR] Deadline template not found")
        return None

    card = copy.deepcopy(template)

    # Populate badge text and meeting title
    try:
        badge_text = str(data.get('dueDate', ''))
        meeting_title = str(data.get('meeting', {}).get('type', ''))

        # Badge lives under first ColumnSet -> second Column -> Badge.text
        def set_badge(o):
            if isinstance(o, dict):
                if o.get('type') == 'Badge' and 'text' in o:
                    o['text'] = badge_text
                for v in o.values():
                    set_badge(v)
            elif isinstance(o, list):
                for v in o:
                    set_badge(v)
        set_badge(card)

        # Meeting title TextBlock directly after header container
        _set_text_in_obj(card, lambda tb: tb.get('text') == 'Strategie 2030', meeting_title or ' ')
    except Exception as e:
        print(f"[WARN] Failed to set header fields: {e}")

    # Extract row/details templates
    row_tmpl, details_tmpl, parent_idx, insert_start = _find_first_task_row_and_details(card)
    if row_tmpl is None or details_tmpl is None:
        print("[ERROR] Could not locate row/details templates in sample-exm.json")
        return None

    tasks = data.get('tasks', []) or []
    if len(tasks) == 0:
        print("[WARN] No tasks provided; card will contain header only")
    
    # Build rows and details for each task
    parent_container = card['body'][parent_idx]
    items = parent_container['items']
    # Detect optional footer (container containing an ActionSet) to preserve and re-append later
    footer_tail = []
    try:
        for j in range(len(items) - 1, -1, -1):
            it = items[j]
            if isinstance(it, dict) and it.get('type') == 'Container':
                sub_items = it.get('items', [])
                if any(isinstance(s, dict) and s.get('type') == 'ActionSet' for s in sub_items):
                    footer_tail = items[j:]
                    break
    except Exception:
        footer_tail = []

    # Keep the header (items[0]); we'll remove existing rows/details and then inject new
    parent_container['items'] = [items[0]]

    for idx, t in enumerate(tasks, start=1):
        # Row
        row = copy.deepcopy(row_tmpl)
        # Fix selectAction to target only this details id
        details_id = f"details{idx}"
        try:
            if 'selectAction' in row and isinstance(row['selectAction'], dict):
                row['selectAction']['targetElements'] = [{ 'elementId': details_id, 'isVisible': True }]
        except Exception:
            pass

        # Set row fields: title, type, due date, and icon by type
        try:
            # Progress item (first column) — map to task title by default
            _set_progress_item_in_row(row, str(t.get('title', '')))
            # type text (the small wrapped text next to the icon)
            _set_text_in_obj(row, lambda tb: tb.get('wrap') is True and tb.get('size') == 'Small', str(t.get('type', '')))
            # due date (TextBlock in the cluster with Input.Toggle)
            if not _set_due_date_in_row(row, str(t.get('dueDate', ''))):
                # fallback: set any small TextBlock that is not the title
                _set_text_in_obj(row, lambda tb: tb.get('size') == 'Small' and tb.get('maxLines') is None, str(t.get('dueDate', '')))
            # icon
            icon_name = get_icon_for_task_type(str(t.get('type', '')))
            _set_icons_in_subtree(row, icon_name)
            # toggle (completion status) — incorporate taskStatus.json behavior
            _set_toggle_in_subtree(row, _is_task_completed(t))
        except Exception as e:
            print(f"[WARN] Failed to populate row {idx}: {e}")

        parent_container['items'].append(row)

        # Details
        details = copy.deepcopy(details_tmpl)
        try:
            details['id'] = details_id
        except Exception:
            pass
        try:
            # detailsTitle
            _set_text_in_obj(details, lambda tb: tb.get('size') == 'Medium' and tb.get('weight') == 'Bolder', str(t.get('detailsTitle', '')))
            # meetingOrigin by label section
            _set_text_by_label_section(details, 'Meeting origin', str(t.get('meetingOrigin', '')))
            # meetingDate by label section
            _set_text_by_label_section(details, 'Meeting date', str(t.get('meetingDate', '')))
            # agendaItem by label section
            _set_text_by_label_section(details, 'Agenda item', str(t.get('agendaItem', '')))
            # relation by label section
            _set_text_by_label_section(details, 'Relation', str(t.get('relation', '')))
            # icons within details
            _set_icons_in_subtree(details, get_icon_for_task_type(str(t.get('type', ''))))
            # propagate toggle state to any toggles in details if present
            _set_toggle_in_subtree(details, _is_task_completed(t))
        except Exception as e:
            print(f"[WARN] Failed to populate details {idx}: {e}")

        parent_container['items'].append(details)

    # Re-append preserved footer (if any)
    if footer_tail:
        parent_container['items'].extend(footer_tail)

    # Enforce single-details visibility behavior: each row's tap shows only its own details
    try:
        # Collect all detail ids we created
        detail_ids = [f"details{idx}" for idx in range(1, len(tasks) + 1)]
        # Walk through items to find row containers in order
        row_idx = 0
        for it in parent_container['items']:
            if isinstance(it, dict) and it.get('type') == 'Container' and it.get('selectAction'):
                row_idx += 1
                my_details = f"details{row_idx}"
                targets = [{ 'elementId': my_details, 'isVisible': True }]
                for did in detail_ids:
                    if did != my_details:
                        targets.append({ 'elementId': did, 'isVisible': False })
                try:
                    it['selectAction']['targetElements'] = targets
                except Exception:
                    pass
        # Add card-level selectAction to close all details when clicking outside rows
        try:
            card['selectAction'] = {
                'type': 'Action.ToggleVisibility',
                'targetElements': [ { 'elementId': did, 'isVisible': False } for did in detail_ids ]
            }
        except Exception:
            pass
    except Exception as e:
        print(f"[WARN] Failed to enforce single-details visibility: {e}")

    return card

async def send_message_to_user_service(email, message, adapter, app_id, card_name=None, conversation_reference: Optional[dict] = None, card_data: Optional[dict] = None):
    """Main service function to send messages to users using hybrid approach"""
    try:
        print(f"[DEBUG] ===== STARTING MESSAGE SERVICE =====")
        print(f"[DEBUG] Target email: {email}")
        print(f"[DEBUG] Message content: {message}")
        print(f"[DEBUG] App ID: {app_id}")
        print(f"[DEBUG] Card name: {card_name}")
        
        # Choose data source: prefer caller-provided card_data, fallback to sample data
        if card_data and isinstance(card_data, dict):
            data_source = card_data
            print(f"[DEBUG] ✅ Using card data from request payload")
        else:
            data_source = load_sample_data()
            if not data_source:
                return json_response({"error": "No input data supplied and sampleData.json not found."}, status=404)
            print("[DEBUG] ✅ Loaded sample data (fallback)")
        
        # Build dynamic card with task injection
        adaptive_card = build_dynamic_card_with_tasks(data_source)
        if not adaptive_card:
            return json_response({"error": "Failed to build dynamic card with tasks"}, status=500)
        print(f"[DEBUG] ✅ Dynamic card built with task injection")
        
        # Get fresh access token to find user
        print(f"[DEBUG] Getting fresh Graph API access token...")
        access_token = get_fresh_graph_access_token()
        print(f"[DEBUG] ✅ Access token obtained successfully")
        
        # Find the user by email
        print(f"[DEBUG] Looking up user by email...")
        user = find_user_by_email(email, access_token)
        if not user:
            print(f"[ERROR] ❌ User not found: {email}")
            return json_response({"error": f"User with email {email} not found"}, status=404)
        
        print(f"[DEBUG] ✅ User found: {user.get('displayName', email)} with ID: {user['id']}")
        
        # Try Bot Framework approach first (for users who have interacted with bot)
        try:
            from bots.teams_conversation_bot import CONVERSATION_REFERENCE
            
            if CONVERSATION_REFERENCE:
                print(f"[DEBUG] 🔄 Trying Bot Framework approach first...")
                
                # Use Bot Framework's proactive messaging with the adaptive card
                result = await send_message_via_bot_framework_with_card(
                    user, adaptive_card, adapter, CONVERSATION_REFERENCE, app_id
                )
                
                print(f"[DEBUG] ✅ Bot Framework approach successful")
                return json_response(result)
            else:
                print(f"[DEBUG] ⚠️ No conversation reference available, trying Graph API")
                raise Exception("No conversation reference")
                
        except Exception as bot_error:
            print(f"[DEBUG] ❌ Bot Framework approach failed: {bot_error}")
            print(f"[DEBUG] 🔄 Falling back to Graph API approach...")
            
            # Fallback to Graph API approach
            try:
                print(f"[DEBUG] Creating or finding chat with user...")
                # Create or find existing chat with the user using Graph API
                chat_id = get_or_create_chat_with_user(user["id"], access_token)
                if not chat_id:
                    print(f"[ERROR] ❌ Could not find or create chat for user {email}")
                    return json_response({"error": f"Could not find or create chat for user {email}"}, status=500)
                
                print(f"[DEBUG] ✅ Chat ID obtained: {chat_id}")
                
                print(f"[DEBUG] Sending TasksAssignedToUser adaptive card...")
                # Send the adaptive card using Graph API
                message_data = send_adaptive_card_to_chat(chat_id, adaptive_card, access_token)
                print(f"[DEBUG] ✅ Successfully sent TasksAssignedToUser card to {email}")
                
                return json_response({
                    "status": f"TasksAssignedToUser card sent to {email}", 
                    "method": "graph_api",
                    "chat_id": chat_id,
                    "user_id": user["id"],
                    "message_id": message_data.get('id') if isinstance(message_data, dict) else None
                })
                
            except Exception as graph_error:
                print(f"[ERROR] ❌ Graph API chat approach failed: {graph_error}")
                print(f"[DEBUG] ===== FINAL ERROR SUMMARY =====")
                print(f"[DEBUG] Bot Framework error: {bot_error}")
                print(f"[DEBUG] Graph API error: {graph_error}")
                return json_response({
                    "error": f"Both Bot Framework and Graph API approaches failed. User may need to interact with the bot first.",
                    "bot_error": str(bot_error),
                    "graph_error": str(graph_error),
                    "recommendation": "Have the user send a message to the bot in Teams first, or ensure the bot is properly installed in Teams"
                }, status=500)
        
    except Exception as e:
        print(f"[ERROR] ❌ CRITICAL ERROR in send_message_to_user_service")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return json_response({"error": str(e)}, status=500)

async def send_deadline_to_user_service(email: str, adapter, app_id: str, data_source: dict):
    """Builds the deadline card (sample-exm.json style) from provided data and sends it to the given email.
    Tries Bot Framework proactive messaging first; falls back to Graph API chat.
    """
    try:
        print("[DEBUG] ===== STARTING DEADLINE MESSAGE SERVICE =====")
        print(f"[DEBUG] Target email: {email}")
        # Build the card
        adaptive_card = build_deadline_card_from_sample_exm(data_source)
        if not adaptive_card:
            return json_response({"error": "Failed to build deadline card from template"}, status=500)

        # Graph fundamentals
        print(f"[DEBUG] Getting fresh Graph API access token...")
        access_token = get_fresh_graph_access_token()
        print(f"[DEBUG] ✅ Access token obtained successfully")

        print(f"[DEBUG] Looking up user by email...")
        user = find_user_by_email(email, access_token)
        if not user:
            return json_response({"error": f"User with email {email} not found"}, status=404)

        # Try Bot Framework first if we have a conversation reference
        try:
            from bots.teams_conversation_bot import CONVERSATION_REFERENCE
            if CONVERSATION_REFERENCE:
                print(f"[DEBUG] 🔄 Trying Bot Framework approach for deadline card...")
                result = await send_message_via_bot_framework_with_card(
                    user, adaptive_card, adapter, CONVERSATION_REFERENCE, app_id
                )
                print(f"[DEBUG] ✅ Bot Framework approach successful")
                return json_response(result)
            else:
                print(f"[DEBUG] ⚠️ No conversation reference available, trying Graph API")
                raise Exception("No conversation reference")
        except Exception as bot_error:
            print(f"[DEBUG] ❌ Bot Framework approach failed: {bot_error}")
            print(f"[DEBUG] 🔄 Falling back to Graph API approach...")
            try:
                chat_id = get_or_create_chat_with_user(user["id"], access_token)
                if not chat_id:
                    return json_response({"error": f"Could not find or create chat for user {email}"}, status=500)
                message_data = send_adaptive_card_to_chat(chat_id, adaptive_card, access_token)
                return json_response({
                    "status": f"Deadline card sent to {email}",
                    "method": "graph_api",
                    "chat_id": chat_id,
                    "user_id": user["id"],
                    "message_id": message_data.get('id') if isinstance(message_data, dict) else None
                })
            except Exception as graph_error:
                return json_response({
                    "error": "Both Bot Framework and Graph API approaches failed.",
                    "bot_error": str(bot_error),
                    "graph_error": str(graph_error)
                }, status=500)
    except Exception as e:
        print(f"[ERROR] ❌ CRITICAL ERROR in send_deadline_to_user_service: {e}")
        import traceback
        print(traceback.format_exc())
        return json_response({"error": str(e)}, status=500)

async def send_message_via_bot_framework_with_card(user, adaptive_card, adapter, conversation_reference, app_id):
    """Send the TasksAssignedToUser adaptive card using Bot Framework proactive messaging"""
    print(f"[DEBUG] ===== BOT FRAMEWORK CARD SENDING =====")
    print(f"[DEBUG] Creating conversation with user: {user.get('displayName', user.get('mail', 'Unknown'))}")
    
    from botbuilder.schema import ConversationParameters, ChannelAccount
    from botbuilder.core import MessageFactory, CardFactory
    
    # Log the adaptive card being sent
    print(f"[DEBUG] Adaptive card type: {type(adaptive_card)}")
    print(f"[DEBUG] Adaptive card keys: {list(adaptive_card.keys()) if isinstance(adaptive_card, dict) else 'Not a dict'}")
    print(f"[DEBUG] Card version: {adaptive_card.get('version', 'unknown')}")
    print(f"[DEBUG] Card body items: {len(adaptive_card.get('body', []))}")
    
    # Validate the card structure
    try:
        # Try to serialize and deserialize to check for JSON issues
        card_json = json.dumps(adaptive_card)
        print(f"[DEBUG] ✅ Card serializes to JSON successfully")
        print(f"[DEBUG] JSON length: {len(card_json)} characters")
        
        # Check for problematic characters
        problematic_chars = []
        for i, char in enumerate(card_json):
            if ord(char) > 127:  # Non-ASCII characters
                problematic_chars.append(f"Position {i}: '{char}' (U+{ord(char):04X})")
                if len(problematic_chars) >= 10:  # Limit to first 10
                    break
        
        if problematic_chars:
            print(f"[DEBUG] ⚠️ Found non-ASCII characters:")
            for char_info in problematic_chars:
                print(f"[DEBUG]   - {char_info}")
        else:
            print(f"[DEBUG] ✅ No problematic characters found")
            
    except Exception as e:
        print(f"[ERROR] ❌ Card JSON serialization failed: {e}")
        raise
    
    # Create a channel account for the target user
    target_user = ChannelAccount(
        id=user['id'],
        name=user.get('displayName', user.get('mail', 'Unknown'))
    )
    
    # Create conversation parameters
    conversation_parameters = ConversationParameters(
        is_group=False,
        bot=conversation_reference.bot,
        members=[target_user],
        tenant_id=conversation_reference.conversation.tenant_id,
    )
    
    # Send the adaptive card
    sent_activity_id = None
    conversation_id = None
    serialized_conversation_reference = None
    async def send_message(turn_context):
        try:
            print(f"[DEBUG] Creating adaptive card attachment...")
            attachment = CardFactory.adaptive_card(adaptive_card)
            print(f"[DEBUG] ✅ Adaptive card attachment created successfully")
            print(f"[DEBUG] Attachment content type: {attachment.content_type}")
            print(f"[DEBUG] Attachment content length: {len(str(attachment.content)) if attachment.content else 0}")
            
            print(f"[DEBUG] Creating message with attachment...")
            message = MessageFactory.attachment(attachment)
            print(f"[DEBUG] ✅ Message created successfully")
            
            print(f"[DEBUG] Sending message to Teams...")
            rr = await turn_context.send_activity(message)
            nonlocal sent_activity_id, conversation_id, serialized_conversation_reference
            sent_activity_id = getattr(rr, 'id', None)
            conversation_id = turn_context.activity.conversation.id if turn_context and turn_context.activity and turn_context.activity.conversation else None
            # capture the exact conversation reference for future updates
            from botbuilder.core import TurnContext as _TC
            serialized_conversation_reference = _TC.get_conversation_reference(turn_context.activity).serialize()
            # Note: Do NOT override conversation_reference.activityId here. The reliable id to update is ResourceResponse.id (sent_activity_id), which we return separately.
            print(f"[DEBUG] ✅ Successfully sent TasksAssignedToUser card to {user.get('mail', 'Unknown')}")
            print(f"[DEBUG] ResourceResponse id (activity_id): {sent_activity_id}")
        
        except Exception as e:
            print(f"[ERROR] ❌ Failed to send adaptive card: {e}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")
            raise
    
    await adapter.create_conversation(
        conversation_reference,
        send_message,
        conversation_parameters
    )
    
    return {
        "status": f"TasksAssignedToUser card sent to {user.get('mail', 'Unknown')}", 
        "method": "bot_framework",
        "user_id": user["id"],
        "activity_id": sent_activity_id,
        "conversation_id": conversation_id,
        "conversation_reference": serialized_conversation_reference
    }

def send_adaptive_card_to_chat(chat_id, adaptive_card, access_token):
    """Send the TasksAssignedToUser adaptive card to a chat using Graph API"""
    import urllib.parse
    # URL encode the chat_id since it contains special characters
    encoded_chat_id = urllib.parse.quote(chat_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/chats/{encoded_chat_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    data = {
        "body": {
            "contentType": "html",
            "content": "<div>New Progress items assigned to you</div>"
        },
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": adaptive_card
            }
        ]
    }
    
    print(f"[DEBUG] ===== ADAPTIVE CARD SENDING ATTEMPT =====")
    print(f"[DEBUG] Target chat_id: {chat_id}")
    print(f"[DEBUG] Encoded chat_id: {encoded_chat_id}")
    print(f"[DEBUG] Request URL: {url}")
    print(f"[DEBUG] Request headers: {json.dumps(headers, indent=2)}")
    print(f"[DEBUG] Request data: {json.dumps(data, indent=2)}")
    
    try:
        r = requests.post(url, headers=headers, json=data)
        print(f"[DEBUG] Response status: {r.status_code}")
        print(f"[DEBUG] Response headers: {dict(r.headers)}")
        print(f"[DEBUG] Response body: {r.text}")
        
        if r.status_code == 201:  # Created successfully
            message_data = r.json()
            print(f"[DEBUG] ✅ ADAPTIVE CARD SENDING SUCCESSFUL")
            print(f"[DEBUG] Message ID: {message_data.get('id')}")
            return message_data
        else:
            print(f"[ERROR] ❌ ADAPTIVE CARD SENDING FAILED")
            print(f"[ERROR] Status code: {r.status_code}")
            print(f"[ERROR] Error response: {r.text}")
            r.raise_for_status()
            
    except Exception as e:
        print(f"[ERROR] ❌ EXCEPTION DURING ADAPTIVE CARD SENDING")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise 

# ============================
# Update card helpers/services
# ============================

async def update_card_via_bot_framework(activity_id: str, adapter, app_id: str, updated_card: dict, conversation_reference: Optional[dict] = None) -> dict:
    """Update an existing activity (card) via Bot Framework using the conversation reference."""
    from botbuilder.core import MessageFactory, CardFactory
    from botbuilder.schema import ConversationReference as BFConversationReference
    from bots.teams_conversation_bot import CONVERSATION_REFERENCE as STORED_REFERENCE

    # Resolve conversation reference
    if conversation_reference:
        ref = BFConversationReference().deserialize(conversation_reference)
        # Merge missing fields from stored reference if available
        if STORED_REFERENCE:
            try:
                if not getattr(ref, 'service_url', None):
                    ref.service_url = getattr(STORED_REFERENCE, 'service_url', None)
                if not getattr(ref, 'channel_id', None):
                    ref.channel_id = getattr(STORED_REFERENCE, 'channel_id', None)
                if not getattr(ref, 'conversation', None):
                    ref.conversation = getattr(STORED_REFERENCE, 'conversation', None)
                if not getattr(ref, 'bot', None):
                    ref.bot = getattr(STORED_REFERENCE, 'bot', None)
                if not getattr(ref, 'user', None):
                    ref.user = getattr(STORED_REFERENCE, 'user', None)
            except Exception:
                pass
    else:
        if not STORED_REFERENCE:
            raise Exception("No conversation reference available. Provide 'conversation_reference' from the send response.")
        ref = STORED_REFERENCE

    # Validate required fields
    if not getattr(ref, 'service_url', None):
        raise Exception("BotFrameworkAdapter.send_activity(): service_url can not be None. Use the full 'conversation_reference' from the send response, or ensure the bot has a stored reference by having the user message the bot first.")

    # Choose activity id: strictly use the provided one; if absent, fall back to ref.activityId; if still absent, fail fast
    ref_activity_id = conversation_reference.get("activityId") if isinstance(conversation_reference, dict) else None
    chosen_activity_id = activity_id or ref_activity_id
    if not chosen_activity_id:
        raise Exception("No activity_id provided and conversation_reference.activityId missing. Cannot update.")

    async def logic(turn_context):
        from botbuilder.schema import Activity, ActivityTypes
        print(f"[DEBUG] Starting update_activity for provided_activity_id={activity_id} ref_activity_id={ref_activity_id} chosen_activity_id={chosen_activity_id}")
        # Build adaptive card attachment
        attachment = CardFactory.adaptive_card(updated_card)
        # Build a full Activity to avoid no-op updates in some channels
        def build_activity(with_id: str) -> Activity:
            a = Activity(
                type=ActivityTypes.message,
                attachments=[attachment],
            )
            a.id = with_id
            a.conversation = turn_context.activity.conversation
            a.service_url = turn_context.activity.service_url
            a.channel_id = turn_context.activity.channel_id
            return a

        primary_id = chosen_activity_id
        alternate_id = None
        if activity_id and ref_activity_id and activity_id != ref_activity_id:
            # We prefer provided id first; alternate is the ref id
            primary_id = activity_id
            alternate_id = ref_activity_id
        elif not activity_id and ref_activity_id:
            primary_id = ref_activity_id
        elif activity_id and not ref_activity_id:
            primary_id = activity_id

        tried = []
        last_err = None
        for attempt_id in [primary_id, alternate_id]:
            if not attempt_id or attempt_id in tried:
                continue
            tried.append(attempt_id)
            try:
                act = build_activity(attempt_id)
                print(f"[DEBUG] Attempting update_activity with id={attempt_id}")
                await turn_context.update_activity(act)
                print(f"[DEBUG] update_activity succeeded with id={attempt_id}")
                return
            except Exception as e:
                last_err = e
                print(f"[WARN] update_activity failed with id={attempt_id}: {e}")
                continue
        if last_err:
            raise last_err

    await adapter.continue_conversation(ref, logic, app_id)
    return {"status": "updated", "method": "bot_framework", "activity_id": activity_id, "used_activity_id": chosen_activity_id, "ref_activity_id": ref_activity_id}

def update_card_via_graph_api(chat_id: str, updated_card: dict, access_token: str) -> dict:
    """Graph v1.0 cannot modify an existing adaptive card; send a new one and return its id."""
    message = send_adaptive_card_to_chat(chat_id, updated_card, access_token)
    return {"status": "sent_new_message", "method": "graph_api", "chat_id": chat_id, "message_id": message.get('id') if isinstance(message, dict) else None}

async def update_card_service(activity_id: Optional[str], chat_id: Optional[str], adapter, app_id: str, card_name: Optional[str] = None, conversation_reference: Optional[dict] = None):
    """Entry point to update a previously sent card. Uses Bot Framework update when possible."""
    # Load updated card content
    updated_card = load_updated_tasks_card(card_name or "TasksAssignedToUserUpdated.json")
    if not updated_card:
        return json_response({"error": f"Updated card template '{card_name or 'TasksAssignedToUserUpdated.json'}' not found."}, status=404)

    # Prefer Bot Framework update to replace existing activity
    if activity_id:
        try:
            result = await update_card_via_bot_framework(activity_id, adapter, app_id, updated_card, conversation_reference)
            return json_response(result)
        except Exception as e:
            if not chat_id:
                return json_response({"error": f"Bot Framework update failed: {str(e)}", "recommendation": "Provide 'chat_id' to send updated card as a new message via Graph API, or include 'conversation_reference' for exact replacement."}, status=400)

    # Fallback: Graph API new message
    if chat_id:
        try:
            access_token = get_fresh_graph_access_token()
            result = update_card_via_graph_api(chat_id, updated_card, access_token)
            return json_response(result)
        except Exception as e:
            return json_response({"error": f"Graph API failed to send updated card: {str(e)}"}, status=500)

    return json_response({"error": "Provide 'activity_id' (Bot Framework) to replace the existing card, or 'chat_id' (Graph API) to send a new updated message."}, status=400)