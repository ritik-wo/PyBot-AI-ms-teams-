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

# Import the message service
from api.message_service import send_message_to_user_service, update_card_service

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

    # Call the bot's custom method to send to all members
    await BOT.send_message_to_all_members(message, ADAPTER)
    return json_response({"status": "Message sent to all members"})


# Endpoint to send message to a specific user
async def send_message_to_user(req: Request) -> Response:
    data = await req.json()
    email = data.get("email")
    message = data.get("message")
    card_name = data.get("card_name")
    # Optional: conversation reference (for exact proactive update context)
    conversation_reference = data.get("conversation_reference")

    # Accept card data in multiple convenient ways:
    # 1) Explicit key: card_data or data
    # 2) Inline at root (same format as sampleData.json) alongside email/message
    card_data = data.get("card_data") or data.get("data")
    if not card_data:
        # If the payload itself looks like the card schema, extract it by excluding known control keys
        possible_keys = {"cardTitle", "departmentName", "meetingTime", "meetingDateTime", "progressIndicator", "badgeText", "progressText", "tasks", "actionButtonText"}
        if any(k in data for k in possible_keys):
            card_data = {k: v for k, v in data.items() if k not in {"email", "message", "card_name", "conversation_reference"}}
    if not email or not message:
        return json_response({"error": "Missing 'email' or 'message' in payload"}, status=400)
    
    # Use the message service to handle the sending logic
    return await send_message_to_user_service(
        email,
        message,
        ADAPTER,
        CONFIG.APP_ID,
        card_name,
        conversation_reference,
        card_data
    )


# Add a root route
async def root(request):
    return json_response({"message": "Teams Bot API is running!"})

APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)
APP.router.add_post("/api/send-message-to-all", send_message_to_all)
APP.router.add_post("/api/send-message-to-user", send_message_to_user)
 
async def update_card(req: Request) -> Response:
    data = await req.json()
    activity_id = data.get("activity_id")
    chat_id = data.get("chat_id")
    card_name = data.get("card_name")  # Optional override, defaults to TasksAssignedToUserUpdated.json
    conversation_reference = data.get("conversation_reference")  # Optional, preferred for exact replace
    if not activity_id and not chat_id:
        return json_response({"error": "Provide either 'activity_id' (Bot Framework) or 'chat_id' (Graph API)."}, status=400)
    return await update_card_service(activity_id, chat_id, ADAPTER, CONFIG.APP_ID, card_name, conversation_reference)

APP.router.add_post("/api/update-card", update_card)
APP.router.add_get("/", root)

if __name__ == "__main__":
    try:
        # Use PORT from environment variable (for Render) or fallback to CONFIG.PORT
        port = int(os.environ.get("PORT", CONFIG.PORT))
        print(f"[INFO] Starting bot on port: {port}")
        web.run_app(APP, host="0.0.0.0", port=port)
    except Exception as error:
        raise error