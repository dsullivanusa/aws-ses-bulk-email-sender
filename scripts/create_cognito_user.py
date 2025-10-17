#!/usr/bin/env python3
"""
Create a user in Cognito User Pool
"""

import boto3
import json
import sys

def create_user(email, full_name, temporary_password=None):
    """Create a new Cognito user"""
    
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
        print(f"\nCreating user: {email}")
        print(f"Full name: {full_name}")
        
        # Create user
        response = client.admin_create_user(
            UserPoolId=config['user_pool_id'],
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': full_name},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword=temporary_password,
            MessageAction='SUPPRESS' if temporary_password else 'RESEND',
            DesiredDeliveryMediums=['EMAIL'] if not temporary_password else []
        )
        
        print(f"\n✅ User created successfully!")
        print(f"Email: {email}")
        print(f"Name: {full_name}")
        
        if temporary_password:
            print(f"Temporary Password: {temporary_password}")
            print(f"\n⚠️  User must change password on first login")
        else:
            print(f"\n📧 Invitation email sent to: {email}")
        
        return True
        
    except client.exceptions.UsernameExistsException:
        print(f"❌ Error: User {email} already exists")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: python create_cognito_user.py <email> <full_name> [temporary_password]")
        print("\nExamples:")
        print("  python create_cognito_user.py admin@example.com 'Admin User'")
        print("  python create_cognito_user.py john@example.com 'John Smith' 'TempPass123!'")
        sys.exit(1)
    
    email = sys.argv[1]
    full_name = sys.argv[2]
    temp_password = sys.argv[3] if len(sys.argv) > 3 else None
    
    create_user(email, full_name, temp_password)

if __name__ == '__main__':
    main()

