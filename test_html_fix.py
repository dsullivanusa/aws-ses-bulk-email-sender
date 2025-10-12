#!/usr/bin/env python3
"""
Test HTML Template Fix in Lambda Function
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def test_web_ui_html():
    """Test the web UI HTML generation"""
    print("🧪 Testing Web UI HTML Generation...")
    
    # Test event for the root path (serves HTML)
    test_event = {
        'httpMethod': 'GET',
        'resource': '/',
        'path': '/',
        'queryStringParameters': None,
        'pathParameters': None,
        'headers': {
            'Accept': 'text/html'
        },
        'body': None,
        'requestContext': {
            'apiId': 'test-api-12345',
            'stage': 'prod',
            'identity': {
                'sourceIp': '127.0.0.1'
            }
        }
    }
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Status Code: {status_code}")
        
        if status_code == 200:
            print("✅ SUCCESS! HTML generated successfully")
            
            # Check if the response contains HTML
            body = payload.get('body', '')
            if '<!DOCTYPE html>' in body:
                print("✅ Valid HTML structure detected")
                
                # Check if API_URL was properly substituted
                if 'const API_URL = \'https://test-api-12345.execute-api.us-gov-west-1.amazonaws.com/prod\';' in body:
                    print("✅ API URL properly substituted in JavaScript")
                elif 'const API_URL = \'{api_url}\';' in body:
                    print("❌ API URL not substituted - template issue")
                elif '{{api_url}}' in body:
                    print("❌ Double braces still present - template issue")
                else:
                    print("⚠️  API URL substitution unclear - checking...")
                    # Look for the API_URL line
                    lines = body.split('\n')
                    for i, line in enumerate(lines):
                        if 'const API_URL' in line:
                            print(f"   Found API_URL line {i+1}: {line.strip()}")
                            break
                
                # Check HTML size
                html_size_kb = len(body) / 1024
                print(f"📏 HTML size: {html_size_kb:.1f} KB")
                
                if html_size_kb > 100:
                    print("⚠️  Large HTML file - this is normal for the full UI")
                
            else:
                print("❌ Response doesn't contain HTML")
                print(f"   Body preview: {body[:200]}...")
                
        elif status_code == 500:
            print("❌ 500 Error - Internal Server Error")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"   Error: {error_message}")
            
            if 'format' in error_message.lower():
                print("🔴 Format string error - HTML template issue")
            elif 'recursion' in error_message.lower():
                print("🔴 Recursion error - likely double .format() call")
            elif 'keyerror' in error_message.lower():
                print("🔴 KeyError - missing template variable")
                
        else:
            print(f"⚠️  Unexpected status: {status_code}")
            print(f"   Response: {payload.get('body', 'No body')[:200]}...")
            
    except Exception as e:
        print(f"❌ Lambda invocation failed: {str(e)}")

def test_api_endpoints():
    """Test that API endpoints still work after HTML fix"""
    print("\n🧪 Testing API Endpoints...")
    
    # Test /config endpoint
    test_event = {
        'httpMethod': 'GET',
        'resource': '/config',
        'path': '/config',
        'queryStringParameters': None,
        'pathParameters': None,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': None,
        'requestContext': {
            'apiId': 'test-api',
            'stage': 'prod'
        }
    }
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 /config endpoint status: {status_code}")
        
        if status_code in [200, 404]:  # 404 is OK if no config exists yet
            print("✅ API endpoints working correctly")
        else:
            print(f"⚠️  API endpoint issue: {status_code}")
            
    except Exception as e:
        print(f"❌ API test failed: {str(e)}")

def main():
    """Run HTML fix tests"""
    print("🔧 Testing Lambda HTML Template Fix")
    print("="*60)
    
    # Test HTML generation
    test_web_ui_html()
    
    # Test API endpoints still work
    test_api_endpoints()
    
    print("\n" + "="*60)
    print("✅ HTML Testing Complete")
    print("\nIf HTML is working correctly:")
    print("1. ✅ Status code should be 200")
    print("2. ✅ API_URL should be properly substituted")
    print("3. ✅ No format recursion errors")
    print("\nIf still having issues:")
    print("1. Check CloudWatch logs for specific error details")
    print("2. Verify the .format() call is single, not double")
    print("3. Ensure template uses {api_url} not {{api_url}}")

if __name__ == '__main__':
    main()