#!/usr/bin/env python3

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

async def test_no_auth_bot():
    """Test the no-authentication bot first"""
    
    print("=== TESTING NO-AUTH BOT (Port 3979) ===\n")
    
    activity = {
        "type": "message",
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "serviceUrl": "http://localhost:3979/",
        "channelId": "test",
        "from": {
            "id": "user-test-id", 
            "name": "Test User"
        },
        "conversation": {
            "id": "test-conversation"
        },
        "recipient": {
            "id": "bot",
            "name": "Test Bot"
        },
        "text": "Hello Bot",
        "locale": "en-US"
    }
    
    headers = {'Content-Type': 'application/json'}
    
    print("🎯 Testing no-auth bot at: http://localhost:3979/api/messages")
    print("📤 Sending test message...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:3979/api/messages", json=activity, headers=headers) as response:
                print(f"📊 Response Status: {response.status}")
                
                response_text = await response.text()
                
                if response.status == 200:
                    print("✅ SUCCESS: No-auth bot works!")
                    print("✅ This means your bot logic is correct")
                    return True
                    
                elif response.status == 401:
                    print("❌ UNEXPECTED: No-auth bot returning 401")
                    print("🔍 This shouldn't happen with no authentication")
                    
                elif response.status == 500:
                    print("⚠️  INTERNAL ERROR: Bot logic issue")
                    print("🔍 Response:", response_text[:500])
                    
                else:
                    print(f"❓ Status {response.status}")
                    print("🔍 Response:", response_text[:200])
                    
                return False
                
    except aiohttp.ClientConnectorError:
        print("❌ CONNECTION FAILED: No-auth bot not running")
        print("💡 Start it with: python app_no_auth.py")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

async def test_auth_bot():
    """Test the authentication bot"""
    
    print("\n=== TESTING AUTH BOT (Port 3978) ===\n")
    
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
        "text": "Hello Bot",
        "locale": "en-US"
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer fake-emulator-token'  # Simulating emulator
    }
    
    print("🎯 Testing auth bot at: http://localhost:3978/api/messages")
    print("📤 Sending test message with auth header...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:3978/api/messages", json=activity, headers=headers) as response:
                print(f"📊 Response Status: {response.status}")
                
                response_text = await response.text()
                
                if response.status == 200:
                    print("✅ SUCCESS: Auth bot works!")
                    print("✅ This means credentials are working")
                    return True
                    
                elif response.status == 401:
                    print("❌ FAILED: Auth bot returning 401")
                    print("❌ This is the same error we see from Teams!")
                    print("🔍 Response:", response_text[:200])
                    
                elif response.status == 500:
                    print("⚠️  INTERNAL ERROR: Bot logic issue")
                    print("🔍 Response:", response_text[:500])
                    
                else:
                    print(f"❓ Status {response.status}")
                    print("🔍 Response:", response_text[:200])
                    
                return False
                
    except aiohttp.ClientConnectorError:
        print("❌ CONNECTION FAILED: Auth bot not running")
        print("💡 Start it with: python app.py")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def analyze_results(no_auth_result, auth_result):
    """Analyze the test results"""
    
    print(f"\n{'='*60}")
    print("🎯 ANALYSIS & DIAGNOSIS")
    print(f"{'='*60}")
    
    if no_auth_result and auth_result:
        print("\n📈 SCENARIO A: Both tests PASSED ✅")
        print("   → Your bot logic is perfect")
        print("   → Your credentials are working")
        print("   → The issue is SPECIFICALLY with Teams service URL")
        print("\n🔧 SOLUTION:")
        print("   → Check Azure Bot registration")
        print("   → Verify Teams channel is enabled")
        print("   → Check service URL permissions")
        
    elif no_auth_result and not auth_result:
        print("\n📈 SCENARIO B: No-auth PASSED ✅, Auth FAILED ❌")
        print("   → Your bot logic is correct")
        print("   → BUT credentials/authentication is broken")
        print("\n🔧 SOLUTION:")
        print("   → Regenerate Azure Bot credentials")
        print("   → Check App ID and Password match exactly")
        print("   → Verify bot registration settings")
        
    elif not no_auth_result and not auth_result:
        print("\n📈 SCENARIO C: Both tests FAILED ❌")
        print("   → Your bot logic has issues")
        print("   → Need to fix bot code first")
        print("\n🔧 SOLUTION:")
        print("   → Fix bot logic errors")
        print("   → Check bot response handling")
        
    elif not no_auth_result and auth_result:
        print("\n📈 SCENARIO D: No-auth FAILED ❌, Auth PASSED ✅")
        print("   → Unexpected scenario")
        print("   → Possible configuration issue")
        
    else:
        print("\n❓ UNEXPECTED RESULT COMBINATION")

async def main():
    """Run the step-by-step analysis"""
    
    print("🤖 AUTOMATED BOT NARROWING ANALYSIS")
    print("="*60)
    print("This will test both bots to isolate the authentication issue")
    print()
    
    # Test no-auth bot first (should be running on 3979)
    no_auth_result = await test_no_auth_bot()
    
    # Wait a moment
    await asyncio.sleep(2)
    
    # Test auth bot (need to start it on 3978)
    print("\n" + "="*60)
    print("NOW TESTING AUTH BOT")
    print("💡 Make sure to start: python app.py (in another terminal)")
    input("\nPress Enter when auth bot is running on port 3978...")
    
    auth_result = await test_auth_bot()
    
    # Analyze results
    analyze_results(no_auth_result, auth_result)

if __name__ == "__main__":
    asyncio.run(main())
