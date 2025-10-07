#!/usr/bin/env python3
"""
Test API_URL Injection
This script tests how the API_URL is injected into the JavaScript
"""

import re

def test_api_url_injection():
    """Test how API_URL is injected into the JavaScript"""
    print("🔍 Testing API_URL injection...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the serve_web_ui function
        serve_web_ui_match = re.search(r'def serve_web_ui\(event\):.*?api_url = (.*?)\n', content, re.DOTALL)
        if serve_web_ui_match:
            api_url_definition = serve_web_ui_match.group(1).strip()
            print(f"✅ Found API URL definition: {api_url_definition}")
            
            # Check if it's using CUSTOM_API_URL
            if 'CUSTOM_API_URL' in api_url_definition:
                print("✅ Using CUSTOM_API_URL environment variable")
            else:
                print("⚠️  Not using CUSTOM_API_URL (will use API Gateway URL)")
        else:
            print("❌ serve_web_ui function not found")
            return False
        
        # Find the HTML template
        html_start = content.find('html_content = f"""')
        if html_start == -1:
            print("❌ HTML template not found")
            return False
        
        # Find the API_URL definition in the JavaScript
        api_url_js_match = re.search(r"const API_URL = '{api_url}';", content)
        if api_url_js_match:
            print("✅ Found API_URL JavaScript definition with f-string placeholder")
        else:
            print("❌ API_URL JavaScript definition not found")
            return False
        
        # Test the f-string replacement
        test_api_url = "https://jcdcmail.cisa.dhs.gov"
        test_js = f"const API_URL = '{test_api_url}';"
        print(f"✅ Test JavaScript output: {test_js}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API_URL injection: {e}")
        return False

def check_environment_variable():
    """Check if CUSTOM_API_URL environment variable is set"""
    print("\n🔍 Checking CUSTOM_API_URL environment variable...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for CUSTOM_API_URL usage
        if 'CUSTOM_API_URL' in content:
            print("✅ CUSTOM_API_URL is referenced in the code")
            
            # Check how it's used
            custom_url_matches = re.findall(r'CUSTOM_API_URL.*?=.*?([^\n]+)', content)
            if custom_url_matches:
                print(f"✅ CUSTOM_API_URL usage: {custom_url_matches[0].strip()}")
        else:
            print("❌ CUSTOM_API_URL is not referenced in the code")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking environment variable: {e}")
        return False

def main():
    """Main function"""
    print("🚀 API_URL Injection Test Script")
    print("=" * 40)
    
    # Test API_URL injection
    injection_ok = test_api_url_injection()
    
    # Check environment variable
    env_ok = check_environment_variable()
    
    print("\n" + "=" * 40)
    if injection_ok and env_ok:
        print("🎉 API_URL injection test passed!")
        print("\nThe API_URL should be properly injected into the JavaScript.")
        print("If you're still getting 'API_URL is not defined' error,")
        print("the issue is likely JavaScript syntax errors preventing execution.")
        print("\nRun this script to fix syntax errors:")
        print("   python fix_api_url_undefined.py")
    else:
        print("❌ API_URL injection test failed")
        print("   Please check the error messages above")

if __name__ == '__main__':
    main()
