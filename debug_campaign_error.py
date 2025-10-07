#!/usr/bin/env python3
"""
Debug Campaign Error - "Unexpected token <"
This script helps diagnose why the Send Campaign API is returning HTML instead of JSON
"""

import requests
import json
import sys

# Your API Gateway URL
API_URL = "https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod"

def test_campaign_endpoint():
    """Test the campaign endpoint to see what it returns"""
    
    print("=" * 80)
    print("🔍 Debugging Campaign API Error")
    print("=" * 80)
    
    # Test data
    test_campaign = {
        "campaign_name": "Test Campaign",
        "subject": "Test Subject",
        "body": "Test body content",
        "target_contacts": ["test@example.com"],
        "filter_description": "Test Filter"
    }
    
    print(f"\n📋 Testing Campaign Endpoint:")
    print(f"   URL: {API_URL}/campaign")
    print(f"   Method: POST")
    print(f"   Payload: {json.dumps(test_campaign, indent=2)}")
    
    try:
        # Make the request
        response = requests.post(
            f"{API_URL}/campaign",
            headers={'Content-Type': 'application/json'},
            json=test_campaign,
            timeout=30
        )
        
        print(f"\n📊 Response Details:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
        print(f"   Content-Length: {len(response.content)} bytes")
        
        # Check if response is HTML or JSON
        content_type = response.headers.get('content-type', '').lower()
        
        if 'application/json' in content_type:
            print(f"\n✅ Response is JSON (as expected)")
            try:
                data = response.json()
                print(f"   JSON Response: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON Parse Error: {str(e)}")
                print(f"   Raw Response: {response.text[:500]}...")
        else:
            print(f"\n❌ Response is NOT JSON!")
            print(f"   Content-Type: {content_type}")
            print(f"   Raw Response (first 500 chars):")
            print(f"   {response.text[:500]}...")
            
            # Check if it's an HTML error page
            if '<html' in response.text.lower() or '<!doctype' in response.text.lower():
                print(f"\n🚨 This is an HTML error page!")
                print(f"   Likely causes:")
                print(f"   1. API Gateway error (500, 502, 503)")
                print(f"   2. Lambda function crashed")
                print(f"   3. CORS issue")
                print(f"   4. Authentication/authorization error")
        
        # Check for common error patterns
        if response.status_code >= 400:
            print(f"\n⚠️  HTTP Error Status: {response.status_code}")
            
            if response.status_code == 500:
                print(f"   Internal Server Error - Lambda function likely crashed")
            elif response.status_code == 502:
                print(f"   Bad Gateway - API Gateway couldn't reach Lambda")
            elif response.status_code == 503:
                print(f"   Service Unavailable - Lambda function unavailable")
            elif response.status_code == 400:
                print(f"   Bad Request - Check request format")
            elif response.status_code == 403:
                print(f"   Forbidden - Check IAM permissions")
        
        return response
        
    except requests.exceptions.Timeout:
        print(f"\n⏰ Request timed out after 30 seconds")
        print(f"   This suggests the Lambda function is taking too long to respond")
        return None
        
    except requests.exceptions.ConnectionError:
        print(f"\n🔌 Connection error")
        print(f"   Check if the API Gateway URL is correct")
        return None
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return None

def test_other_endpoints():
    """Test other endpoints to see if they work"""
    
    print(f"\n" + "=" * 80)
    print(f"🔍 Testing Other Endpoints")
    print(f"=" * 80)
    
    endpoints = [
        ("/", "GET", "Main web UI"),
        ("/contacts?limit=1", "GET", "Contacts endpoint"),
        ("/groups", "GET", "Groups endpoint")
    ]
    
    for endpoint, method, description in endpoints:
        print(f"\n📋 Testing {description}:")
        print(f"   {method} {API_URL}{endpoint}")
        
        try:
            if method == "GET":
                response = requests.get(f"{API_URL}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{API_URL}{endpoint}", timeout=10)
            
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
            
            if response.status_code == 200:
                print(f"   ✅ Working")
            else:
                print(f"   ❌ Error")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def check_lambda_logs():
    """Provide instructions for checking Lambda logs"""
    
    print(f"\n" + "=" * 80)
    print(f"📋 Next Steps to Debug")
    print(f"=" * 80)
    
    print(f"\n1. Check Lambda Logs:")
    print(f"   python view_lambda_errors.py bulk-email-api-function 1")
    print(f"   python tail_lambda_logs.py bulk-email-api-function")
    
    print(f"\n2. Check API Gateway Logs:")
    print(f"   - Go to API Gateway Console")
    print(f"   - Find your API")
    print(f"   - Check CloudWatch Logs")
    
    print(f"\n3. Test with curl:")
    print(f"   curl -X POST '{API_URL}/campaign' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"campaign_name\":\"test\",\"subject\":\"test\",\"body\":\"test\",\"target_contacts\":[\"test@example.com\"]}}'")
    
    print(f"\n4. Common Fixes:")
    print(f"   - Deploy the latest Lambda function")
    print(f"   - Check IAM permissions")
    print(f"   - Verify DynamoDB tables exist")
    print(f"   - Check SQS queue exists")

def main():
    """Main function"""
    
    print(f"🚀 Starting Campaign API Debug...")
    
    # Test the campaign endpoint
    response = test_campaign_endpoint()
    
    # Test other endpoints
    test_other_endpoints()
    
    # Provide next steps
    check_lambda_logs()
    
    print(f"\n" + "=" * 80)
    print(f"✅ Debug Complete!")
    print(f"=" * 80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
