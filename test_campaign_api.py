#!/usr/bin/env python3
"""
Simple test to check what the campaign API returns
"""

import requests
import json

API_URL = "https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod"

def test_campaign():
    print("Testing campaign API...")
    
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
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.text)}")
        
        # Check if it's JSON
        if 'application/json' in response.headers.get('content-type', ''):
            print("✅ Response is JSON")
            try:
                data = response.json()
                print(f"JSON Response: {json.dumps(data, indent=2)}")
            except:
                print("❌ Failed to parse JSON")
                print(f"Raw: {response.text[:200]}...")
        else:
            print("❌ Response is NOT JSON")
            print(f"Raw response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_campaign()
