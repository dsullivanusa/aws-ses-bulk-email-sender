#!/usr/bin/env python3
"""
Diagnose Web UI Issues
Checks if the web UI, tabs, and DynamoDB fetching are working properly
"""

import requests
import json
import sys

API_URL = "https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod"

def test_web_ui():
    """Test if the main web UI loads"""
    
    print("=" * 80)
    print("🔍 Testing Web UI")
    print("=" * 80)
    
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            if '<html' in response.text.lower():
                print("✅ Web UI loads successfully")
                
                # Check for key elements
                if 'tab-content' in response.text:
                    print("✅ Tab structure found")
                else:
                    print("❌ Tab structure missing")
                
                if 'loadContacts' in response.text:
                    print("✅ JavaScript functions found")
                else:
                    print("❌ JavaScript functions missing")
                
                if 'API_URL' in response.text:
                    print("✅ API URL configuration found")
                else:
                    print("❌ API URL configuration missing")
                    
            else:
                print("❌ Response is not HTML")
                print(f"First 200 chars: {response.text[:200]}")
        else:
            print(f"❌ Web UI failed to load: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error loading web UI: {e}")

def test_contacts_endpoint():
    """Test the contacts endpoint"""
    
    print(f"\n" + "=" * 80)
    print("🔍 Testing Contacts Endpoint")
    print("=" * 80)
    
    try:
        response = requests.get(f"{API_URL}/contacts?limit=5", timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                contacts = data.get('contacts', [])
                print(f"✅ Contacts endpoint working")
                print(f"   Found {len(contacts)} contacts")
                
                if contacts:
                    print(f"   Sample contact: {contacts[0].get('email', 'N/A')}")
                else:
                    print("   ⚠️  No contacts found in database")
            else:
                print("❌ Response is not JSON")
                print(f"Response: {response.text[:200]}")
        else:
            print(f"❌ Contacts endpoint failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error testing contacts: {e}")

def test_other_endpoints():
    """Test other API endpoints"""
    
    print(f"\n" + "=" * 80)
    print("🔍 Testing Other Endpoints")
    print("=" * 80)
    
    endpoints = [
        ("/config", "GET", "Email Config"),
        ("/groups", "GET", "Groups"),
        ("/contacts/distinct?field=group", "GET", "Distinct Groups")
    ]
    
    for endpoint, method, name in endpoints:
        print(f"\n📋 Testing {name}:")
        try:
            if method == "GET":
                response = requests.get(f"{API_URL}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{API_URL}{endpoint}", timeout=10)
            
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            
            if response.status_code == 200:
                print(f"   ✅ {name} working")
            else:
                print(f"   ❌ {name} failed")
                print(f"   Response: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ {name} error: {e}")

def test_lambda_function():
    """Test if Lambda function is responding"""
    
    print(f"\n" + "=" * 80)
    print("🔍 Testing Lambda Function Health")
    print("=" * 80)
    
    # Test with a simple request
    try:
        response = requests.get(f"{API_URL}/contacts?limit=1", timeout=15)
        
        print(f"Lambda Response Time: {response.elapsed.total_seconds():.2f} seconds")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Lambda function is responding")
        elif response.status_code == 500:
            print("❌ Lambda function has internal error")
        elif response.status_code == 502:
            print("❌ Lambda function is not responding (Bad Gateway)")
        elif response.status_code == 503:
            print("❌ Lambda function is unavailable")
        else:
            print(f"❌ Lambda function returned unexpected status: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ Lambda function timeout (>15 seconds)")
    except Exception as e:
        print(f"❌ Lambda function error: {e}")

def provide_solutions():
    """Provide solutions based on findings"""
    
    print(f"\n" + "=" * 80)
    print("💡 Solutions")
    print("=" * 80)
    
    print(f"\n🔧 If Web UI doesn't load:")
    print(f"   1. Redeploy Lambda function:")
    print(f"      python deploy_bulk_email_api.py")
    print(f"   2. Check Lambda logs:")
    print(f"      python view_lambda_errors.py bulk-email-api-function 1")
    
    print(f"\n🔧 If DynamoDB fetching fails:")
    print(f"   1. Check DynamoDB tables exist:")
    print(f"      python setup_all_tables.py")
    print(f"   2. Check IAM permissions:")
    print(f"      python create_iam_resources.py")
    
    print(f"\n🔧 If tabs don't work:")
    print(f"   1. Check browser console for JavaScript errors (F12)")
    print(f"   2. Clear browser cache and refresh")
    print(f"   3. Try different browser")
    
    print(f"\n🔧 If Lambda function is slow/unresponsive:")
    print(f"   1. Check Lambda memory and timeout settings")
    print(f"   2. Check CloudWatch metrics")
    print(f"   3. Check for infinite loops or blocking operations")

def main():
    """Main function"""
    
    print(f"🚀 Starting Web UI Diagnosis...")
    
    test_web_ui()
    test_contacts_endpoint()
    test_other_endpoints()
    test_lambda_function()
    provide_solutions()
    
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
