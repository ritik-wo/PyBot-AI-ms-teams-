# Test bot without authentication for narrowing down the issue

import sys
import traceback
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bots import TeamsConversationBot

# Create adapter without authentication
SETTINGS = BotFrameworkAdapterSettings(
    app_id="",  # Empty for no auth
    app_password=""  # Empty for no auth
)

print("CREATING ADAPTER WITHOUT AUTHENTICATION")
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Simple bot without credentials
BOT = TeamsConversationBot("", "")

# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

ADAPTER.on_turn_error = on_error

# Listen for incoming requests on /api/messages.
async def messages(req: Request) -> Response:
    print("NO-AUTH REQUEST=>>>", req.method, req.url)
    
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
        print("NO-AUTH BODY=>>>", body)
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = ""  # No auth header
    
    print("NO-AUTH ACTIVITY=>>>", activity.text if hasattr(activity, 'text') else 'No text')
    
    try:
        response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        print("NO-AUTH RESPONSE=>>>", response)
    except Exception as e:
        print("NO-AUTH ERROR=>>>", str(e))
        traceback.print_exc()
        raise
        
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=HTTPStatus.OK)

APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    print("Starting bot without authentication on port 3979...")
    try:
        web.run_app(APP, host="localhost", port=3979)
    except Exception as error:
        raise error
