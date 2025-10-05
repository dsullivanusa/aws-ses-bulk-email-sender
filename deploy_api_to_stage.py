#!/usr/bin/env python3
"""
Deploy API Gateway to prod stage
"""

import boto3
import json

REGION = 'us-gov-west-1'

def deploy_api():
    """Deploy API Gateway to prod stage"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    print("🔍 Finding API Gateway...")
    
    # Find the API
    apis = apigateway.get_rest_apis()
    api_id = None
    api_name = None
    
    for api in apis['items']:
        if 'bulk-email' in api['name'].lower():
            api_id = api['id']
            api_name = api['name']
            break
    
    if not api_id:
        print("❌ API Gateway not found!")
        print("\nAvailable APIs:")
        for api in apis['items']:
            print(f"  - {api['name']} (ID: {api['id']})")
        return
    
    print(f"✅ Found API: {api_name} (ID: {api_id})")
    
    # Check if /contacts/search exists
    print("\n🔍 Checking for /contacts/search endpoint...")
    resources = apigateway.get_resources(restApiId=api_id)
    
    search_exists = False
    for resource in resources['items']:
        if resource['path'] == '/contacts/search':
            search_exists = True
            print(f"✅ /contacts/search endpoint exists (ID: {resource['id']})")
            
            # Check methods
            if 'resourceMethods' in resource:
                methods = list(resource['resourceMethods'].keys())
                print(f"   Methods: {', '.join(methods)}")
    
    if not search_exists:
        print("❌ /contacts/search endpoint NOT FOUND!")
        print("   Run: python add_search_endpoint.py")
        return
    
    # Deploy to prod stage
    print("\n🚀 Deploying API to 'prod' stage...")
    
    try:
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Deployed search endpoint'
        )
        
        print(f"✅ API deployed successfully!")
        print(f"   Deployment ID: {deployment['id']}")
        
        api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
        print(f"\n🌐 API URL: {api_url}")
        print(f"   Search endpoint: {api_url}/contacts/search")
        
        print("\n✅ Search should now work in the browser!")
        print("   Hard refresh the page (Ctrl+Shift+R) and try again.")
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("\n📦 Deploying API Gateway Changes\n")
    print("="*80)
    deploy_api()
    print("="*80)

