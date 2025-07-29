# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
import uuid
from datetime import datetime
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botframework.connector.auth import SimpleCredentialProvider
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bots import TeamsConversationBot
from config import DefaultConfig
from dotenv import load_dotenv
import os
from pathlib import Path
import requests
import json

# Explicitly load the .env file from the project root
load_dotenv(dotenv_path=Path('.') / '.env')

print("MicrosoftAppId from env:", os.environ.get("MicrosoftAppId"))
print("MicrosoftAppPassword from env:", os.environ.get("MicrosoftAppPassword"))

CONFIG = DefaultConfig()
print(f"Loaded APP_ID: {CONFIG.APP_ID}")
print(f"Loaded APP_PASSWORD: {CONFIG.APP_PASSWORD[:5]}***")

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
SETTINGS = BotFrameworkAdapterSettings(
    app_id=CONFIG.APP_ID,
    app_password=CONFIG.APP_PASSWORD,
    channel_auth_tenant = CONFIG.CHANNEL_AUTH_TENANT

)
ADAPTER = BotFrameworkAdapter(SETTINGS)

ADAPTER._credential_provider = SimpleCredentialProvider(
    app_id=CONFIG.APP_ID,
    password=CONFIG.APP_PASSWORD
)


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


ADAPTER.on_turn_error = on_error

# If the channel is the Emulator, and authentication is not in use, the AppId will be null.
# We generate a random AppId for this case only. This is not required for production, since
# the AppId will have a value.
APP_ID = SETTINGS.app_id if SETTINGS.app_id else uuid.uuid4()

# Create the Bot
BOT = TeamsConversationBot(CONFIG.APP_ID, CONFIG.APP_PASSWORD)

# Helper: Get Microsoft Graph access token
GRAPH_CLIENT_ID = os.environ.get("MicrosoftAppId")
GRAPH_CLIENT_SECRET = os.environ.get("MicrosoftAppPassword")
GRAPH_TENANT_ID = os.environ.get("CHANNEL_AUTH_TENANT")

def get_graph_access_token():
    url = f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": GRAPH_CLIENT_ID,
        "client_secret": GRAPH_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    print(f"[DEBUG] Requesting Graph access token from {url}")
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]

# Helper: Find user by email

def find_user_by_email(email, access_token):
    url = f"https://graph.microsoft.com/v1.0/users?$filter=mail eq '{email}' or userPrincipalName eq '{email}'"
    headers = {"Authorization": f"Bearer {access_token}"}
    print(f"[DEBUG] Finding user by email: {email}")
    r = requests.get(url, headers=headers)
    print(f"[DEBUG] Find user response: {r.status_code} {r.text}")
    r.raise_for_status()
    users = r.json().get("value", [])
    if not users:
        print(f"[ERROR] No user found for email: {email}")
        return None
    print(f"[DEBUG] Found user: {users[0]}")
    return users[0]

# Helper: Find existing chat with user
def find_chat_with_user(user_id, access_token):
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/chats"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    print(f"[DEBUG] Finding existing chats for user_id: {user_id}")
    r = requests.get(url, headers=headers)
    print(f"[DEBUG] Find chats response: {r.status_code} {r.text}")
    
    if r.status_code == 200:
        chats = r.json().get("value", [])
        # Look for one-on-one chats
        for chat in chats:
            if chat.get("chatType") == "oneOnOne":
                print(f"[DEBUG] Found existing one-on-one chat: {chat['id']}")
                return chat["id"]
    
    print(f"[DEBUG] No existing one-on-one chat found for user_id: {user_id}")
    return None

def create_chat_with_user(user_id, access_token):
    url = "https://graph.microsoft.com/v1.0/chats"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {
        "chatType": "oneOnOne",
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"
            }
        ]
    }
    print(f"[DEBUG] Creating chat with user_id: {user_id}")
    r = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] Create chat response: {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()["id"]

# Helper: Get or create chat with user
def get_or_create_chat_with_user(user_id, access_token):
    # First try to find existing chat
    existing_chat_id = find_chat_with_user(user_id, access_token)
    if existing_chat_id:
        print(f"[DEBUG] Using existing chat: {existing_chat_id}")
        return existing_chat_id
    
    # If no existing chat, create new one
    print(f"[DEBUG] Creating new chat for user_id: {user_id}")
    return create_chat_with_user(user_id, access_token)

# Helper: Send card message to chat

def send_card_message_to_chat(chat_id, user_name, message, access_token):
    url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    card_content = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {"type": "TextBlock", "text": f"Hello {user_name}", "weight": "bolder", "size": "medium"},
            {"type": "TextBlock", "text": message}
        ]
    }
    data = {
        "body": {
            "contentType": "html",
            "content": f"<div>Hello {user_name}</div>"
        },
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card_content
            }
        ]
    }
    print(f"[DEBUG] Sending card message to chat_id: {chat_id}")
    r = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] Send card message response: {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()

# Helper: Send simple text message to chat (for testing)
def send_text_message_to_chat(chat_id, message, access_token):
    import urllib.parse
    # URL encode the chat_id since it contains special characters
    encoded_chat_id = urllib.parse.quote(chat_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/chats/{encoded_chat_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {
        "body": {
            "contentType": "html",
            "content": message
        }
    }
    print(f"[DEBUG] Sending text message to chat_id: {chat_id}")
    print(f"[DEBUG] Encoded chat_id: {encoded_chat_id}")
    print(f"[DEBUG] Full URL: {url}")
    print(f"[DEBUG] Message content: {message}")
    print(f"[DEBUG] Request headers: {headers}")
    print(f"[DEBUG] Request data: {data}")
    r = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] Send text message response: {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()

# Helper: Get fresh access token with detailed logging
def get_fresh_graph_access_token():
    url = f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": GRAPH_CLIENT_ID,
        "client_secret": GRAPH_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    print(f"[DEBUG] Requesting fresh Graph access token from {url}")
    print(f"[DEBUG] Using client_id: {GRAPH_CLIENT_ID}")
    print(f"[DEBUG] Using tenant_id: {GRAPH_TENANT_ID}")
    r = requests.post(url, data=data)
    print(f"[DEBUG] Fresh token response: {r.status_code} {r.text}")
    r.raise_for_status()
    token_data = r.json()
    print(f"[DEBUG] Token type: {token_data.get('token_type')}")
    print(f"[DEBUG] Token expires in: {token_data.get('expires_in')} seconds")
    return token_data["access_token"]

# Helper: Send message using Teams Activity API
def send_teams_activity_message(user_id, message, access_token):
    url = "https://graph.microsoft.com/v1.0/teams/activity/send"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    # Create adaptive card content
    card_content = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": f"Hello! 👋",
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
                        "value": "Teams Activity API 📡"
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
    
    data = {
        "topic": {
            "source": "entityUrl",
            "value": f"https://graph.microsoft.com/v1.0/users/{user_id}"
        },
        "activityType": "taskCreated",
        "previewText": {
            "content": message[:100] + "..." if len(message) > 100 else message
        },
        "recipient": {
            "@odata.type": "microsoft.graph.aadUserConversationMember",
            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}"
        },
        "templateParameters": [
            {
                "name": "cardContent",
                "value": json.dumps(card_content)
            }
        ]
    }
    
    print(f"[DEBUG] Sending Teams activity to user_id: {user_id}")
    print(f"[DEBUG] Teams activity data: {json.dumps(data, indent=2)}")
    r = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] Teams activity response: {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json()


# Listen for incoming requests on /api/messages.
async def messages(req: Request) -> Response:
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=HTTPStatus.OK)


# New endpoint to send a message to all members
async def send_message_to_all(req: Request) -> Response:
    data = await req.json()
    message = data.get("message")
    if not message:
        return json_response({"error": "Missing 'message' in payload"}, status=400)

    # Create a minimal fake activity to pass to the bot logic
    activity = Activity(
        type="message",
        text=message,
        channel_id="msteams",
        service_url="https://smba.trafficmanager.net/",  # Placeholder, not used in this context
        conversation=None,  # Not used, as we will get all members
        from_property=None,  # Not used
        recipient=None,  # Not used
    )
    auth_header = ""

    # Call the bot's custom method to send to all members
    await BOT.send_message_to_all_members(message)
    return json_response({"status": "Message sent to all members"})


# Update the endpoint to use Bot Framework proactive messaging (simplified approach)
async def send_message_to_user(req: Request) -> Response:
    data = await req.json()
    email = data.get("email")
    message = data.get("message")
    if not email or not message:
        return json_response({"error": "Missing 'email' or 'message' in payload"}, status=400)
    
    try:
        print(f"[DEBUG] Starting send_message_to_user for {email}")
        
        # Get fresh access token to find user
        access_token = get_fresh_graph_access_token()
        
        # Find the user by email
        user = find_user_by_email(email, access_token)
        if not user:
            return json_response({"error": f"User with email {email} not found"}, status=404)
        
        print(f"[DEBUG] Found user: {user.get('displayName', email)} with ID: {user['id']}")
        
        # Import the global conversation reference from the bot
        from bots.teams_conversation_bot import CONVERSATION_REFERENCE
        
        if not CONVERSATION_REFERENCE:
            return json_response({"error": "No conversation reference available. Have a user interact with the bot first in Teams."}, status=400)
        
        # Use Bot Framework's proactive messaging to create a new conversation
        from botbuilder.schema import ConversationParameters, ChannelAccount
        from botbuilder.core import MessageFactory, CardFactory
        
        async def send_to_user_logic(turn_context):
            try:
                print(f"[DEBUG] Creating conversation with user: {user.get('displayName', email)}")
                
                # Create a channel account for the target user
                target_user = ChannelAccount(
                    id=user['id'],
                    name=user.get('displayName', email)
                )
                
                # Create conversation parameters
                conversation_parameters = ConversationParameters(
                    is_group=False,
                    bot=turn_context.activity.recipient,
                    members=[target_user],
                    tenant_id=turn_context.activity.conversation.tenant_id,
                )
                
                # Create adaptive card
                adaptive_card = {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Hello {user.get('displayName', email)}! 👋",
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
                
                # Send the adaptive card
                async def send_message(tc):
                    await tc.send_activity(MessageFactory.attachment(CardFactory.adaptive_card(adaptive_card)))
                    print(f"[DEBUG] Successfully sent adaptive card to {email}")
                
                await turn_context.adapter.create_conversation(
                    CONVERSATION_REFERENCE,
                    send_message,
                    conversation_parameters
                )
                
            except Exception as e:
                print(f"[ERROR] Failed to send message to {email}: {e}")
                import traceback
                traceback.print_exc()
        
        # Execute the proactive messaging
        await ADAPTER.continue_conversation(CONVERSATION_REFERENCE, send_to_user_logic, CONFIG.APP_ID)
        
        return json_response({"status": f"Adaptive card sent to {email}", "method": "bot_framework"})
        
    except Exception as e:
        print(f"[ERROR] Failed to send message to {email}: {e}")
        import traceback
        traceback.print_exc()
        return json_response({"error": str(e)}, status=500)


# Add a root route
async def root(request):
    return json_response({"message": "Teams Bot API is running!"})

APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)
APP.router.add_post("/api/send-message-to-all", send_message_to_all)
APP.router.add_post("/api/send-message-to-user", send_message_to_user)
APP.router.add_get("/", root)

if __name__ == "__main__":
    try:
        # Use PORT from environment variable (for Render) or fallback to CONFIG.PORT
        port = int(os.environ.get("PORT", CONFIG.PORT))
        print(f"[INFO] Starting bot on port: {port}")
        web.run_app(APP, host="0.0.0.0", port=port)
    except Exception as error:
        raise error