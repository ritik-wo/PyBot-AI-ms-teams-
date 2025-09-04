"""Card update service for Microsoft Teams bot adaptive cards."""
import json
from typing import Optional, Dict, Any
from aiohttp.web import json_response
from api.graph_api import get_fresh_graph_access_token
from .card_loaders import load_updated_tasks_card
from .messaging_core import send_adaptive_card_to_chat


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
