#!/usr/bin/env python3
"""
Delete a user from Cognito User Pool
"""

import boto3
import json
import sys

def delete_user(email):
    """Delete Cognito user"""
    
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
        # Confirm deletion
        response = input(f"⚠️  Delete user {email}? This cannot be undone. (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return False
        
        print(f"\n🗑️  Deleting user: {email}")
        
        # Delete user
        client.admin_delete_user(
            UserPoolId=config['user_pool_id'],
            Username=email
        )
        
        print(f"\n✅ User deleted successfully!")
        print(f"Deleted: {email}")
        
        return True
        
    except client.exceptions.UserNotFoundException:
        print(f"❌ Error: User {email} not found")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_cognito_user.py <email>")
        print("\nExample:")
        print("  python delete_cognito_user.py user@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    delete_user(email)

if __name__ == '__main__':
    main()

