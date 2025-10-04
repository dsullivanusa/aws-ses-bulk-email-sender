#!/usr/bin/env python3
"""
Disable Cognito Authentication for Web UI
Returns to simple user name field
"""

import json

def disable_cognito():
    """Disable Cognito authentication"""
    try:
        with open('cognito_config.json', 'r') as f:
            config = json.load(f)
        
        config['enabled'] = False
        
        with open('cognito_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("="*70)
        print("⚠️  COGNITO AUTHENTICATION DISABLED")
        print("="*70)
        print("\nCognito configuration:")
        print(f"  User Pool ID: {config['user_pool_id']}")
        print(f"  App Client ID: {config['app_client_id']}")
        print(f"  Status: DISABLED")
        print()
        print("Next step: Deploy the Lambda function")
        print("  python update_lambda.py")
        print()
        print("Users will now use simple name field (no login required)")
        print("="*70)
        
    except FileNotFoundError:
        print("⚠️  No Cognito configuration found")
        print("Authentication is already disabled (default)")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    disable_cognito()

