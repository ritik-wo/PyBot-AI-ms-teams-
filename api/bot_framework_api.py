from datetime import datetime
from botbuilder.schema import ConversationParameters, ChannelAccount
from botbuilder.core import MessageFactory, CardFactory

def create_adaptive_card(user_name, message):
    """Create an adaptive card with the given content"""
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": f"Hello {user_name}! 👋",
                "weight": "bolder",
                "size": "large",
                "color": "accent"
            },
            {
                "type": "TextBlock",
                "text": message,
                "wrap": True,
                "spacing": "medium"
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "Sent via:",
                        "value": "Bot Framework API 📡"
                    },
                    {
                        "title": "Timestamp:",
                        "value": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 🕐"
                    }
                ],
                "spacing": "medium"
            }
        ],
        "actions": [
            {
                "type": "Action.Submit",
                "title": "Reply with 'Hello Bot!' 👋",
                "data": {
                    "action": "reply",
                    "message": "Hello Bot!"
                }
            }
        ]
    }

async def send_message_via_bot_framework(user, message, adapter, conversation_reference, app_id):
    """Send a message using Bot Framework proactive messaging"""
    print(f"[DEBUG] Creating conversation with user: {user.get('displayName', user.get('mail', 'Unknown'))}")
    
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
    
    # Create adaptive card
    adaptive_card = create_adaptive_card(user.get('displayName', user.get('mail', 'Unknown')), message)
    
    # Send the adaptive card
    async def send_message(turn_context):
        await turn_context.send_activity(MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card)))
        print(f"[DEBUG] Successfully sent adaptive card to {user.get('mail', 'Unknown')}")
    
    await adapter.create_conversation(
        conversation_reference,
        send_message,
        conversation_parameters
    )
    
    return {
        "status": f"Adaptive card sent to {user.get('mail', 'Unknown')}", 
        "method": "bot_framework",
        "user_id": user["id"]
    } 