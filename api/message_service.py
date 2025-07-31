from aiohttp.web import json_response
import json
import os
import requests
from api.graph_api import (
    get_fresh_graph_access_token, 
    find_user_by_email, 
    get_or_create_chat_with_user, 
    send_card_message_to_chat,
    send_teams_activity_message
)
from api.bot_framework_api import send_message_via_bot_framework

def load_tasks_assigned_card():
    """Load the TasksAssignedToUser adaptive card template"""
    card_path = os.path.join(os.getcwd(), "resources", "post-meeting-cards", "TasksAssignedToUser.json")
    try:
        with open(card_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load adaptive card template: {e}")
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

async def send_message_to_user_service(email, message, adapter, app_id):
    """Main service function to send messages to users using hybrid approach"""
    try:
        print(f"[DEBUG] ===== STARTING MESSAGE SERVICE =====")
        print(f"[DEBUG] Target email: {email}")
        print(f"[DEBUG] Message content: {message} (will be ignored - sending TasksAssignedToUser card)")
        print(f"[DEBUG] App ID: {app_id}")
        
        # Load the adaptive card template
        adaptive_card = load_tasks_assigned_card()
        print(f"[DEBUG] ✅ Loaded TasksAssignedToUser adaptive card template")
        
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
                send_adaptive_card_to_chat(chat_id, adaptive_card, access_token)
                print(f"[DEBUG] ✅ Successfully sent TasksAssignedToUser card to {email}")
                
                return json_response({
                    "status": f"TasksAssignedToUser card sent to {email}", 
                    "method": "graph_api",
                    "chat_id": chat_id,
                    "user_id": user["id"]
                })
                
            except Exception as graph_error:
                print(f"[ERROR] ❌ Graph API chat approach failed: {graph_error}")
                print(f"[DEBUG] 🔄 Trying Teams Activity API as final fallback...")
                
                # Final fallback: Teams Activity API
                try:
                    print(f"[DEBUG] Using Teams Activity API...")
                    send_teams_activity_with_card(user["id"], adaptive_card, access_token)
                    print(f"[DEBUG] ✅ Successfully sent TasksAssignedToUser card via Teams Activity API to {email}")
                    
                    return json_response({
                        "status": f"TasksAssignedToUser card sent to {email} via Teams Activity API", 
                        "method": "teams_activity_api",
                        "user_id": user["id"],
                        "note": "User may need to install the bot in Teams for full functionality"
                    })
                    
                except Exception as teams_activity_error:
                    print(f"[ERROR] ❌ Teams Activity API approach failed: {teams_activity_error}")
                    print(f"[DEBUG] ===== FINAL ERROR SUMMARY =====")
                    print(f"[DEBUG] Bot Framework error: {bot_error}")
                    print(f"[DEBUG] Graph API error: {graph_error}")
                    print(f"[DEBUG] Teams Activity API error: {teams_activity_error}")
                    return json_response({
                        "error": f"All messaging approaches failed. User may need to interact with the bot first or install it in Teams.",
                        "bot_error": str(bot_error),
                        "graph_error": str(graph_error),
                        "teams_activity_error": str(teams_activity_error),
                        "recommendation": "Have the user send a message to the bot in Teams first, or install the bot in Teams"
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
    print(f"[DEBUG] Creating conversation with user: {user.get('displayName', user.get('mail', 'Unknown'))}")
    
    from botbuilder.schema import ConversationParameters, ChannelAccount
    from botbuilder.core import MessageFactory, CardFactory
    
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
    async def send_message(turn_context):
        await turn_context.send_activity(MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card)))
        print(f"[DEBUG] Successfully sent TasksAssignedToUser card to {user.get('mail', 'Unknown')}")
    
    await adapter.create_conversation(
        conversation_reference,
        send_message,
        conversation_parameters
    )
    
    return {
        "status": f"TasksAssignedToUser card sent to {user.get('mail', 'Unknown')}", 
        "method": "bot_framework",
        "user_id": user["id"]
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

def send_teams_activity_with_card(user_id, adaptive_card, access_token):
    """Send the TasksAssignedToUser adaptive card using Teams Activity API"""
    import requests
    from datetime import datetime
    
    url = "https://graph.microsoft.com/v1.0/teams/activity/send"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    data = {
        "topic": {
            "source": "entityUrl",
            "value": f"https://graph.microsoft.com/v1.0/users/{user_id}"
        },
        "activityType": "taskCreated",
        "previewText": {
            "content": "New Progress items assigned to you"
        },
        "recipient": {
            "@odata.type": "microsoft.graph.aadUserConversationMember",
            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}"
        },
        "templateParameters": [
            {
                "name": "cardContent",
                "value": json.dumps(adaptive_card)
            }
        ]
    }
    
    print(f"[DEBUG] Sending Teams activity with TasksAssignedToUser card to user_id: {user_id}")
    print(f"[DEBUG] Teams activity data: {json.dumps(data, indent=2)}")
    r = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] Teams activity response: {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json() 