import os
import requests
import json
from datetime import datetime

# Graph API Configuration
GRAPH_CLIENT_ID = os.environ.get("MicrosoftAppId")
GRAPH_CLIENT_SECRET = os.environ.get("MicrosoftAppPassword")
GRAPH_TENANT_ID = os.environ.get("CHANNEL_AUTH_TENANT")

def get_fresh_graph_access_token():
    """Get a fresh access token for Microsoft Graph API"""
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

def find_user_by_email(email, access_token):
    """Find a user by email address using Graph API"""
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

def find_chat_with_user(user_id, access_token):
    """Find existing chat with a user"""
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
    """Create a new chat with a user"""
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

def get_or_create_chat_with_user(user_id, access_token):
    """Get existing chat or create new one with user"""
    # First try to find existing chat
    existing_chat_id = find_chat_with_user(user_id, access_token)
    if existing_chat_id:
        print(f"[DEBUG] Using existing chat: {existing_chat_id}")
        return existing_chat_id
    
    # If no existing chat, create new one
    print(f"[DEBUG] Creating new chat for user_id: {user_id}")
    return create_chat_with_user(user_id, access_token)

def send_card_message_to_chat(chat_id, user_name, message, access_token):
    """Send an adaptive card message to a chat"""
    import urllib.parse
    # URL encode the chat_id since it contains special characters
    encoded_chat_id = urllib.parse.quote(chat_id, safe='')
    url = f"https://graph.microsoft.com/v1.0/chats/{encoded_chat_id}/messages"
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

def send_text_message_to_chat(chat_id, message, access_token):
    """Send a simple text message to a chat"""
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
    print(f"[DEBUG] Message content: {message}")
    r = requests.post(url, headers=headers, json=data)
    print(f"[DEBUG] Send text message response: {r.status_code} {r.text}")
    r.raise_for_status()
    return r.json() 