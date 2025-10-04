#!/usr/bin/env python3
"""
Reset password for a Cognito user
Sends password reset email to user
"""

import boto3
import json
import sys

def reset_password(email):
    """Reset user password"""
    
    # Load Cognito config
    try:
        with open('cognito_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Error: cognito_config.json not found")
        print("Run: python setup_cognito_auth.py first")
        return False
    
    client = boto3.client('cognito-idp', region_name=config['region'])
    
    try:
        print(f"\n🔄 Resetting password for: {email}")
        
        # Reset password
        client.admin_reset_user_password(
            UserPoolId=config['user_pool_id'],
            Username=email
        )
        
        print(f"\n✅ Password reset initiated!")
        print(f"📧 Reset email sent to: {email}")
        print(f"\nUser must:")
        print(f"  1. Check email for reset code")
        print(f"  2. Use code to set new password")
        print(f"  3. Log in with new password")
        
        return True
        
    except client.exceptions.UserNotFoundException:
        print(f"❌ Error: User {email} not found")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python reset_cognito_password.py <email>")
        print("\nExample:")
        print("  python reset_cognito_password.py user@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    reset_password(email)

if __name__ == '__main__':
    main()

