#!/usr/bin/env python3
"""
Debug Weekly Rollup Filter Issue
Helps diagnose why Weekly Rollup filter doesn't work for Send Campaign
"""

import requests
import json
import sys

API_URL = "https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod"

def test_weekly_rollup_distinct():
    """Test the distinct values endpoint for weekly_rollup"""
    
    print("=" * 80)
    print("🔍 Testing Weekly Rollup Filter")
    print("=" * 80)
    
    print(f"\n1️⃣ Testing Distinct Values for 'weekly_rollup':")
    try:
        response = requests.get(f"{API_URL}/contacts/distinct?field=weekly_rollup", timeout=10)
        
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            data = response.json()
            values = data.get('values', [])
            print(f"   ✅ Found {len(values)} distinct values:")
            for value in values:
                print(f"      - '{value}'")
            
            if 'Yes' not in values and 'No' not in values:
                print(f"   ⚠️  Warning: 'Yes' and 'No' values not found!")
                print(f"   💡 This means no contacts have weekly_rollup set to Yes/No")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_weekly_rollup_filter():
    """Test filtering contacts by weekly_rollup"""
    
    print(f"\n2️⃣ Testing Filter for 'weekly_rollup = Yes':")
    try:
        filter_data = {
            "filters": [
                {
                    "field": "weekly_rollup",
                    "values": ["Yes"]
                }
            ]
        }
        
        response = requests.post(
            f"{API_URL}/contacts/filter",
            headers={'Content-Type': 'application/json'},
            json=filter_data,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('contacts', [])
            print(f"   ✅ Found {len(contacts)} contacts with weekly_rollup = 'Yes'")
            
            if len(contacts) == 0:
                print(f"   ⚠️  No contacts found with weekly_rollup = 'Yes'")
                print(f"   💡 This explains why Send Campaign shows no targets")
            else:
                print(f"   Sample contacts:")
                for i, contact in enumerate(contacts[:3]):
                    print(f"      {i+1}. {contact.get('email', 'N/A')} - weekly_rollup: {contact.get('weekly_rollup', 'N/A')}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_weekly_rollup_filter_no():
    """Test filtering contacts by weekly_rollup = No"""
    
    print(f"\n3️⃣ Testing Filter for 'weekly_rollup = No':")
    try:
        filter_data = {
            "filters": [
                {
                    "field": "weekly_rollup",
                    "values": ["No"]
                }
            ]
        }
        
        response = requests.post(
            f"{API_URL}/contacts/filter",
            headers={'Content-Type': 'application/json'},
            json=filter_data,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('contacts', [])
            print(f"   ✅ Found {len(contacts)} contacts with weekly_rollup = 'No'")
            
            if len(contacts) == 0:
                print(f"   ⚠️  No contacts found with weekly_rollup = 'No'")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def check_sample_contacts():
    """Check what weekly_rollup values exist in the database"""
    
    print(f"\n4️⃣ Checking Sample Contacts for weekly_rollup values:")
    try:
        response = requests.get(f"{API_URL}/contacts?limit=10", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            contacts = data.get('contacts', [])
            
            print(f"   Found {len(contacts)} sample contacts:")
            weekly_rollup_values = set()
            
            for i, contact in enumerate(contacts):
                weekly_rollup = contact.get('weekly_rollup', 'N/A')
                weekly_rollup_values.add(weekly_rollup)
                print(f"      {i+1}. {contact.get('email', 'N/A')} - weekly_rollup: '{weekly_rollup}'")
            
            print(f"\n   📊 Unique weekly_rollup values found: {list(weekly_rollup_values)}")
            
            if 'Yes' not in weekly_rollup_values and 'No' not in weekly_rollup_values:
                print(f"   ⚠️  No contacts have weekly_rollup set to 'Yes' or 'No'")
                print(f"   💡 This is why the filter returns 0 results")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def provide_solutions():
    """Provide solutions for the weekly_rollup filter issue"""
    
    print(f"\n" + "=" * 80)
    print(f"💡 Solutions")
    print(f"=" * 80)
    
    print(f"\n🔧 If no contacts have weekly_rollup values:")
    print(f"   1. Add weekly_rollup values to existing contacts:")
    print(f"      - Go to Contacts tab")
    print(f"      - Edit contacts and set Weekly Rollup to 'Yes' or 'No'")
    print(f"      - Or import contacts with weekly_rollup values")
    
    print(f"\n🔧 If the filter API is broken:")
    print(f"   1. Check Lambda logs:")
    print(f"      python view_lambda_errors.py bulk-email-api-function 1")
    print(f"   2. Redeploy the Lambda function:")
    print(f"      python deploy_bulk_email_api.py")
    
    print(f"\n🔧 Alternative approach:")
    print(f"   1. Use 'All' button instead of Weekly Rollup filter")
    print(f"   2. Or use other filter types that have data")

def main():
    """Main function"""
    
    print(f"🚀 Starting Weekly Rollup Filter Debug...")
    
    test_weekly_rollup_distinct()
    test_weekly_rollup_filter()
    test_weekly_rollup_filter_no()
    check_sample_contacts()
    provide_solutions()
    
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
