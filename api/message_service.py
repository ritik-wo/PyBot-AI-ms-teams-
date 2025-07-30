from aiohttp.web import json_response
from api.graph_api import (
    get_fresh_graph_access_token, 
    find_user_by_email, 
    get_or_create_chat_with_user, 
    send_card_message_to_chat,
    send_teams_activity_message
)
from api.bot_framework_api import send_message_via_bot_framework

async def send_message_to_user_service(email, message, adapter, app_id):
    """Main service function to send messages to users using hybrid approach"""
    try:
        print(f"[DEBUG] Starting send_message_to_user for {email}")
        
        # Get fresh access token to find user
        access_token = get_fresh_graph_access_token()
        
        # Find the user by email
        user = find_user_by_email(email, access_token)
        if not user:
            return json_response({"error": f"User with email {email} not found"}, status=404)
        
        print(f"[DEBUG] Found user: {user.get('displayName', email)} with ID: {user['id']}")
        
        # Try Bot Framework approach first (for users who have interacted with bot)
        try:
            from bots.teams_conversation_bot import CONVERSATION_REFERENCE
            
            if CONVERSATION_REFERENCE:
                print(f"[DEBUG] Trying Bot Framework approach first")
                
                # Use Bot Framework's proactive messaging
                result = await send_message_via_bot_framework(
                    user, message, adapter, CONVERSATION_REFERENCE, app_id
                )
                
                return json_response(result)
            else:
                print(f"[DEBUG] No conversation reference available, trying Graph API")
                raise Exception("No conversation reference")
                
        except Exception as bot_error:
            print(f"[DEBUG] Bot Framework approach failed: {bot_error}")
            print(f"[DEBUG] Falling back to Graph API approach")
            
            # Fallback to Graph API approach
            try:
                # Create or find existing chat with the user using Graph API
                chat_id = get_or_create_chat_with_user(user["id"], access_token)
                if not chat_id:
                    return json_response({"error": f"Could not find or create chat for user {email}"}, status=500)
                
                print(f"[DEBUG] Using chat_id: {chat_id}")
                
                # Send adaptive card message using Graph API
                send_card_message_to_chat(chat_id, user.get("displayName", email), message, access_token)
                print(f"[DEBUG] Successfully sent adaptive card to {email}")
                
                return json_response({
                    "status": f"Adaptive card sent to {email}", 
                    "method": "graph_api",
                    "chat_id": chat_id,
                    "user_id": user["id"]
                })
                
            except Exception as graph_error:
                print(f"[ERROR] Graph API chat approach failed: {graph_error}")
                print(f"[DEBUG] Trying Teams Activity API as final fallback")
                
                # Final fallback: Try Teams Activity API
                try:
                    send_teams_activity_message(user["id"], message, access_token)
                    print(f"[DEBUG] Successfully sent via Teams Activity API to {email}")
                    
                    return json_response({
                        "status": f"Message sent to {email} via Teams Activity API", 
                        "method": "teams_activity_api",
                        "user_id": user["id"]
                    })
                    
                except Exception as teams_error:
                    print(f"[ERROR] Teams Activity API also failed: {teams_error}")
                    return json_response({
                        "error": f"All approaches failed. User may need to interact with the bot first.",
                        "bot_error": str(bot_error),
                        "graph_error": str(graph_error),
                        "teams_error": str(teams_error)
                    }, status=500)
        
    except Exception as e:
        print(f"[ERROR] Failed to send message to {email}: {e}")
        import traceback
        traceback.print_exc()
        return json_response({"error": str(e)}, status=500) 