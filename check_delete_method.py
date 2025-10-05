#!/usr/bin/env python3
"""
Check if DELETE method is configured for /contacts endpoint in API Gateway
"""
import boto3
import json

def check_delete_method():
    """Check API Gateway DELETE method configuration"""
    
    client = boto3.client('apigateway', region_name='us-gov-west-1')
    
    try:
        # Find the API
        print("Looking for API Gateway...")
        apis = client.get_rest_apis()
        
        api = None
        for a in apis['items']:
            if a['name'] == 'bulk-email-api':
                api = a
                break
        
        if not api:
            print("ERROR: API 'bulk-email-api' not found")
            return
        
        api_id = api['id']
        print(f"✓ Found API: {api['name']} (ID: {api_id})")
        
        # Get resources
        print("\nGetting resources...")
        resources = client.get_resources(restApiId=api_id)
        
        contacts_resource = None
        for resource in resources['items']:
            if resource['path'] == '/contacts':
                contacts_resource = resource
                break
        
        if not contacts_resource:
            print("ERROR: /contacts resource not found")
            return
        
        resource_id = contacts_resource['id']
        print(f"✓ Found /contacts resource (ID: {resource_id})")
        
        # Check methods
        print("\nMethods available on /contacts:")
        methods = contacts_resource.get('resourceMethods', {})
        for method_name in methods.keys():
            print(f"  - {method_name}")
        
        # Check if DELETE exists
        if 'DELETE' in methods:
            print("\n✓ DELETE method EXISTS on /contacts")
            
            # Get method details
            method = client.get_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='DELETE'
            )
            
            print("\nDELETE Method Details:")
            print(f"  Authorization Type: {method.get('authorizationType', 'NONE')}")
            print(f"  API Key Required: {method.get('apiKeyRequired', False)}")
            print(f"  Request Parameters: {method.get('requestParameters', {})}")
            
            # Check integration
            integration = client.get_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='DELETE'
            )
            
            print("\nIntegration Details:")
            print(f"  Type: {integration.get('type', 'UNKNOWN')}")
            print(f"  URI: {integration.get('uri', 'N/A')}")
            print(f"  HTTP Method: {integration.get('httpMethod', 'N/A')}")
            
        else:
            print("\n❌ DELETE method DOES NOT EXIST on /contacts")
            print("\nYou need to add the DELETE method to API Gateway.")
            print("Would you like me to create a script to add it?")
        
        # Check deployment
        print("\n" + "="*50)
        print("Checking deployments...")
        deployments = client.get_deployments(restApiId=api_id)
        
        if deployments['items']:
            latest = deployments['items'][0]
            print(f"Latest deployment: {latest['id']}")
            print(f"Created: {latest.get('createdDate', 'Unknown')}")
        else:
            print("No deployments found")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_delete_method()

