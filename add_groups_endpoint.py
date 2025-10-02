#!/usr/bin/env python3
"""
Add /groups endpoint to existing API Gateway
Run this after updating your Lambda function with the new code
"""

import boto3
import json

# Configuration
REGION = 'us-gov-west-1'
API_NAME = 'bulk-email-api'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def add_groups_endpoint():
    """Add the /groups GET endpoint to API Gateway"""
    
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
                print(f"Found API: {api['name']} (ID: {api_id})")
                break
        
        if not api_id:
            print(f"ERROR: Could not find API Gateway with name containing '{API_NAME}'")
            print("\nAvailable APIs:")
            for api in apis['items']:
                print(f"  - {api['name']} (ID: {api['id']})")
            return
        
        # Get the root resource
        resources = apigateway.get_resources(restApiId=api_id)
        root_id = None
        
        for resource in resources['items']:
            if resource['path'] == '/':
                root_id = resource['id']
                break
        
        if not root_id:
            print("ERROR: Could not find root resource")
            return
        
        print(f"Root resource ID: {root_id}")
        
        # Check if /groups already exists
        groups_exists = False
        for resource in resources['items']:
            if resource['path'] == '/groups':
                print("⚠️  /groups endpoint already exists!")
                groups_exists = True
                groups_resource_id = resource['id']
                break
        
        # Create /groups resource if it doesn't exist
        if not groups_exists:
            print("Creating /groups resource...")
            groups_resource = apigateway.create_resource(
                restApiId=api_id,
                parentId=root_id,
                pathPart='groups'
            )
            groups_resource_id = groups_resource['id']
            print(f"✓ Created /groups resource (ID: {groups_resource_id})")
        
        # Add GET method to /groups
        try:
            print("Adding GET method to /groups...")
            apigateway.put_method(
                restApiId=api_id,
                resourceId=groups_resource_id,
                httpMethod='GET',
                authorizationType='NONE'
            )
            print("✓ Added GET method")
        except apigateway.exceptions.ConflictException:
            print("⚠️  GET method already exists on /groups")
        
        # Get Lambda function ARN
        lambda_response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_arn = lambda_response['Configuration']['FunctionArn']
        print(f"Lambda ARN: {lambda_arn}")
        
        # Set up Lambda integration
        try:
            print("Setting up Lambda integration...")
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=groups_resource_id,
                httpMethod='GET',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f'arn:aws-us-gov:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
            )
            print("✓ Lambda integration configured")
        except Exception as e:
            print(f"Integration setup: {str(e)}")
        
        # Get AWS account ID
        sts = boto3.client('sts', region_name=REGION)
        account_id = sts.get_caller_identity()['Account']
        
        # Add Lambda permission
        try:
            print("Adding Lambda invoke permission...")
            lambda_client.add_permission(
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId=f'apigateway-groups-{api_id}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f'arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/GET/groups'
            )
            print("✓ Lambda permission added")
        except lambda_client.exceptions.ResourceConflictException:
            print("⚠️  Lambda permission already exists")
        except Exception as e:
            print(f"⚠️  Could not add Lambda permission: {str(e)}")
            print("    You may need to add this manually in the Lambda console")
        
        # Add OPTIONS method for CORS
        try:
            print("Adding OPTIONS method for CORS...")
            apigateway.put_method(
                restApiId=api_id,
                resourceId=groups_resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE'
            )
            
            apigateway.put_method_response(
                restApiId=api_id,
                resourceId=groups_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Methods': True,
                    'method.response.header.Access-Control-Allow-Origin': True
                }
            )
            
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=groups_resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={'application/json': '{"statusCode": 200}'}
            )
            
            apigateway.put_integration_response(
                restApiId=api_id,
                resourceId=groups_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            print("✓ CORS configured")
        except apigateway.exceptions.ConflictException:
            print("⚠️  OPTIONS method already configured")
        
        # Deploy the API
        print("\nDeploying API to 'prod' stage...")
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Added /groups endpoint'
        )
        print(f"✓ Deployment successful! (ID: {deployment['id']})")
        
        print("\n" + "="*60)
        print("✓ SUCCESS! /groups endpoint has been added and deployed")
        print("="*60)
        print(f"\nAPI Endpoint: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod")
        print(f"Groups endpoint: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/groups")
        print("\nYou can now test the endpoint:")
        print(f"  curl https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/groups")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("Add /groups Endpoint to API Gateway")
    print("="*60)
    print()
    
    add_groups_endpoint()

