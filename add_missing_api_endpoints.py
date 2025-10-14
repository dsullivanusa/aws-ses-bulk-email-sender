#!/usr/bin/env python3
"""
Add Missing Endpoints to Existing API Gateway
This script adds all missing endpoints that exist in the Lambda but not in API Gateway
"""

import boto3
import json
import sys
from botocore.exceptions import ClientError

REGION = 'us-gov-west-1'
API_NAME = 'bulk-email-api'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def get_api_id():
    """Get the API Gateway ID by name"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    response = apigateway.get_rest_apis(limit=500)
    apis = response.get('items', [])
    
    for api in apis:
        if API_NAME in api['name'].lower():
            return api['id']
    
    return None

def get_lambda_arn():
    """Get Lambda function ARN"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        return response['Configuration']['FunctionArn']
    except Exception as e:
        print(f"Error getting Lambda ARN: {e}")
        return None

def get_root_resource_id(api_id):
    """Get the root resource ID"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    response = apigateway.get_resources(restApiId=api_id)
    resources = response.get('items', [])
    
    for resource in resources:
        if resource['path'] == '/':
            return resource['id']
    
    return None

def get_existing_resources(api_id):
    """Get all existing resources"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    response = apigateway.get_resources(restApiId=api_id, limit=500)
    resources = response.get('items', [])
    
    # Create a mapping of path to resource
    resource_map = {}
    for resource in resources:
        resource_map[resource['path']] = resource
    
    return resource_map

def create_resource(api_id, parent_id, path_part):
    """Create a new resource"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        response = apigateway.create_resource(
            restApiId=api_id,
            parentId=parent_id,
            pathPart=path_part
        )
        print(f"  ✅ Created resource: /{path_part}")
        return response['id']
    except ClientError as e:
        if 'ConflictException' in str(e):
            print(f"  ⚠️  Resource /{path_part} already exists")
            # Get the existing resource ID
            resources = apigateway.get_resources(restApiId=api_id)
            for resource in resources['items']:
                if resource.get('pathPart') == path_part and resource['parentId'] == parent_id:
                    return resource['id']
        else:
            print(f"  ❌ Error creating resource /{path_part}: {e}")
        return None

def add_method(api_id, resource_id, method, lambda_arn):
    """Add a method to a resource"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        # Create method
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            authorizationType='NONE'
        )
        
        # Create integration
        uri = f"arn:aws-us-gov:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=uri
        )
        
        print(f"    ✅ Added {method} method")
        return True
        
    except ClientError as e:
        if 'ConflictException' in str(e):
            print(f"    ℹ️  {method} method already exists")
        else:
            print(f"    ❌ Error adding {method} method: {e}")
        return False

def add_cors_method(api_id, resource_id):
    """Add CORS OPTIONS method"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        # Create OPTIONS method
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        
        # Create mock integration for OPTIONS
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Add method response
        apigateway.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        
        # Add integration response
        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
        
        print(f"    ✅ Added CORS OPTIONS method")
        return True
        
    except ClientError as e:
        if 'ConflictException' in str(e):
            print(f"    ℹ️  OPTIONS method already exists")
        else:
            print(f"    ❌ Error adding OPTIONS method: {e}")
        return False

def ensure_lambda_permission(api_id, lambda_arn):
    """Ensure Lambda has permission to be invoked by API Gateway"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    # Extract account ID from Lambda ARN
    account_id = lambda_arn.split(':')[4]
    
    statement_id = f'apigateway-invoke-{api_id}'
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/*'
        )
        print(f"\n✅ Added Lambda invoke permission for API Gateway")
    except ClientError as e:
        if 'ResourceConflictException' in str(e):
            print(f"\nℹ️  Lambda permission already exists")
        else:
            print(f"\n⚠️  Error adding Lambda permission: {e}")

def add_missing_endpoints():
    """Add all missing endpoints to API Gateway"""
    
    print("="*80)
    print("ADDING MISSING ENDPOINTS TO API GATEWAY")
    print("="*80)
    
    # Get API ID
    api_id = get_api_id()
    if not api_id:
        print(f"❌ API Gateway '{API_NAME}' not found")
        return False
    
    print(f"\n✅ Found API Gateway: {api_id}")
    
    # Get Lambda ARN
    lambda_arn = get_lambda_arn()
    if not lambda_arn:
        print(f"❌ Lambda function '{LAMBDA_FUNCTION_NAME}' not found")
        return False
    
    print(f"✅ Found Lambda: {lambda_arn}")
    
    # Get root resource
    root_id = get_root_resource_id(api_id)
    if not root_id:
        print("❌ Root resource not found")
        return False
    
    print(f"✅ Root resource ID: {root_id}")
    
    # Get existing resources
    existing_resources = get_existing_resources(api_id)
    print(f"\n📋 Existing resources: {list(existing_resources.keys())}")
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    # Define all endpoints that should exist
    endpoints = [
        # Config endpoint
        {
            'path': '/config',
            'parent_path': '/',
            'methods': ['GET', 'POST']
        },
        # Contacts endpoints
        {
            'path': '/contacts',
            'parent_path': '/',
            'methods': ['GET', 'POST', 'PUT', 'DELETE']
        },
        {
            'path': '/contacts/distinct',
            'parent_path': '/contacts',
            'methods': ['GET']
        },
        {
            'path': '/contacts/filter',
            'parent_path': '/contacts',
            'methods': ['POST']
        },
        {
            'path': '/contacts/batch',
            'parent_path': '/contacts',
            'methods': ['POST']
        },
        {
            'path': '/contacts/search',
            'parent_path': '/contacts',
            'methods': ['POST']
        },
        # Groups endpoint
        {
            'path': '/groups',
            'parent_path': '/',
            'methods': ['GET']
        },
        # Campaign endpoints
        {
            'path': '/campaign',
            'parent_path': '/',
            'methods': ['POST']
        },
        {
            'path': '/campaigns',  # This is the missing one!
            'parent_path': '/',
            'methods': ['GET']
        },
        # Upload endpoint
        {
            'path': '/upload-attachment',
            'parent_path': '/',
            'methods': ['POST']
        },
        # Attachment presigned URL endpoint
        {
            'path': '/attachment-url',
            'parent_path': '/',
            'methods': ['GET']
        },
        # Preview endpoints
        {
            'path': '/preview',
            'parent_path': '/',
            'methods': ['POST', 'GET']
        }
    ]
    
    print(f"\n{'='*80}")
    print("CREATING MISSING RESOURCES AND METHODS")
    print("="*80)
    
    # Track what we add
    added_resources = []
    added_methods = []
    
    for endpoint in endpoints:
        path = endpoint['path']
        parent_path = endpoint['parent_path']
        methods = endpoint['methods']
        
        print(f"\n📍 Processing {path}...")
        
        # Check if resource exists
        if path in existing_resources:
            resource_id = existing_resources[path]['id']
            print(f"  ✅ Resource exists (ID: {resource_id})")
        else:
            # Create the resource
            parent_id = existing_resources[parent_path]['id'] if parent_path in existing_resources else root_id
            path_part = path.split('/')[-1]
            
            resource_id = create_resource(api_id, parent_id, path_part)
            if resource_id:
                existing_resources[path] = {'id': resource_id, 'path': path}
                added_resources.append(path)
        
        if resource_id:
            # Add methods
            for method in methods:
                if add_method(api_id, resource_id, method, lambda_arn):
                    added_methods.append(f"{method} {path}")
            
            # Add CORS
            add_cors_method(api_id, resource_id)
    
    # Ensure Lambda permission
    ensure_lambda_permission(api_id, lambda_arn)
    
    # Deploy the changes
    print(f"\n{'='*80}")
    print("DEPLOYING CHANGES")
    print("="*80)
    
    try:
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Added missing endpoints for campaign history and other features'
        )
        
        print(f"✅ Successfully deployed to 'prod' stage")
        print(f"   Deployment ID: {deployment['id']}")
        
        # Get the API URL
        api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
        print(f"\n🌐 API URL: {api_url}")
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print("="*80)
        print(f"✅ Added {len(added_resources)} new resources:")
        for resource in added_resources:
            print(f"   • {resource}")
        
        print(f"\n✅ Added {len(added_methods)} new methods:")
        for method in added_methods:
            print(f"   • {method}")
        
        print(f"\n{'='*80}")
        print("✅ API Gateway updated successfully!")
        print("="*80)
        print("\n🎉 Your campaign history tab should now work!")
        print(f"   Try accessing: {api_url}/campaigns")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = add_missing_endpoints()
    sys.exit(0 if success else 1)

