#!/usr/bin/env python3

"""
Script to help verify Bot registration settings
"""

def check_bot_registration():
    """Print checklist for Azure Bot Registration"""
    
    print("=== Azure Bot Registration Checklist ===\n")
    
    print("Please verify the following in your Azure Portal:\n")
    
    print("1. **Bot Channels Registration**:")
    print("   - Go to Azure Portal → Your Bot Registration")
    print("   - Check 'Configuration' section")
    print("   - Microsoft App ID should match: 2851b584-7025-47ce-ba67-5dd1922ce0ad")
    print("   - Messaging endpoint should be: https://your-ngrok-url.ngrok-free.app/api/messages")
    print("")
    
    print("2. **App Registration (Microsoft Entra ID)**:")
    print("   - Go to Azure Portal → Microsoft Entra ID → App registrations")
    print("   - Find app: 2851b584-7025-47ce-ba67-5dd1922ce0ad")
    print("   - Check 'Certificates & secrets' section")
    print("   - Ensure your new client secret is active and not expired")
    print("   - Value should start with: JYw8Q~ETbP...")
    print("")
    
    print("3. **API Permissions**:")
    print("   - In the same App Registration → 'API permissions'")
    print("   - Should have: Microsoft Graph permissions (if needed)")
    print("   - Should have: Bot Framework permissions")
    print("   - Check if 'Admin consent' is granted")
    print("")
    
    print("4. **Teams Channel Configuration**:")
    print("   - Back to Bot Channels Registration → 'Channels'")
    print("   - Microsoft Teams channel should be enabled")
    print("   - No additional configuration should be needed for Teams")
    print("")
    
    print("5. **Common Issues to Check**:")
    print("   - ✓ Bot Messaging Endpoint URL is accessible (ngrok running)")
    print("   - ✓ App ID and Password match exactly (no extra spaces)")
    print("   - ✓ Client secret is not expired")
    print("   - ✓ Bot is published and available in Teams")
    print("")
    
    print("6. **Test from Bot Framework Emulator**:")
    print("   - Download Bot Framework Emulator")
    print("   - Test with your local endpoint: http://localhost:3978/api/messages")
    print("   - Use App ID: 2851b584-7025-47ce-ba67-5dd1922ce0ad")
    print("   - Use App Password: JYw8Q~ETbPYjgQ1e37DMva.Cz.yR~MZ7V3RsZaoA")
    print("   - This will help isolate if the issue is Teams-specific or general")
    print("")
    
    print("7. **Potential Fix - Regenerate ALL Credentials**:")
    print("   - Sometimes the simplest fix is to regenerate everything:")
    print("   - Create a new App Registration in Microsoft Entra ID")
    print("   - Create a new Bot Channels Registration")
    print("   - Link them together")
    print("   - Update your code with the new credentials")
    print("")

def check_ngrok_setup():
    """Check if ngrok is configured correctly"""
    
    print("=== ngrok Configuration Check ===\n")
    
    print("Your logs show ngrok URL: 3d39605a02ee.ngrok-free.app")
    print("Make sure:")
    print("1. ngrok is running: ngrok http 3978")
    print("2. The ngrok URL in Azure matches exactly")
    print("3. Your ngrok URL should end with '/api/messages'")
    print("4. Example: https://3d39605a02ee.ngrok-free.app/api/messages")
    print("")

if __name__ == "__main__":
    check_bot_registration()
    check_ngrok_setup()
    
    print("=== Immediate Next Steps ===\n")
    print("1. Verify all the above settings in Azure Portal")
    print("2. Try testing with Bot Framework Emulator first") 
    print("3. If emulator works but Teams doesn't, the issue is Teams-specific")
    print("4. If emulator also fails with 401, the issue is with credentials/permissions")
    print("5. Consider regenerating all credentials as a last resort")
    print("")
    print("The fact that you can get auth tokens means credentials are mostly right,")
    print("but there might be a scope/audience mismatch for the specific Teams service URL.")
