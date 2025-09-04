"""Core messaging functionality for Microsoft Teams bot."""
import json
from typing import Dict, Any, Optional
from aiohttp.web import json_response
from api.graph_api import (
    get_fresh_graph_access_token, 
    find_user_by_email, 
    get_or_create_chat_with_user
)
from api.bot_framework_api import send_message_via_bot_framework
from .card_loaders import load_sample_data
from api.cards.tasks_assigned import build_dynamic_card_with_tasks
from .deadline_service import build_deadline_card_from_sample_exm


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
            # Provide detailed error to aid debugging without fallbacks
            return json_response({
                "error": "Failed to build dynamic card with tasks",
                "reason": "extract_task_section_template returned None or builder aborted",
                "hint": "Check server logs for [ERROR] and [DIAG] lines from api/cards/tasks_assigned.extract_task_section_template(). They report ColumnSet/Container counts and placeholder presence.",
                "expected_template": "resources/post-meeting-cards/TasksAssignedToUser.json",
                "notes": [
                    "Header is detected as a ColumnSet immediately followed by a Container with selectAction and task placeholders",
                    "Details container id should start with 'details'",
                    "Verify your template retains placeholders like tasks[0] or {{tasks[",
                ]
            }, status=500)
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
    """Builds the deadline card (deadline_template.json style) from provided data and sends it to the given email.
    Tries Bot Framework proactive messaging first; falls back to Graph API chat.
    """
    try:
        print("[DEBUG] ===== STARTING DEADLINE MESSAGE SERVICE =====")
        print(f"[DEBUG] Target email: {email}")
        # Use ProgressMaker service fallback data directly
        from services.progressmaker_service import ProgressMakerService
        pm_service = ProgressMakerService()
        # Call with dummy parameters to trigger fallback data
        all_tasks_data = await pm_service.query_progress_items("dummy-execution", "dummy-sprint", "2025-09-06")
        
        # Get user info to find their assignee ID
        print(f"[DEBUG] Getting fresh Graph API access token...")
        access_token = get_fresh_graph_access_token()
        print(f"[DEBUG] ✅ Access token obtained successfully")
        
        print(f"[DEBUG] Looking up user by email...")
        user = find_user_by_email(email, access_token)
        if not user:
            return json_response({"error": f"User with email {email} not found"}, status=404)
        
        # For now, we'll use a mapping of email to assignee ID
        # In a real implementation, this would come from the user management system
        email_to_assignee_map = {
            "user1@example.com": "a6a5c4aa-6755-4b3d-ba57-e18ed225e35a",
            "user2@example.com": "cdc82f24-a55a-43ad-a580-86009a2c31e2"
        }
        
        user_assignee_id = email_to_assignee_map.get(email)
        if not user_assignee_id:
            print(f"[DEBUG] No assignee ID found for email {email}, using first assignee from sample data")
            user_assignee_id = "a6a5c4aa-6755-4b3d-ba57-e18ed225e35a"  # Default to first user for testing
        
        # Filter tasks for this specific user
        tasks_data = [task for task in all_tasks_data if task.get("assignee") == user_assignee_id]
        print(f"[DEBUG] Filtered {len(tasks_data)} tasks for assignee {user_assignee_id}")
        
        if not tasks_data:
            return json_response({"message": f"No deadline tasks found for user {email}"}, status=200)
        
        adaptive_card = build_deadline_card_from_sample_exm(tasks_data)
        if not adaptive_card:
            return json_response({"error": "Failed to build deadline card from template"}, status=500)

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
    import requests
    
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
