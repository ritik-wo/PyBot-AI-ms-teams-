#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

async def test_detailed_error():
    """Test to see the actual error from the bot"""
    
    print("=== DETAILED ERROR ANALYSIS ===\n")
    
    activity = {
        "type": "message",
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "serviceUrl": "http://localhost:3978/",
        "channelId": "emulator", 
        "from": {
            "id": "user-test-id",
            "name": "Test User"
        },
        "conversation": {
            "id": "test-conversation"
        },
        "recipient": {
            "id": "28:2851b584-7025-47ce-ba67-5dd1922ce0ad",
            "name": "Test Bot"
        },
        "text": "hello",  # Simple message
        "locale": "en-US"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer fake-token'
    }
    
    print("🎯 Sending simple 'hello' message...")
    print("📤 Activity:", json.dumps(activity, indent=2))
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:3978/api/messages", json=activity, headers=headers) as response:
                print(f"\n📊 Response Status: {response.status}")
                print(f"📊 Response Headers: {dict(response.headers)}")
                
                response_text = await response.text()
                print(f"📊 Response Body: {response_text}")
                
                if response.status == 500:
                    print("\n🔍 ANALYSIS:")
                    print("The bot is throwing a 500 error, not a 401!")
                    print("This means the authentication is not the issue.")
                    print("The issue is in your bot's message processing logic.")
                    
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("Make sure the auth bot is running on port 3978")
    input("Press Enter to continue...")
    asyncio.run(test_detailed_error())
