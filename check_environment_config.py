#!/usr/bin/env python3
"""
Check Environment Configuration
This script checks the current Lambda environment variables
"""

import boto3
import json

def check_lambda_environment():
    """Check the current Lambda environment variables"""
    print("🔍 Checking Lambda environment configuration...")
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Get function configuration
        response = lambda_client.get_function(FunctionName='bulk-email-api')
        config = response['Configuration']
        env_vars = config.get('Environment', {}).get('Variables', {})
        
        print(f"✅ Function: {config['FunctionName']}")
        print(f"   Runtime: {config['Runtime']}")
        print(f"   Last Modified: {config['LastModified']}")
        
        print(f"\n📋 Environment Variables:")
        if env_vars:
            for key, value in env_vars.items():
                print(f"   {key} = {value}")
        else:
            print("   No environment variables set")
        
        # Check specifically for CUSTOM_API_URL
        custom_api_url = env_vars.get('CUSTOM_API_URL')
        if custom_api_url:
            print(f"\n✅ CUSTOM_API_URL is set to: {custom_api_url}")
            
            if custom_api_url == "https://jcdcmail.cisa.dhs.gov":
                print("✅ Custom domain is correctly configured!")
                return True
            else:
                print(f"⚠️  Custom domain URL is: {custom_api_url}")
                print("   Expected: https://jcdcmail.cisa.dhs.gov")
                return False
        else:
            print("\n❌ CUSTOM_API_URL is not set")
            print("   The function will use the default API Gateway URL")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Lambda environment: {e}")
        return False

def show_how_api_url_works():
    """Show how the API_URL is determined in the code"""
    print("\n🔍 How API_URL is determined in the code:")
    print("=" * 50)
    
    print("1. The Lambda function checks for CUSTOM_API_URL environment variable")
    print("2. If CUSTOM_API_URL is set, it uses that value")
    print("3. If not set, it uses the API Gateway URL")
    print("4. The value is then injected into the JavaScript as:")
    print("   const API_URL = 'https://jcdcmail.cisa.dhs.gov';")
    
    print("\n📝 Code logic:")
    print("   if CUSTOM_API_URL:")
    print("       api_url = CUSTOM_API_URL")
    print("   else:")
    print("       api_id = event.get('requestContext', {}).get('apiId', 'UNKNOWN')")
    print("       api_url = f'https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod'")

def main():
    """Main function"""
    print("🚀 Environment Configuration Checker")
    print("=" * 40)
    
    # Check current environment
    env_ok = check_lambda_environment()
    
    # Show how it works
    show_how_api_url_works()
    
    print("\n" + "=" * 40)
    if env_ok:
        print("🎉 Environment is correctly configured!")
        print("   The web UI will use: https://jcdcmail.cisa.dhs.gov")
    else:
        print("❌ Environment needs to be configured")
        print("\nTo fix this, run:")
        print("   python setup_custom_domain.py")

if __name__ == '__main__':
    main()
