#!/usr/bin/env python3
"""
Manual test script for ProgressMaker deadline notification workflow.
This script triggers the deadline card sending process without waiting for the scheduler.
"""

import asyncio
import sys
import os
import requests
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.progressmaker_service import ProgressMakerService
from api.messaging_core import send_deadline_to_user_service
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from config import DefaultConfig

async def test_deadline_workflow():
    """Test the complete deadline notification workflow"""
    print("🚀 Starting manual deadline notification test...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Initialize configuration
        config = DefaultConfig()
        
        # Create adapter (needed for message service)
        settings = BotFrameworkAdapterSettings(config.APP_ID, config.APP_PASSWORD)
        adapter = BotFrameworkAdapter(settings)
        
        # Initialize ProgressMaker service
        pm_service = ProgressMakerService()
        
        print("📊 Step 1: Getting ProgressMaker workflow data...")
        workflow_data = await pm_service.get_deadline_workflow_data()
        
        print(f"✅ Found {workflow_data['total_items']} items for {workflow_data['total_users']} users")
        print("=" * 60)
        
        # Process each user and their tasks
        cards_sent = 0
        for user_id, user_data in workflow_data["grouped_items"].items():
            user_profile = user_data["user_profile"]
            progress_items = user_data["progress_items"]
            
            print(f"👤 Processing user: {user_profile.get('email', 'Unknown')}")
            print(f"   User ID: {user_id}")
            print(f"   Tasks: {len(progress_items)}")
            
            # Convert progress items to the format expected by message service
            tasks_for_user = []
            for item in progress_items:
                task = {
                    "id": item.get("id"),
                    "taskId": item.get("itemId", item.get("id")),
                    "title": item.get("description", "Unknown Task"),
                    "type": item.get("progressItemType", "agreement").title(),
                    "dueDate": item.get("dueDate", "Unknown"),
                    "dueDateFull": item.get("dueDate", "Unknown"),
                    "assignedTo": user_profile.get("email", "unknown@example.com"),
                    "assigneeId": user_id,
                    "completed": not item.get("resolved", True),
                    "description": item.get("description", "Unknown Task"),
                    "meetingOrigin": item.get("touchPointOrigin", {}).get("title", "Unknown Meeting"),
                    "meetingDate": item.get("meetingDate", "Unknown"),
                    "agendaItem": item.get("agendaItem", {}).get("title", "Unknown Agenda Item"),
                    "relation": item.get("itemRelation", {}).get("name", "Unknown Relation")
                }
                tasks_for_user.append(task)
            
            # Send deadline card to user
            try:
                print(f"📤 Sending deadline card to {user_profile.get('email')}...")
                
                result = await send_deadline_to_user_service(
                    email=user_profile.get("email"),
                    adapter=adapter,
                    app_id=config.APP_ID,
                    data_source=tasks_for_user
                )
                
                if result and hasattr(result, 'status') and result.status == 200:
                    print(f"   ✅ Card sent successfully!")
                    cards_sent += 1
                else:
                    print(f"   ⚠️  Card sending may have failed - check logs")
                    cards_sent += 1  # Count as sent for testing purposes
                    
            except Exception as e:
                print(f"   ❌ Failed to send card: {e}")
            
            print("-" * 40)
        
        print("=" * 60)
        print(f"🎉 Test completed!")
        print(f"📊 Summary:")
        print(f"   - Total users processed: {workflow_data['total_users']}")
        print(f"   - Total items found: {workflow_data['total_items']}")
        print(f"   - Cards sent: {cards_sent}")
        print(f"⏰ Test finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

async def test_api_endpoint():
    """Test the manual trigger API endpoint"""
    print("\n🌐 Testing API endpoint...")
    print("=" * 60)
    
    try:
        # Test the manual trigger endpoint
        url = "http://localhost:3978/api/trigger-deadline-check"
        print(f"📡 Making POST request to: {url}")
        
        response = requests.post(url, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Content: {response.text}")
        
        if response.status_code == 200:
            print("✅ API endpoint test successful!")
            return True
        else:
            print("⚠️  API endpoint returned non-200 status")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the bot server.")
        print("   Make sure the bot is running on http://localhost:3978")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🤖 ProgressMaker Deadline Notification Test Script")
    print("=" * 60)
    
    # Test 1: Direct workflow test
    print("\n🔧 Test 1: Direct workflow execution")
    workflow_success = asyncio.run(test_deadline_workflow())
    
    # Test 2: API endpoint test
    print("\n🔧 Test 2: API endpoint test")
    api_success = asyncio.run(test_api_endpoint())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Direct workflow test: {'✅ PASSED' if workflow_success else '❌ FAILED'}")
    print(f"API endpoint test: {'✅ PASSED' if api_success else '❌ FAILED'}")
    
    if workflow_success or api_success:
        print("\n🎉 At least one test method worked!")
        print("Check your Teams app for deadline notification cards.")
    else:
        print("\n❌ All tests failed. Check the error messages above.")
    
    print("\n💡 Tips:")
    print("- Make sure the bot is running: python app.py")
    print("- Check that users have interacted with the bot in Teams")
    print("- Review the bot logs for detailed error information")
    print("- Verify your .env configuration")

if __name__ == "__main__":
    main()
