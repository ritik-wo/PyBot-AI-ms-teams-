#!/usr/bin/env python3

import asyncio
import aiohttp
from msal import ConfidentialClientApplication
from config import DefaultConfig
import urllib.parse

CONFIG = DefaultConfig()

# Test both raw and encoded passwords
RAW_PASSWORD = "JYw8Q~ETbPYjgQ1e37DMva.Cz.yR~MZ7V3RsZaoA"
ENCODED_PASSWORD = urllib.parse.quote(RAW_PASSWORD, safe="")

async def test_bot_authentication():
    """Test if the bot credentials can authenticate with Microsoft Graph API"""
    
    print(f"Testing authentication with App ID: {CONFIG.APP_ID}")
    print(f"App Password (first 10 chars): {CONFIG.APP_PASSWORD[:10]}...")
    
    # Create MSAL client application
    app = ConfidentialClientApplication(
        client_id=CONFIG.APP_ID,
        client_credential=CONFIG.APP_PASSWORD,
        authority="https://login.microsoftonline.com/botframework.com"
    )
    
    # Test getting a token for Bot Framework
    scopes = ["https://api.botframework.com/.default"]
    
    try:
        result = app.acquire_token_silent(scopes, account=None)
        
        if not result:
            print("No cached token available, acquiring new token...")
            result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            print("✓ Successfully obtained access token!")
            print(f"Token type: {result.get('token_type', 'N/A')}")
            print(f"Expires in: {result.get('expires_in', 'N/A')} seconds")
            print(f"Token (first 50 chars): {result['access_token'][:50]}...")
            
            # Test making a request to Bot Framework API
            await test_bot_framework_api(result['access_token'])
            
        else:
            print("❌ Failed to obtain access token!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Error description: {result.get('error_description', 'No description')}")
            print(f"Error codes: {result.get('error_codes', 'No codes')}")
            
    except Exception as e:
        print(f"❌ Exception during authentication: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()

async def test_bot_framework_api(access_token):
    """Test making a request to Bot Framework API with the token"""
    
    print("\n--- Testing Bot Framework API ---")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Test endpoint - get bot info
    test_url = f"https://api.botframework.com/v3/conversations"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, headers=headers) as response:
                print(f"API Response Status: {response.status}")
                print(f"API Response Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    print("✓ Bot Framework API call successful!")
                elif response.status == 401:
                    print("❌ Bot Framework API returned 401 Unauthorized")
                    print("This suggests the token is invalid or expired")
                elif response.status == 403:
                    print("❌ Bot Framework API returned 403 Forbidden")
                    print("This suggests the token doesn't have the required permissions")
                else:
                    print(f"❌ Bot Framework API returned status {response.status}")
                
                text = await response.text()
                print(f"Response body (first 200 chars): {text[:200]}")
                
    except Exception as e:
        print(f"❌ Exception during API test: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_teams_token():
    """Test getting token specifically for Teams"""
    print("\n--- Testing Teams-specific token ---")
    
    app = ConfidentialClientApplication(
        client_id=CONFIG.APP_ID,
        client_credential=CONFIG.APP_PASSWORD,
        authority="https://login.microsoftonline.com/common"
    )
    
    # Teams-specific scopes
    scopes = ["https://graph.microsoft.com/.default"]
    
    try:
        result = app.acquire_token_for_client(scopes=scopes)
        
        if "access_token" in result:
            print("✓ Successfully obtained Teams/Graph access token!")
            print(f"Token type: {result.get('token_type', 'N/A')}")
            print(f"Expires in: {result.get('expires_in', 'N/A')} seconds")
            return result['access_token']
        else:
            print("❌ Failed to obtain Teams access token!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Error description: {result.get('error_description', 'No description')}")
            
    except Exception as e:
        print(f"❌ Exception during Teams authentication: {str(e)}")
        
    return None

if __name__ == "__main__":
    print("=== Bot Authentication Debug Tool ===\n")
    asyncio.run(test_bot_authentication())
    asyncio.run(test_teams_token())
    print("\n=== Debug Complete ===")
