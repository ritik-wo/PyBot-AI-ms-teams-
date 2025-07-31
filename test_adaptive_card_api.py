#!/usr/bin/env python3
"""
Test script to verify the API endpoint sends the TasksAssignedToUser adaptive card
"""

import requests
import json

def test_send_adaptive_card():
    """Test sending the TasksAssignedToUser adaptive card via API"""
    
    # API endpoint URL (adjust if running on different port)
    url = "http://localhost:3978/api/send-message-to-user"
    
    # Test payload
    payload = {
        "email": "TeamsAIAdmin@progressmaker.io",  # Replace with actual test email
        "message": "This message will be ignored - only the adaptive card will be sent"
    }
    
    print("🧪 Testing API endpoint...")
    print(f"📧 Target email: {payload['email']}")
    print(f"💬 Message: {payload['message']}")
    print(f"🎯 Expected: TasksAssignedToUser adaptive card will be sent")
    print("-" * 50)
    
    try:
        # Send POST request
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        print(f"📝 Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: API call completed successfully!")
            response_data = response.json()
            print(f"📊 Method used: {response_data.get('method', 'Unknown')}")
            print(f"👤 User ID: {response_data.get('user_id', 'Unknown')}")
            if 'chat_id' in response_data:
                print(f"💬 Chat ID: {response_data.get('chat_id')}")
        else:
            print("❌ FAILED: API call returned error status")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API server")
        print("💡 Make sure the server is running on http://localhost:3978")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_send_adaptive_card() 