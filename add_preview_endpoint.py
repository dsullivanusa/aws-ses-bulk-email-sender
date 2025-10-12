#!/usr/bin/env python3
"""
Add /preview endpoints to existing API Gateway
This enables email preview functionality
"""

import boto3
import json

# Configuration
REGION = 'us-gov-west-1'
API_NAME = 'bulk-email-api'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def add_preview_endpoints():
    """Add the /preview POST and /preview/{preview_id} GET endpoints to API Gateway"""
    
    # Initialize AWS clients
    apigateway = boto3.client('apigateway', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        # Find the API Gateway
        print(f"Looking for API Gateway: {API_NAME}...")
        apis = apigateway.get_rest_apis()
        
        api_id = None
        for api in apis['items']:
            if API_NAME in api['name']:
                api_id = api['id']
                print(f"✅ Found API: {api['name']} (ID: {api_id})")
                break
        
        if not api_id:
            print(f"❌ ERROR: Could not find API Gateway with name containing '{API_NAME}'")
            print("\nAvailable APIs:")
            for api in apis['items']:
                print(f"  - {api['name']} (ID: {api['id']})")
            return
        
        # Get Lambda function ARN and extract account ID
        try:
            lambda_response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            lambda_arn = lambda_response['Configuration']['FunctionArn']
            print(f"✅ Found Lambda function: {LAMBDA_FUNCTION_NAME}")
            print(f"   ARN: {lambda_arn}")
            
            # Extract account ID from Lambda ARN
            # Format: arn:aws-us-gov:lambda:region:account-id:function:function-name
            account_id = lambda_arn.split(':')[4]
            print(f"   Account ID: {account_id}")
        except Exception as e:
            print(f"❌ ERROR: Could not find Lambda function '{LAMBDA_FUNCTION_NAME}': {e}")
            return
        
        # Get resources
        resources = apigateway.get_resources(restApiId=api_id)
        
        # Find root resource
        root_id = None
        for resource in resources['items']:
            if resource['path'] == '/':
                root_id = resource['id']
                break
        
        if not root_id:
            print("❌ ERROR: Could not find root resource")
            return
        
        print(f"✅ Root resource ID: {root_id}")
        
        # ============================================
        # Step 1: Create /preview resource (if not exists)
        # ============================================
        print("\n📋 Step 1: Creating /preview resource...")
        
        preview_exists = False
        preview_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/preview':
                preview_exists = True
                preview_resource_id = resource['id']
                print(f"   ℹ️  /preview already exists (ID: {preview_resource_id})")
                break
        
        if not preview_exists:
            # Create /preview resource
            print("   Creating /preview resource...")
            preview_resource = apigateway.create_resource(
                restApiId=api_id,
                parentId=root_id,
                pathPart='preview'
            )
            preview_resource_id = preview_resource['id']
            print(f"   ✅ Created /preview (ID: {preview_resource_id})")
        
        # ============================================
        # Step 2: Add POST method to /preview
        # ============================================
        print("\n📋 Step 2: Adding POST method to /preview...")
        
        try:
            # Check if POST method already exists
            existing_method = apigateway.get_method(
                restApiId=api_id,
                resourceId=preview_resource_id,
                httpMethod='POST'
            )
            print("   ℹ️  POST method already exists on /preview")
        except apigateway.exceptions.NotFoundException:
            # Create POST method
            print("   Creating POST method...")
            apigateway.put_method(
                restApiId=api_id,
                resourceId=preview_resource_id,
                httpMethod='POST',
                authorizationType='NONE',
                requestParameters={}
            )
            print("   ✅ Created POST method")
            
            # Set up Lambda integration
            print("   Setting up Lambda integration...")
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=preview_resource_id,
                httpMethod='POST',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f'arn:aws-us-gov:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
            )
            print("   ✅ Lambda integration configured")
            
            # Add Lambda permission
            print("   Adding Lambda invoke permission...")
            try:
                lambda_client.add_permission(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    StatementId=f'apigateway-preview-post-{api_id}',
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f'arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/POST/preview'
                )
                print("   ✅ Lambda permission added")
            except lambda_client.exceptions.ResourceConflictException:
                print("   ℹ️  Lambda permission already exists")
        
        # ============================================
        # Step 3: Create /preview/{preview_id} resource
        # ============================================
        print("\n📋 Step 3: Creating /preview/{preview_id} resource...")
        
        preview_id_exists = False
        preview_id_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/preview/{preview_id}':
                preview_id_exists = True
                preview_id_resource_id = resource['id']
                print(f"   ℹ️  /preview/{{preview_id}} already exists (ID: {preview_id_resource_id})")
                break
        
        if not preview_id_exists:
            # Create /preview/{preview_id} resource
            print("   Creating /preview/{preview_id} resource...")
            preview_id_resource = apigateway.create_resource(
                restApiId=api_id,
                parentId=preview_resource_id,
                pathPart='{preview_id}'
            )
            preview_id_resource_id = preview_id_resource['id']
            print(f"   ✅ Created /preview/{{preview_id}} (ID: {preview_id_resource_id})")
        
        # ============================================
        # Step 4: Add GET method to /preview/{preview_id}
        # ============================================
        print("\n📋 Step 4: Adding GET method to /preview/{preview_id}...")
        
        try:
            # Check if GET method already exists
            existing_method = apigateway.get_method(
                restApiId=api_id,
                resourceId=preview_id_resource_id,
                httpMethod='GET'
            )
            print("   ℹ️  GET method already exists on /preview/{preview_id}")
        except apigateway.exceptions.NotFoundException:
            # Create GET method
            print("   Creating GET method...")
            apigateway.put_method(
                restApiId=api_id,
                resourceId=preview_id_resource_id,
                httpMethod='GET',
                authorizationType='NONE',
                requestParameters={
                    'method.request.path.preview_id': True
                }
            )
            print("   ✅ Created GET method")
            
            # Set up Lambda integration
            print("   Setting up Lambda integration...")
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=preview_id_resource_id,
                httpMethod='GET',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f'arn:aws-us-gov:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations',
                requestParameters={
                    'integration.request.path.preview_id': 'method.request.path.preview_id'
                }
            )
            print("   ✅ Lambda integration configured")
            
            # Add Lambda permission
            print("   Adding Lambda invoke permission...")
            try:
                lambda_client.add_permission(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    StatementId=f'apigateway-preview-get-{api_id}',
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f'arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/GET/preview/*'
                )
                print("   ✅ Lambda permission added")
            except lambda_client.exceptions.ResourceConflictException:
                print("   ℹ️  Lambda permission already exists")
        
        # ============================================
        # Step 5: Deploy to 'prod' stage
        # ============================================
        print("\n📋 Step 5: Deploying API to 'prod' stage...")
        
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Added /preview endpoints for email preview feature'
        )
        print(f"   ✅ Deployment created (ID: {deployment['id']})")
        
        # ============================================
        # Summary
        # ============================================
        print("\n" + "="*60)
        print("✅ Preview endpoints successfully added to API Gateway!")
        print("="*60)
        print(f"\n📍 API Gateway ID: {api_id}")
        print(f"📍 Preview resource ID: {preview_resource_id}")
        print(f"📍 Preview ID resource ID: {preview_id_resource_id}")
        print(f"\n🔗 Endpoints:")
        print(f"   POST   https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/preview")
        print(f"   GET    https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/preview/{{preview_id}}")
        print(f"\n✅ API deployed to 'prod' stage")
        print(f"\n💡 Test the endpoints:")
        print(f"   1. Create an email in the web UI")
        print(f"   2. Click '👁️ Preview Email' button")
        print(f"   3. New window should open with preview")
        print(f"\n📊 Monitor in CloudWatch Logs:")
        print(f"   /aws/lambda/{LAMBDA_FUNCTION_NAME}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("="*60)
    print("  Add Preview Endpoints to API Gateway")
    print("="*60)
    print()
    
    success = add_preview_endpoints()
    
    if success:
        print("\n✅ SUCCESS: Preview endpoints are ready to use!")
    else:
        print("\n❌ FAILED: Please check the error messages above")

