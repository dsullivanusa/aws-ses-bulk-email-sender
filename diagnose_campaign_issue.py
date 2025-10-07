#!/usr/bin/env python3
"""
Diagnose Campaign API Issue
Helps identify why the campaign endpoint returns HTML instead of JSON
"""

import requests
import json
import sys

API_URL = "https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod"

def test_endpoints():
    """Test various endpoints to see what they return"""
    
    print("=" * 80)
    print("🔍 Diagnosing Campaign API Issue")
    print("=" * 80)
    
    # Test 1: Root endpoint (should return HTML)
    print(f"\n1️⃣ Testing Root Endpoint (should return HTML):")
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        if '<html' in response.text.lower():
            print(f"   ✅ Returns HTML (expected)")
        else:
            print(f"   ❌ Does not return HTML")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Campaign endpoint (should return JSON)
    print(f"\n2️⃣ Testing Campaign Endpoint (should return JSON):")
    test_data = {
        "campaign_name": "Test Campaign",
        "subject": "Test Subject",
        "body": "Test body",
        "target_contacts": ["test@example.com"],
        "filter_description": "Test"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/campaign",
            headers={'Content-Type': 'application/json'},
            json=test_data,
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   Response Length: {len(response.text)}")
        
        # Check if it's HTML or JSON
        if '<html' in response.text.lower():
            print(f"   ❌ Returns HTML (unexpected!)")
            print(f"   First 200 chars: {response.text[:200]}...")
        elif 'application/json' in response.headers.get('content-type', ''):
            print(f"   ✅ Returns JSON (expected)")
            try:
                data = response.json()
                print(f"   JSON Response: {json.dumps(data, indent=2)}")
            except:
                print(f"   ❌ Failed to parse JSON")
        else:
            print(f"   ⚠️  Returns neither HTML nor JSON")
            print(f"   First 200 chars: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Other API endpoints
    print(f"\n3️⃣ Testing Other API Endpoints:")
    
    endpoints = [
        ("/contacts?limit=1", "GET", "Contacts"),
        ("/config", "GET", "Config"),
        ("/groups", "GET", "Groups")
    ]
    
    for endpoint, method, name in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{API_URL}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{API_URL}{endpoint}", timeout=10)
            
            print(f"   {name}: Status {response.status_code}, Content-Type: {response.headers.get('content-type')}")
            
            if response.status_code == 200 and 'application/json' in response.headers.get('content-type', ''):
                print(f"   ✅ {name} working correctly")
            else:
                print(f"   ❌ {name} has issues")
                
        except Exception as e:
            print(f"   ❌ {name} error: {e}")

def check_lambda_deployment():
    """Check if Lambda function needs to be redeployed"""
    
    print(f"\n" + "=" * 80)
    print(f"🚀 Lambda Deployment Check")
    print(f"=" * 80)
    
    print(f"\n💡 Possible Issues:")
    print(f"   1. Lambda function not deployed with latest changes")
    print(f"   2. API Gateway routing issue")
    print(f"   3. Lambda function returning wrong content type")
    print(f"   4. Exception in send_campaign function")
    
    print(f"\n🔧 Recommended Actions:")
    print(f"   1. Deploy the Lambda function:")
    print(f"      python deploy_bulk_email_api.py")
    print(f"   2. Check Lambda logs:")
    print(f"      python view_lambda_errors.py bulk-email-api-function 1")
    print(f"   3. Test with curl:")
    print(f"      curl -X POST '{API_URL}/campaign' \\")
    print(f"        -H 'Content-Type: application/json' \\")
    print(f"        -d '{{\"campaign_name\":\"test\",\"subject\":\"test\",\"body\":\"test\",\"target_contacts\":[\"test@example.com\"]}}'")

def main():
    """Main function"""
    
    test_endpoints()
    check_lambda_deployment()
    
    print(f"\n" + "=" * 80)
    print(f"✅ Diagnosis Complete!")
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
