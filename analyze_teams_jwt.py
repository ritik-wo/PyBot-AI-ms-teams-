#!/usr/bin/env python3

import jwt
import json
from datetime import datetime

def analyze_teams_jwt():
    """Analyze the JWT token from Teams to see what's wrong"""
    
    # This is the actual JWT token from your Teams logs
    teams_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjZ3R0VoTTBwdEhyZENreGNNbDVlT3JTMC1XayIsIng1dCI6IjZ3R0VoTTBwdEhyZENreGNNbDVlT3JTMC1XayIsInR5cCI6IkpXVCJ9.ew0KICAic2VydmljZXVybCI6ICJodHRwczovL3NtYmEudHJhZmZpY21hbmFnZXIubmV0L2RlLzE3MDY1ZWQ1LTA1YmEtNGZjMi1iNThhLTFmYjE5OTE0MmY1OS8iLA0KICAibmJmIjogMTc1MzA5NTcxOCwNCiAgImV4cCI6IDE3NTMwOTkzMTgsDQogICJpc3MiOiAiaHR0cHM6Ly9hcGkuYm90ZnJhbWV3b3JrLmNvbSIsDQogICJhdWQiOiAiMjg1MWI1ODQtNzAyNS00N2NlLWJhNjctNWRkMTkyMmNlMGFkIg0KfQ.E5aRZdCYf0ATE6-k6X4LpS27QkBVzDjG7_A6sAB13CBxI3GAvfYRrWswbOTs8X3G1fgcsS65D-mv3zLH5yC1UiMnavMCbsg3XrYdOiiNqXs_LxEZ6I0NTsya0IXijqe-845rzW39KBBoMnbripNtp_cdjDV4f8q0qFunfs_29TfW-zaaUC4UhNBptU5W476-0MCQWknmB2B8nzB68XLlsS-iiT_2R_gJjPd2Nn7XA5zekmDQrxhUMnUF1JzboAWcc5W4udUl5DclB27uTuFG4Vc6soW7N5gKzHJBThU1VZjTL4FRCOATrGZ-cqh0vPb7zQpu8M_1DNWMy781jv_ZZw"
    
    print("=== TEAMS JWT TOKEN ANALYSIS ===\n")
    
    try:
        # Decode without verification first to see the payload
        print("🔍 Decoding JWT without verification...")
        decoded = jwt.decode(teams_token, options={"verify_signature": False})
        print("✅ JWT decoding successful!")
        print("\n📋 JWT Payload:")
        print(json.dumps(decoded, indent=2))
        
        # Check expiration
        if 'exp' in decoded:
            exp_time = datetime.fromtimestamp(decoded['exp'])
            current_time = datetime.now()
            print(f"\n⏰ Token expiration: {exp_time}")
            print(f"⏰ Current time: {current_time}")
            if exp_time < current_time:
                print("❌ TOKEN IS EXPIRED!")
                return False
            else:
                print("✅ Token is still valid")
        
        # Check audience
        if 'aud' in decoded:
            audience = decoded['aud']
            expected_app_id = "2851b584-7025-47ce-ba67-5dd1922ce0ad"
            print(f"\n🎯 Token audience: {audience}")
            print(f"🎯 Expected app ID: {expected_app_id}")
            if audience == expected_app_id:
                print("✅ Audience matches your App ID")
            else:
                print("❌ AUDIENCE MISMATCH!")
                return False
        
        # Check issuer
        if 'iss' in decoded:
            issuer = decoded['iss']
            print(f"\n🏛️ Token issuer: {issuer}")
            if issuer == "https://api.botframework.com":
                print("✅ Correct Bot Framework issuer")
            else:
                print("❌ Unexpected issuer")
        
        # Check service URL
        if 'serviceurl' in decoded:
            service_url = decoded['serviceurl']
            print(f"\n🌐 Service URL: {service_url}")
            print("✅ This is the Teams service URL for your bot")
        
        return True
        
    except jwt.DecodeError as e:
        print(f"❌ JWT DECODE ERROR: {e}")
        print("🔍 The token format might be corrupted")
        return False
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

def analyze_issue():
    """Analyze what we know so far"""
    
    print("\n" + "="*60)
    print("🎯 COMPREHENSIVE ANALYSIS")
    print("="*60)
    
    print("\n✅ WHAT WE KNOW:")
    print("1. Your bot credentials work (debug script confirmed)")
    print("2. Teams CAN send messages to your bot")
    print("3. Your bot CAN receive and process Teams messages")
    print("4. The JWT token from Teams appears valid")
    print("5. The error happens when your bot tries to RESPOND")
    
    print("\n❓ THE MYSTERY:")
    print("1. Teams authentication works (incoming)")
    print("2. But outbound authentication fails (your bot → Teams)")
    print("3. Error: 'Operation returned an invalid status code Unauthorized'")
    
    print("\n🔧 LIKELY CAUSES:")
    print("1. **Service URL Authentication Issue**")
    print("   → Your bot can't authenticate with the specific Teams service URL")
    print("   → https://smba.trafficmanager.net/de/17065ed5-05ba-4fc2-b58a-1fb199142f59/")
    print()
    print("2. **Scope/Audience Mismatch**") 
    print("   → Your bot credentials work for botframework.com")
    print("   → But not for the specific Teams tenant service")
    print()
    print("3. **Azure Bot Registration Issue**")
    print("   → Teams channel not properly configured")
    print("   → Missing permissions for Teams service URLs")

if __name__ == "__main__":
    token_valid = analyze_teams_jwt()
    analyze_issue()
    
    if token_valid:
        print("\n🎯 RECOMMENDED NEXT STEPS:")
        print("1. The Teams JWT token is valid")
        print("2. The issue is with your bot authenticating OUTBOUND")
        print("3. Check Azure Bot Registration → Channels → Teams")
        print("4. Verify your bot has permission to send to Teams service URLs")
        print("5. Try regenerating credentials one more time")
    else:
        print("\n🎯 TOKEN ISSUE FOUND:")
        print("The Teams JWT token has problems that need to be addressed first")
