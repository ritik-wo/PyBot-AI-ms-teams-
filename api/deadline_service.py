"""Deadline card building and utility functions for Microsoft Teams bot."""
import json
import os
import copy
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from .card_loaders import load_deadline_template


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


def build_deadline_card_simple(data: dict) -> Optional[dict]:
    """Build a deadline card using the main template with sample data (no static data)"""
    # Use the main deadline template instead of the deleted simple one
    return build_deadline_card_from_sample_exm(data.get('tasks', []))


def transform_sample_data_to_progressmaker_format(sample_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Transform old sample data format to ProgressMaker API format for proper placeholder replacement"""
    if not sample_data or 'tasks' not in sample_data:
        return []
    
    transformed_tasks = []
    for task in sample_data.get('tasks', []):
        # Transform each task to match ProgressMaker API structure
        transformed_task = {
            "id": f"task-{len(transformed_tasks) + 1}",
            "description": task.get('title', 'Progress Item'),
            "progressItemType": task.get('type', 'agreement').lower(),
            "assignee": "user@example.com",
            "dueDate": "2025-09-06",  # Will be formatted later
            "meetingDate": "2025-09-01",  # Will be formatted later
            "touchPointOrigin": {
                "id": f"origin-{len(transformed_tasks) + 1}",
                "title": task.get('meetingOrigin', 'Weekly Review'),
                "sprintId": "sprint-1",
                "itemId": f"item-{len(transformed_tasks) + 1}"
            },
            "agendaItem": {
                "id": f"agenda-{len(transformed_tasks) + 1}",
                "title": task.get('agendaItem', 'Progress Review'),
                "position": len(transformed_tasks)
            },
            "itemRelation": {
                "id": f"relation-{len(transformed_tasks) + 1}",
                "name": task.get('relation', 'Progress Target'),
                "itemType": "target"
            },
            "resolved": False,
            "itemId": f"item-{len(transformed_tasks) + 1}"
        }
        
        # Handle due date formatting
        due_date_str = task.get('dueDate', '01.02.')
        if due_date_str == '01.02.':
            transformed_task['dueDate'] = '2025-02-01'
        else:
            transformed_task['dueDate'] = '2025-09-06'
            
        # Handle meeting date formatting  
        meeting_date_str = task.get('meetingDate', '27.01.2026')
        if meeting_date_str == '27.01.2026':
            transformed_task['meetingDate'] = '2026-01-27'
        else:
            transformed_task['meetingDate'] = '2025-09-01'
        
        transformed_tasks.append(transformed_task)
    
    print(f"[DEBUG] Transformed {len(transformed_tasks)} tasks from sample data to ProgressMaker format")
    return transformed_tasks


def build_deadline_card_from_sample_exm(tasks_for_user: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Build deadline card using template with placeholders populated with actual sample data.
    Preserves all IDs, selectActions, toggles, and interactive functionality.
    Expected tasks_for_user: List of task dictionaries from ProgressMaker sample data
    """
    template = load_deadline_template()
    if not template:
        print("[ERROR] Deadline template not found")
        return None

    # Create a deep copy of the template
    card = copy.deepcopy(template)
    
    try:
        if tasks_for_user and len(tasks_for_user) > 0:
            # Use the first task for the main card content
            primary_task = tasks_for_user[0]
            secondary_task = tasks_for_user[1] if len(tasks_for_user) > 1 else primary_task
            
            print(f"[DEBUG] Building deadline card with task: {primary_task.get('title', 'Unknown')}")
            
            # Calculate days left for deadline
            days_left = "2"
            try:
                due_date = primary_task.get('dueDate', '2025-09-06')
                if isinstance(due_date, str) and len(due_date) > 5:
                    parsed_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).date()
                    days_remaining = (parsed_date - date.today()).days
                    days_left = str(max(0, days_remaining))
            except:
                days_left = "2"
            
            # Format dates
            formatted_due_date = "06.09."
            formatted_meeting_date = "01.09.2025"
            try:
                due_date = primary_task.get('dueDate', '2025-09-06')
                if isinstance(due_date, str) and len(due_date) > 5:
                    parsed_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    formatted_due_date = parsed_date.strftime('%d.%m.')
                
                meeting_date = primary_task.get('meetingDate', '2025-09-01')
                if isinstance(meeting_date, str) and len(meeting_date) > 5:
                    parsed_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
                    formatted_meeting_date = parsed_date.strftime('%d.%m.%Y')
            except:
                pass
            
            # Create placeholder mapping using correct field names from ProgressMaker API
            placeholder_data = {
                '{{task.title}}': str(primary_task.get('description', 'Progress Item')),
                '{{task.progressItem}}': str(primary_task.get('description', 'Progress Item')),
                '{{task.secondaryTitle}}': str(secondary_task.get('description', 'Secondary Progress Item')),
                '{{task.type}}': str(primary_task.get('progressItemType', 'agreement')).title(),
                '{{task.dueDate}}': formatted_due_date,
                '{{task.relation}}': str(primary_task.get('itemRelation', {}).get('name', 'Progress Target')),
                '{{meeting.origin}}': str(primary_task.get('touchPointOrigin', {}).get('title', 'Weekly Review')),
                '{{meeting.date}}': formatted_meeting_date,
                '{{meeting.agendaItem}}': str(primary_task.get('agendaItem', {}).get('title', 'Progress Review')),
                '{{deadline.daysLeft}}': days_left
            }
            
            print(f"[DEBUG] Placeholder mapping: {placeholder_data}")
            
            # Replace placeholders in the card
            def replace_placeholders(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, str):
                            for placeholder, replacement in placeholder_data.items():
                                if placeholder in value:
                                    obj[key] = value.replace(placeholder, replacement)
                                    print(f"[DEBUG] Replaced {placeholder} with {replacement}")
                        elif isinstance(value, (dict, list)):
                            replace_placeholders(value)
                elif isinstance(obj, list):
                    for item in obj:
                        replace_placeholders(item)
            
            # Apply placeholder replacement
            replace_placeholders(card)
            
            # Update toggles with actual task data
            def update_toggles(obj):
                if isinstance(obj, dict):
                    if obj.get('type') == 'Input.Toggle':
                        task_id = primary_task.get('taskId', primary_task.get('id', 'unknown'))
                        obj['id'] = f"toggle_{task_id}"
                        obj['value'] = not primary_task.get('resolved', True)  # resolved=False means not completed
                        print(f"[DEBUG] Updated toggle {obj['id']} to: {obj['value']}")
                    for value in obj.values():
                        if isinstance(value, (dict, list)):
                            update_toggles(value)
                elif isinstance(obj, list):
                    for item in obj:
                        update_toggles(item)
            
            update_toggles(card)
            
            # Update action data for task submission
            if 'actions' in card and len(card['actions']) > 0:
                action = card['actions'][0]
                if 'data' not in action:
                    action['data'] = {}
                action['data']['action'] = 'update_deadline_tasks'
                action['data']['source'] = 'progressmaker_deadline_notification'
                action['data']['task_ids'] = [t.get('taskId', t.get('id')) for t in tasks_for_user]
                action['data']['user_email'] = primary_task.get('assignedTo', 'unknown@example.com')
        
        else:
            print("[WARNING] No tasks provided for deadline card - using template as-is")
    
    except Exception as e:
        print(f"[ERROR] Failed to build deadline card: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
    
    return card


def build_task_status_card(data: dict) -> Optional[dict]:
    """Build the task status card using taskStatus.json and placeholder population.
    This ensures the first column (Progress item) binds to tasks[i].title exactly as the template defines.
    """
    from .card_loaders import load_task_status_template
    from api.cards.utils import populate_placeholders
    
    template = load_task_status_template()
    if not template:
        print("[ERROR] taskStatus.json template not found")
        return None
    try:
        return populate_placeholders(template, data)
    except Exception as e:
        print(f"[ERROR] Failed to populate taskStatus template: {e}")
        return None
