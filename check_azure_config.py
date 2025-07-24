#!/usr/bin/env python3

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_ID = os.environ.get("MicrosoftAppId")
APP_PASSWORD = os.environ.get("MicrosoftAppPassword")

def get_access_token():
    """Get access token for Microsoft Graph API"""
    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': APP_ID,
        'client_secret': APP_PASSWORD,
        'scope': 'https://graph.microsoft.com/.default'
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Token request status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get('access_token')
        else:
            print(f"Token request failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def check_bot_framework_auth():
    """Test Bot Framework authentication"""
    url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': APP_ID,
        'client_secret': APP_PASSWORD,
        'scope': 'https://api.botframework.com/.default'
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"\n=== Bot Framework Authentication ===")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Bot Framework authentication successful")
            print(f"Token type: {token_data.get('token_type', 'N/A')}")
            print(f"Expires in: {token_data.get('expires_in', 'N/A')} seconds")
            return token_data.get('access_token')
        else:
            print("❌ Bot Framework authentication failed")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error with Bot Framework auth: {e}")
        return None

def main():
    print("=== Azure AD App Registration Checker ===")
    print(f"App ID: {APP_ID}")
    print(f"App Password: {'*' * len(APP_PASSWORD) if APP_PASSWORD else 'NOT SET'}")
    
    if not APP_ID or not APP_PASSWORD:
        print("❌ Missing APP_ID or APP_PASSWORD in environment variables")
        return
    
    # Test Bot Framework authentication (this is what your bot uses)
    bot_token = check_bot_framework_auth()
    
    # Test Graph API authentication (for additional permissions)
    print(f"\n=== Microsoft Graph Authentication ===")
    graph_token = get_access_token()
    
    if graph_token:
        print("✅ Graph API authentication successful")
    else:
        print("❌ Graph API authentication failed")
    
    print(f"\n=== Summary ===")
    print(f"Bot Framework Auth: {'✅ Success' if bot_token else '❌ Failed'}")
    print(f"Graph API Auth: {'✅ Success' if graph_token else '❌ Failed'}")
    
    if not bot_token:
        print(f"\n❌ CRITICAL: Bot Framework authentication failed!")
        print(f"This is why your bot gets 401 errors when sending messages.")
        print(f"\nTo fix this:")
        print(f"1. Go to Azure Portal → Microsoft Entra ID → App registrations")
        print(f"2. Find your app: {APP_ID}")
        print(f"3. Check 'Certificates & secrets' - regenerate client secret if needed")
        print(f"4. Verify the app is not disabled or expired")
        print(f"5. Check if Conditional Access policies are blocking the app")
    
    if bot_token and not graph_token:
        print(f"\n⚠️  Bot Framework works but Graph API fails")
        print(f"This means basic bot messaging should work, but advanced Teams features won't")
        print(f"Add Microsoft Graph permissions if you need them:")
        print(f"- TeamMember.Read.All")
        print(f"- Team.ReadBasic.All") 
        print(f"- User.Read.All")

if __name__ == "__main__":
    main()
