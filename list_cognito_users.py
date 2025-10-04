#!/usr/bin/env python3
"""
List all users in Cognito User Pool
"""

import boto3
import json

def list_users():
    """List all Cognito users"""
    
    # Load Cognito config
    try:
        with open('cognito_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ Error: cognito_config.json not found")
        print("Run: python setup_cognito_auth.py first")
        return
    
    client = boto3.client('cognito-idp', region_name=config['region'])
    
    try:
        print("\n" + "="*80)
        print("COGNITO USERS")
        print("="*80)
        print(f"\nUser Pool: {config['user_pool_id']}")
        print()
        
        response = client.list_users(
            UserPoolId=config['user_pool_id']
        )
        
        users = response.get('Users', [])
        
        if not users:
            print("No users found.")
            return
        
        print(f"Total Users: {len(users)}\n")
        print(f"{'Email':<40} {'Name':<30} {'Status':<15} {'Verified'}")
        print("-"*110)
        
        for user in users:
            email = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), 'N/A')
            name = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'name'), 'N/A')
            email_verified = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email_verified'), 'false')
            status = user['UserStatus']
            
            print(f"{email:<40} {name:<30} {status:<15} {email_verified}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    list_users()

