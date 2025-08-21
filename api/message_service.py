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

async def send_message_to_user_service(email, message, adapter, app_id, card_name=None, conversation_reference: Optional[dict] = None):
    """Main service function to send messages to users using hybrid approach"""
    try:
        print(f"[DEBUG] ===== STARTING MESSAGE SERVICE =====")
        print(f"[DEBUG] Target email: {email}")
        print(f"[DEBUG] Message content: {message}")
        print(f"[DEBUG] App ID: {app_id}")
        print(f"[DEBUG] Card name: {card_name}")
        
        # Load the adaptive card template by name
        if card_name:
            adaptive_card = load_card_by_name(card_name)
            if not adaptive_card:
                return json_response({"error": f"Card template '{card_name}' not found."}, status=404)
        else:
            adaptive_card = load_card_by_name("TasksAssignedToUser.json")
            if not adaptive_card:
                return json_response({"error": "Default card template 'TasksAssignedToUser.json' not found."}, status=404)
        print(f"[DEBUG] ✅ Loaded adaptive card template: {card_name or 'TasksAssignedToUser.json'}")
        
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

    # Choose correct activity id to update. In Teams, BF activity ids are GUID-like. Graph ids are numeric.
    chosen_activity_id = activity_id
    try:
        import re
        guid_like = re.compile(r"^[0-9a-fA-F-]{16,}$")
        if not activity_id or not guid_like.match(activity_id):
            # Prefer the activityId embedded in the conversation reference if provided
            if conversation_reference and isinstance(conversation_reference, dict):
                ref_activity_id = conversation_reference.get("activityId") or conversation_reference.get("activity_id")
                if ref_activity_id and guid_like.match(ref_activity_id):
                    chosen_activity_id = ref_activity_id
    except Exception:
        pass

    async def logic(turn_context):
        from botbuilder.schema import Activity, ActivityTypes
        print(f"[DEBUG] Starting update_activity for activity_id={activity_id} chosen_activity_id={chosen_activity_id}")
        # Build adaptive card attachment
        attachment = CardFactory.adaptive_card(updated_card)
        # Build a full Activity to avoid no-op updates in some channels
        updated_activity = Activity(
            type=ActivityTypes.message,
            attachments=[attachment],
        )
        updated_activity.id = chosen_activity_id
        # Ensure routing fields are set explicitly
        updated_activity.conversation = turn_context.activity.conversation
        updated_activity.service_url = turn_context.activity.service_url
        updated_activity.channel_id = turn_context.activity.channel_id
        print(f"[DEBUG] Update payload ready. conversation_id={updated_activity.conversation.id if updated_activity.conversation else 'None'} service_url={updated_activity.service_url}")
        await turn_context.update_activity(updated_activity)
        print(f"[DEBUG] update_activity invoked successfully for chosen_activity_id={chosen_activity_id}")

    await adapter.continue_conversation(ref, logic, app_id)
    return {"status": "updated", "method": "bot_framework", "activity_id": activity_id, "used_activity_id": chosen_activity_id}

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