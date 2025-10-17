#!/usr/bin/env python3
"""
Setup AWS Cognito User Pool for Web UI Authentication
Creates user pool, app client, and domain for login
"""

import boto3
import json
import sys

REGION = 'us-gov-west-1'
USER_POOL_NAME = 'BulkEmailCampaignUsers'
APP_CLIENT_NAME = 'BulkEmailWebUI'
DOMAIN_PREFIX = 'bulk-email-auth'  # Change if needed

def create_cognito_user_pool():
    """Create Cognito User Pool"""
    client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        print("="*70)
        print("AWS Cognito User Pool Setup")
        print("="*70)
        print()
        
        # Create User Pool
        print("Creating User Pool...")
        response = client.create_user_pool(
            PoolName=USER_POOL_NAME,
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            },
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],
            UsernameConfiguration={
                'CaseSensitive': False
            },
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                },
                {
                    'Name': 'name',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                }
            ],
            AccountRecoverySetting={
                'RecoveryMechanisms': [
                    {
                        'Priority': 1,
                        'Name': 'verified_email'
                    }
                ]
            }
        )
        
        user_pool_id = response['UserPool']['Id']
        print(f"✅ User Pool Created: {user_pool_id}")
        
        # Create App Client
        print("\nCreating App Client...")
        app_response = client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=APP_CLIENT_NAME,
            GenerateSecret=False,  # For web apps
            RefreshTokenValidity=30,
            AccessTokenValidity=1,
            IdTokenValidity=1,
            TokenValidityUnits={
                'AccessToken': 'hours',
                'IdToken': 'hours',
                'RefreshToken': 'days'
            },
            ReadAttributes=['email', 'name'],
            WriteAttributes=['email', 'name'],
            ExplicitAuthFlows=[
                'ALLOW_USER_SRP_AUTH',
                'ALLOW_REFRESH_TOKEN_AUTH'
            ],
            PreventUserExistenceErrors='ENABLED'
        )
        
        app_client_id = app_response['UserPoolClient']['ClientId']
        print(f"✅ App Client Created: {app_client_id}")
        
        # Create Cognito Domain
        print("\nCreating Cognito Domain...")
        try:
            domain_response = client.create_user_pool_domain(
                Domain=DOMAIN_PREFIX,
                UserPoolId=user_pool_id
            )
            cognito_domain = f"{DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com"
            print(f"✅ Domain Created: {cognito_domain}")
        except client.exceptions.ResourceNotFoundException as e:
            print(f"⚠️  Domain may already exist: {str(e)}")
            cognito_domain = f"{DOMAIN_PREFIX}.auth.{REGION}.amazoncognito.com"
        
        # Save configuration
        config = {
            'user_pool_id': user_pool_id,
            'app_client_id': app_client_id,
            'region': REGION,
            'cognito_domain': cognito_domain,
            'enabled': False  # Disabled by default
        }
        
        with open('cognito_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("\n" + "="*70)
        print("✅ COGNITO SETUP COMPLETE!")
        print("="*70)
        print(f"\nUser Pool ID:    {user_pool_id}")
        print(f"App Client ID:   {app_client_id}")
        print(f"Region:          {REGION}")
        print(f"Cognito Domain:  {cognito_domain}")
        print(f"\nConfiguration saved to: cognito_config.json")
        print("\nStatus: DISABLED (enable with: python enable_cognito_auth.py)")
        print()
        print("="*70)
        print("NEXT STEPS:")
        print("="*70)
        print("1. Create test user:")
        print(f"   python create_cognito_user.py admin@example.com 'Admin User'")
        print()
        print("2. Enable Cognito authentication:")
        print("   python enable_cognito_auth.py")
        print()
        print("3. Deploy updated Lambda:")
        print("   python update_lambda.py")
        print()
        print("4. Test login at your Web UI")
        print("="*70)
        
        return config
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def main():
    print()
    response = input(f"⚠️  This will create a Cognito User Pool in {REGION}. Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        create_cognito_user_pool()
    else:
        print("Cancelled.")

if __name__ == '__main__':
    main()

