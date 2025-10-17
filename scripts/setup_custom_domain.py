#!/usr/bin/env python3
"""
Setup Custom Domain Configuration
This script helps configure the Lambda function to use jcdcmail.cisa.dhs.gov
"""

import boto3
import json

def set_custom_api_url():
    """Set the CUSTOM_API_URL environment variable for the Lambda function"""
    print("🔧 Setting up custom domain configuration...")
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Get current function configuration
        response = lambda_client.get_function(FunctionName='bulk-email-api-function')
        current_config = response['Configuration']
        current_env = current_config.get('Environment', {}).get('Variables', {})
        
        print(f"✅ Current function: {current_config['FunctionName']}")
        print(f"   Runtime: {current_config['Runtime']}")
        
        # Set the custom API URL
        custom_api_url = "https://jcdcmail.cisa.dhs.gov"
        current_env['CUSTOM_API_URL'] = custom_api_url
        
        print(f"✅ Setting CUSTOM_API_URL to: {custom_api_url}")
        
        # Update the function configuration
        update_response = lambda_client.update_function_configuration(
            FunctionName='bulk-email-api-function',
            Environment={
                'Variables': current_env
            }
        )
        
        print("✅ Lambda function configuration updated successfully!")
        print(f"   Function ARN: {update_response['FunctionArn']}")
        print(f"   Last Modified: {update_response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda configuration: {e}")
        return False

def verify_custom_domain_setup():
    """Verify the custom domain is properly configured"""
    print("\n🔍 Verifying custom domain configuration...")
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Get updated function configuration
        response = lambda_client.get_function(FunctionName='bulk-email-api-function')
        config = response['Configuration']
        env_vars = config.get('Environment', {}).get('Variables', {})
        
        custom_api_url = env_vars.get('CUSTOM_API_URL')
        
        if custom_api_url:
            print(f"✅ CUSTOM_API_URL is set to: {custom_api_url}")
            
            if custom_api_url == "https://jcdcmail.cisa.dhs.gov":
                print("✅ Custom domain configuration is correct!")
                return True
            else:
                print(f"❌ Custom domain URL is incorrect: {custom_api_url}")
                return False
        else:
            print("❌ CUSTOM_API_URL is not set")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying configuration: {e}")
        return False

def test_custom_domain():
    """Test if the custom domain is accessible"""
    print("\n🔍 Testing custom domain accessibility...")
    
    import requests
    
    custom_domain = "https://jcdcmail.cisa.dhs.gov"
    
    try:
        print(f"   Testing: {custom_domain}")
        response = requests.get(custom_domain, timeout=10)
        
        if response.status_code == 200:
            print("✅ Custom domain is accessible!")
            print(f"   Status Code: {response.status_code}")
            return True
        else:
            print(f"⚠️  Custom domain returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Custom domain is not accessible: {e}")
        print("   This might be expected if the domain is not yet configured")
        return False

def main():
    """Main function"""
    print("🚀 Custom Domain Setup Script")
    print("=" * 40)
    
    # Set the custom API URL
    setup_ok = set_custom_api_url()
    
    if setup_ok:
        # Verify the configuration
        verify_ok = verify_custom_domain_setup()
        
        # Test the custom domain
        test_ok = test_custom_domain()
        
        print("\n" + "=" * 40)
        if verify_ok:
            print("🎉 CUSTOM DOMAIN CONFIGURATION COMPLETE!")
            print(f"\n✅ Lambda function is now configured to use: jcdcmail.cisa.dhs.gov")
            print("\nNext steps:")
            print("1. Ensure your custom domain is properly configured in API Gateway")
            print("2. Test the web UI at: https://jcdcmail.cisa.dhs.gov")
            print("3. The JavaScript will now use the custom domain instead of API Gateway URL")
            
            if not test_ok:
                print("\n⚠️  Note: Custom domain is not yet accessible")
                print("   This is normal if the domain configuration is still in progress")
        else:
            print("❌ Custom domain configuration failed")
            print("   Please check the error messages above")
    else:
        print("\n❌ Could not set up custom domain configuration")

if __name__ == '__main__':
    main()
