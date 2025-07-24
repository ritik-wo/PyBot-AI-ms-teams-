#!/usr/bin/env python3

import asyncio
from botbuilder.core import (
    BotFrameworkAdapter, 
    BotFrameworkAdapterSettings,
    TurnContext,
    MessageFactory
)
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, ConversationAccount
from config import DefaultConfig
import urllib.parse

async def test_adapter_authentication():
    """Test Bot Framework Adapter authentication directly"""
    
    CONFIG = DefaultConfig()
    
    print("=== Testing Bot Framework Adapter Authentication ===\n")
    
    # Test with raw password
    print("--- Testing with RAW password ---")
    await test_adapter_with_password(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
    
    # Test with encoded password  
    print("\n--- Testing with URL-ENCODED password ---")
    encoded_password = urllib.parse.quote(CONFIG.APP_PASSWORD, safe="")
    await test_adapter_with_password(CONFIG.APP_ID, encoded_password)

async def test_adapter_with_password(app_id, password):
    """Test adapter with specific password"""
    
    print(f"App ID: {app_id}")
    print(f"Password (first 10): {password[:10]}...")
    
    try:
        # Create adapter settings
        settings = BotFrameworkAdapterSettings(
            app_id=app_id,
            app_password=password
        )
        
        print("✓ Settings created successfully")
        
        # Create adapter
        adapter = BotFrameworkAdapter(settings)
        print("✓ Adapter created successfully")
        
        # Create a fake activity similar to what Teams sends
        activity = Activity(
            type=ActivityTypes.message,
            id="test-123",
            service_url="https://smba.trafficmanager.net/de/17065ed5-05ba-4fc2-b58a-1fb199142f59/",
            channel_id="msteams",
            from_property=ChannelAccount(
                id="29:test-user",
                name="Test User"
            ),
            conversation=ConversationAccount(
                id="a:test-conversation",
                tenant_id="17065ed5-05ba-4fc2-b58a-1fb199142f59"
            ),
            recipient=ChannelAccount(
                id=f"28:{app_id}",
                name="Test Bot"
            ),
            text="test message"
        )
        
        print("✓ Test activity created")
        
        # Create turn context
        turn_context = TurnContext(adapter, activity)
        print("✓ Turn context created")
        
        # Try to send a simple message (this is where the 401 happens)
        print("🔄 Attempting to send message...")
        
        try:
            # This should fail with the 401 error we're seeing
            await turn_context.send_activity("Hello! This is a test message.")
            print("✅ SUCCESS! Message sent without error!")
            
        except Exception as e:
            print(f"❌ FAILED to send message: {e}")
            print(f"Error type: {type(e)}")
            
            # Check if it's the same 401 error
            if "Unauthorized" in str(e):
                print("🎯 This is the same 401 Unauthorized error!")
            else:
                print("❓ Different error than expected")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Failed to create adapter: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_adapter_authentication())
