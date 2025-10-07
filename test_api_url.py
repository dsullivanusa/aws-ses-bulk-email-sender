#!/usr/bin/env python3
"""
Test API_URL Generation
This script tests what the API_URL should be when the Lambda function runs
"""

import os

def test_api_url_generation():
    """Test how API_URL is generated"""
    print("🔍 Testing API_URL generation...")
    
    # Simulate the logic from serve_web_ui function
    CUSTOM_API_URL = os.environ.get('CUSTOM_API_URL', None)
    
    if CUSTOM_API_URL:
        api_url = CUSTOM_API_URL
        print(f"✅ Using custom API URL: {api_url}")
    else:
        # Simulate API Gateway URL generation
        api_id = "yi6ss4dsoe"  # From your previous message
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"✅ Using API Gateway URL: {api_url}")
    
    # Test the f-string replacement
    test_js = f"const API_URL = '{api_url}';"
    print(f"✅ Generated JavaScript: {test_js}")
    
    # Check if the URL is valid
    if api_url.startswith('https://') and 'execute-api' in api_url:
        print("✅ API URL format looks correct")
        return True
    else:
        print("❌ API URL format looks incorrect")
        return False

def check_environment_variables():
    """Check relevant environment variables"""
    print("\n🔍 Checking environment variables...")
    
    custom_api_url = os.environ.get('CUSTOM_API_URL')
    if custom_api_url:
        print(f"✅ CUSTOM_API_URL is set: {custom_api_url}")
    else:
        print("ℹ️  CUSTOM_API_URL is not set (will use API Gateway URL)")
    
    return True

def main():
    """Main function"""
    print("🚀 API_URL Test Script")
    print("=" * 30)
    
    # Test API URL generation
    url_ok = test_api_url_generation()
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    print("\n" + "=" * 30)
    if url_ok and env_ok:
        print("🎉 API_URL generation test passed!")
        print("\nThe API_URL should be properly defined in the JavaScript.")
        print("If you're still getting 'API_URL is not defined' error,")
        print("the issue is likely in the JavaScript syntax or f-string processing.")
    else:
        print("❌ API_URL generation test failed")
        print("   Please check the error messages above")

if __name__ == '__main__':
    main()
