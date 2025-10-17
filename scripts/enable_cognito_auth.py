#!/usr/bin/env python3
"""
Enable Cognito Authentication for Web UI
"""

import json

def enable_cognito():
    """Enable Cognito authentication"""
    try:
        with open('cognito_config.json', 'r') as f:
            config = json.load(f)
        
        config['enabled'] = True
        
        with open('cognito_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("="*70)
        print("✅ COGNITO AUTHENTICATION ENABLED")
        print("="*70)
        print("\nCognito configuration:")
        print(f"  User Pool ID: {config['user_pool_id']}")
        print(f"  App Client ID: {config['app_client_id']}")
        print(f"  Region: {config['region']}")
        print(f"  Status: ENABLED")
        print()
        print("Next step: Deploy the Lambda function")
        print("  python update_lambda.py")
        print()
        print("Users will now be required to log in to access the Web UI")
        print("="*70)
        
    except FileNotFoundError:
        print("❌ Error: cognito_config.json not found")
        print("Run: python setup_cognito_auth.py first")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    enable_cognito()

