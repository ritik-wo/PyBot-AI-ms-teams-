#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

async def test_bot_endpoints():
    """Automated tests to narrow down the 401 issue"""
    
    print("=== AUTOMATED NARROWING DOWN TESTS ===\n")
    
    # Test configurations
    tests = [
        {
            "name": "Test 1: With Authentication (Simulating Emulator)",
            "url": "http://localhost:3978/api/messages",
            "auth_required": True,
            "app_id": "2851b584-7025-47ce-ba67-5dd1922ce0ad"
        },
        {
            "name": "Test 2: No Authentication",
            "url": "http://localhost:3979/api/messages", 
            "auth_required": False,
            "app_id": ""
        }
    ]
    
    for test in tests:
        print(f"\n{'='*50}")
        print(f"{test['name']}")
        print(f"{'='*50}")
        
        try:
            await run_single_test(test)
        except Exception as e:
            print(f"❌ Test setup failed: {e}")
    
    print(f"\n{'='*50}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*50}")

async def run_single_test(test_config):
    """Run a single bot test"""
    
    url = test_config["url"]
    auth_required = test_config["auth_required"]
    app_id = test_config["app_id"]
    
    # Create a realistic bot activity (similar to what emulator/Teams sends)
    activity = create_test_activity(app_id, auth_required)
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Add auth header if required (simulating emulator)
    if auth_required:
        # This simulates what Bot Framework Emulator would send
        headers['Authorization'] = 'Bearer fake-emulator-token'
        print("🔐 Using authentication headers")
    else:
        print("🔓 No authentication")
    
    print(f"🎯 Testing endpoint: {url}")
    print(f"📤 Sending test message...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=activity, headers=headers) as response:
                print(f"📊 Response Status: {response.status}")
                print(f"📊 Response Headers: {dict(response.headers)}")
                
                response_text = await response.text()
                
                if response.status == 200:
                    print("✅ SUCCESS: Bot responded successfully!")
                    print("✅ This means the bot logic and basic communication works")
                    
                elif response.status == 401:
                    print("❌ FAILED: 401 Unauthorized")
                    print("❌ This indicates an authentication problem")
                    print("🔍 Response body:", response_text[:200] if response_text else "Empty")
                    
                elif response.status == 500:
                    print("⚠️  INTERNAL ERROR: Bot logic error")
                    print("🔍 Response body:", response_text[:500] if response_text else "Empty")
                    
                else:
                    print(f"❓ UNEXPECTED: Status {response.status}")
                    print("🔍 Response body:", response_text[:200] if response_text else "Empty")
                
    except aiohttp.ClientConnectorError:
        print("❌ CONNECTION FAILED: Bot is not running on this port")
        print("💡 Make sure the bot is started before running tests")
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")

def create_test_activity(app_id, auth_required=True):
    """Create a test activity similar to what emulator/Teams would send"""
    
    activity = {
        "type": "message",
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "serviceUrl": "http://localhost:3978/",  # Emulator service URL
        "channelId": "emulator" if auth_required else "test",
        "from": {
            "id": "user-test-id",
            "name": "Test User"
        },
        "conversation": {
            "id": "test-conversation-id"
        },
        "recipient": {
            "id": f"28:{app_id}" if app_id else "bot",
            "name": "Test Bot"
        },
        "text": "Hello Bot",
        "locale": "en-US"
    }
    
    return activity

async def analyze_results():
    """Provide analysis based on test results"""
    
    print("\n🎯 RESULT ANALYSIS:")
    print("="*50)
    
    print("\nIf you see these results, here's what they mean:\n")
    
    print("📈 SCENARIO A: Test 1 ✅ SUCCESS, Test 2 ✅ SUCCESS")
    print("   → Your bot logic works fine")
    print("   → The issue is specifically with Teams service URL authentication")
    print("   → Solution: Check Azure Bot registration Teams channel settings")
    print()
    
    print("📈 SCENARIO B: Test 1 ❌ 401 ERROR, Test 2 ✅ SUCCESS") 
    print("   → Bot logic is fine, but credentials are wrong")
    print("   → Solution: Regenerate Azure Bot credentials")
    print()
    
    print("📈 SCENARIO C: Test 1 ❌ ERROR, Test 2 ❌ ERROR")
    print("   → Bot logic has issues")  
    print("   → Solution: Fix bot code before testing authentication")
    print()
    
    print("📈 SCENARIO D: Test 1 ✅ SUCCESS, Teams still fails")
    print("   → Teams-specific service URL authentication issue")
    print("   → Solution: Check service URL permissions in Azure")

if __name__ == "__main__":
    print("🤖 Starting automated bot testing...")
    print("💡 Make sure both bots are running:")
    print("   - python app.py (port 3978)")
    print("   - python app_no_auth.py (port 3979)")
    print()
    
    input("Press Enter when both bots are running...")
    
    asyncio.run(test_bot_endpoints())
    asyncio.run(analyze_results())
