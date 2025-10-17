#!/usr/bin/env python3
"""
Delete API Gateway
Removes existing API Gateway by name or ID
"""

import boto3
import json
import sys

REGION = 'us-gov-west-1'

def list_apis():
    """List all API Gateways"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    response = apigateway.get_rest_apis(limit=500)
    apis = response.get('items', [])
    
    if not apis:
        print("No API Gateways found.")
        return []
    
    print("\n" + "="*80)
    print("EXISTING API GATEWAYS")
    print("="*80)
    print(f"{'API ID':<25} {'Name':<35} {'Created':<20}")
    print("-"*80)
    
    for api in apis:
        api_id = api['id']
        name = api['name']
        created = api.get('createdDate', 'N/A')
        print(f"{api_id:<25} {name:<35} {str(created):<20}")
    
    print("="*80)
    return apis

def delete_api(api_id):
    """Delete API Gateway by ID"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        # Get API details
        api = apigateway.get_rest_api(restApiId=api_id)
        api_name = api['name']
        
        print(f"\nAPI to delete:")
        print(f"  ID:   {api_id}")
        print(f"  Name: {api_name}")
        
        response = input(f"\n⚠️  Delete this API Gateway? This cannot be undone! (yes/no): ")
        
        if response.lower() != 'yes':
            print("Cancelled.")
            return False
        
        print(f"\n🗑️  Deleting API Gateway...")
        apigateway.delete_rest_api(restApiId=api_id)
        
        print(f"\n✅ API Gateway deleted successfully!")
        print(f"Deleted: {api_name} ({api_id})")
        
        return True
        
    except apigateway.exceptions.NotFoundException:
        print(f"❌ Error: API Gateway {api_id} not found")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    if len(sys.argv) > 1:
        # API ID provided as argument
        api_id = sys.argv[1]
        delete_api(api_id)
    else:
        # List APIs and prompt
        apis = list_apis()
        
        if not apis:
            return
        
        print("\nEnter API ID to delete (or 'cancel' to exit):")
        api_id = input("> ").strip()
        
        if api_id.lower() == 'cancel':
            print("Cancelled.")
            return
        
        delete_api(api_id)

if __name__ == '__main__':
    main()

