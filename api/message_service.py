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
from typing import Optional

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
    data_path = os.path.join(os.getcwd(), "resources", "sampleData.json")
    try:
        print(f"[DEBUG] Loading sample data from: {data_path}")
        with open(data_path, "r", encoding="utf-8") as f:
            sample_data = json.loads(f.read())
            print(f"[DEBUG] ✅ Sample data loaded successfully")
            return sample_data
    except Exception as e:
        print(f"[ERROR] Failed to load sample data: {e}")
        return None

def build_dynamic_card_with_tasks(data: dict) -> dict:
    """Build dynamic card using task_assigning_card_template.json as base and injecting task sections"""
    import copy
    
    print(f"[DEBUG] Building dynamic card with task injection...")
    
    # Load base template (header + footer)
    base_template = load_card_by_name("task_assigning_card_template.json")
    if not base_template:
        print(f"[ERROR] Failed to load base template")
        return None
    
    # Load full template to extract task section
    full_template = load_card_by_name("TasksAssignedToUser.json")
    if not full_template:
        print(f"[ERROR] Failed to load full template for task extraction")
        return None
    
    # Get task count
    tasks = data.get('tasks', [])
    task_count = len(tasks)
    print(f"[DEBUG] Detected {task_count} tasks in data")
    
    # Extract task section template
    task_section_template = extract_task_section_template(full_template)
    if not task_section_template:
        print(f"[ERROR] Failed to extract task section template")
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

def extract_task_section_template(full_template: dict) -> dict:
    """Extract the complete task section template including table header and task rows"""
    try:
        print(f"[DEBUG] Extracting task section template with table structure...")
        
        # Look for the table structure in the template
        def find_table_structure(items):
            table_elements = []
            
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    # Look for the table header (ColumnSet with "Progress item", "Type", "Due date")
                    if (item.get('type') == 'ColumnSet' and 
                        'Progress item' in str(item)):
                        print(f"[DEBUG] Found table header at index {i}")
                        table_elements.append(item)
                        
                        # Look for the first task row (Container with tasks[0])
                        for j in range(i + 1, len(items)):
                            next_item = items[j]
                            if (isinstance(next_item, dict) and 
                                next_item.get('type') == 'Container' and 
                                'tasks[0]' in str(next_item) and 
                                'selectAction' in next_item):
                                print(f"[DEBUG] Found first task row at index {j}")
                                table_elements.append(next_item)
                                
                                # Look for the details container
                                for k in range(j + 1, len(items)):
                                    details_item = items[k]
                                    if (isinstance(details_item, dict) and 
                                        details_item.get('type') == 'Container' and 
                                        details_item.get('id') == 'details1'):
                                        print(f"[DEBUG] Found details container at index {k}")
                                        table_elements.append(details_item)
                                        break
                                break
                        
                        if len(table_elements) >= 2:  # At least header + one task row
                            print(f"[DEBUG] ✅ Found complete table structure with {len(table_elements)} elements")
                            return table_elements
                    
                    # Recursively search in nested items
                    if 'items' in item:
                        result = find_table_structure(item['items'])
                        if result:
                            return result
                    
                    # Also check in body if it exists
                    if 'body' in item:
                        result = find_table_structure(item['body'])
                        if result:
                            return result
            
            return None
        
        # Start searching from the body
        body = full_template.get('body', [])
        table_structure = find_table_structure(body)
        
        if table_structure and len(table_structure) >= 2:
            # Return the table header and task template
            return {
                "table_header": table_structure[0],  # The ColumnSet with headers
                "task_row_template": table_structure[1],  # The Container with task[0] data
                "task_details_template": table_structure[2] if len(table_structure) > 2 else None
            }
        
        print(f"[ERROR] Could not find complete table structure in template")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to extract task section template: {e}")
        return None

def generate_task_sections(task_template: dict, task_count: int, tasks: list) -> list:
    """Generate table header + N task rows based on template structure and set icons per task."""
    import copy
    import json
    
    print(f"[DEBUG] Generating table with {task_count} task rows...")
    
    if not task_template or not isinstance(task_template, dict):
        print(f"[ERROR] Invalid task template provided")
        return []
    
    table_sections = []
    
    # Add the table header first (only once)
    if 'table_header' in task_template:
        table_sections.append(copy.deepcopy(task_template['table_header']))
        print(f"[DEBUG] Added table header")
    
    # Generate task rows
    task_row_template = task_template.get('task_row_template')
    task_details_template = task_template.get('task_details_template')
    
    if not task_row_template:
        print(f"[ERROR] No task row template found")
        return table_sections
    
    for i in range(task_count):
        # Deep copy the task row template
        task_row = copy.deepcopy(task_row_template)
        
        # Convert to string for replacement
        row_str = json.dumps(task_row)
        
        # Replace task[0] with task[i] and details1 with details{i+1}
        row_str = row_str.replace('tasks[0]', f'tasks[{i}]')
        row_str = row_str.replace('details1', f'details{i+1}')
        
        # Convert back to dict
        try:
            updated_row = json.loads(row_str)
            # Set icon for this row based on task type
            try:
                icon_name = get_icon_for_task_type(tasks[i].get('type'))
                _set_icons_in_subtree(updated_row, icon_name)
            except Exception:
                pass
            # Fix selectAction so this row toggles only its own details container
            try:
                _fix_row_toggle_action(updated_row, details_id=f"details{i+1}")
            except Exception:
                pass
            table_sections.append(updated_row)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse updated task row: {e}")
            continue
        
        # Add the details container if available
        if task_details_template:
            task_details = copy.deepcopy(task_details_template)
            
            # Convert to string for replacement
            details_str = json.dumps(task_details)
            
            # Replace task[0] with task[i] and details1 with details{i+1}
            details_str = details_str.replace('tasks[0]', f'tasks[{i}]')
            details_str = details_str.replace('details1', f'details{i+1}')
            
            # Convert back to dict
            try:
                updated_details = json.loads(details_str)
                # Set icon(s) inside the details section as well (if any)
                try:
                    icon_name = get_icon_for_task_type(tasks[i].get('type'))
                    _set_icons_in_subtree(updated_details, icon_name)
                except Exception:
                    pass
                table_sections.append(updated_details)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse updated task details: {e}")
                continue
    
    print(f"[DEBUG] ✅ Generated table with {len(table_sections)} elements (1 header + {task_count} task rows + details)")
    return table_sections

def inject_task_sections_into_card(card: dict, task_sections: list):
    """Inject task sections into card body before the footer"""
    print(f"[DEBUG] Injecting {len(task_sections)} task sections into card...")
    
    body = card.get('body', [])
    
    # Find insertion point (before the action button container)
    insertion_index = len(body) - 1  # Default to before last item
    
    for i, item in enumerate(body):
        if isinstance(item, dict) and item.get('type') == 'Container':
            # Check if this container has ActionSet (footer)
            items = item.get('items', [])
            for sub_item in items:
                if isinstance(sub_item, dict) and sub_item.get('type') == 'ActionSet':
                    insertion_index = i
                    break
    
    # Insert task sections at the found position
    for i, task_section in enumerate(task_sections):
        body.insert(insertion_index + i, task_section)
    
    print(f"[DEBUG] ✅ Task sections injected at position {insertion_index}")

def populate_placeholders(template: dict, data: dict) -> dict:
    """Populate template placeholders with data"""
    import re
    
    def replace_placeholders(obj):
        if isinstance(obj, dict):
            return {key: replace_placeholders(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [replace_placeholders(item) for item in obj]
        elif isinstance(obj, str):
            # Replace {{placeholder}} with actual data
            def replacer(match):
                placeholder = match.group(1)
                try:
                    # Handle nested properties like tasks[0].title
                    if '[' in placeholder and ']' in placeholder:
                        # Parse array access like tasks[0].title
                        parts = placeholder.split('.')
                        result = data
                        for part in parts:
                            if '[' in part and ']' in part:
                                # Handle array access
                                array_name = part.split('[')[0]
                                index = int(part.split('[')[1].split(']')[0])
                                result = result[array_name][index]
                            else:
                                result = result[part]
                        return str(result)
                    else:
                        # Simple property access
                        parts = placeholder.split('.')
                        result = data
                        for part in parts:
                            result = result[part]
                        return str(result)
                except (KeyError, IndexError, TypeError):
                    print(f"[WARN] Placeholder not found in data: {placeholder}")
                    return match.group(0)  # Return original if not found
            
            return re.sub(r'\{\{([^}]+)\}\}', replacer, obj)
        else:
            return obj
    
    print(f"[DEBUG] Populating placeholders...")
    populated_card = replace_placeholders(template)
    
    # Normalize icons globally per request (e.g., CheckmarkCircle -> Info)
    try:
        populated_card = replace_icon_names(populated_card, from_name='CheckmarkCircle', to_name='Info')
    except Exception as _e:
        print(f"[WARN] Icon normalization skipped due to error: {_e}")
    
    print(f"[DEBUG] ✅ Placeholders populated successfully")
    return populated_card

def get_icon_for_task_type(task_type: str) -> str:
    """Simple mapping from task type to icon name."""
    mapping = {
        'Agreement': 'CheckmarkStarburst',
        'Decision': 'Diamond',
        'Issue': 'Info',
    }
    return mapping.get(task_type, 'CheckmarkStarburst')

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
            for item in obj:
                visit(item)
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