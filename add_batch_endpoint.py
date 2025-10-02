#!/usr/bin/env python3
"""
Add /contacts/batch endpoint to existing API Gateway
This enables batch CSV import of up to 25 contacts at a time
"""

import boto3
import json

# Configuration
REGION = 'us-gov-west-1'
API_NAME = 'bulk-mail-api'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def add_batch_endpoint():
    """Add the /contacts/batch POST endpoint to API Gateway"""
    
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
        
        # Get resources
        resources = apigateway.get_resources(restApiId=api_id)
        
        # Find /contacts resource
        contacts_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/contacts':
                contacts_resource_id = resource['id']
                print(f"Found /contacts resource (ID: {contacts_resource_id})")
                break
        
        if not contacts_resource_id:
            print("ERROR: Could not find /contacts resource. Make sure your API has /contacts endpoint.")
            return
        
        # Check if /contacts/batch already exists
        batch_exists = False
        batch_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/contacts/batch':
                print("⚠️  /contacts/batch endpoint already exists!")
                batch_exists = True
                batch_resource_id = resource['id']
                break
        
        # Create /contacts/batch resource if it doesn't exist
        if not batch_exists:
            print("Creating /contacts/batch resource...")
            batch_resource = apigateway.create_resource(
                restApiId=api_id,
                parentId=contacts_resource_id,
                pathPart='batch'
            )
            batch_resource_id = batch_resource['id']
            print(f"✓ Created /contacts/batch resource (ID: {batch_resource_id})")
        
        # Add POST method to /contacts/batch
        try:
            print("Adding POST method to /contacts/batch...")
            apigateway.put_method(
                restApiId=api_id,
                resourceId=batch_resource_id,
                httpMethod='POST',
                authorizationType='NONE'
            )
            print("✓ Added POST method")
        except apigateway.exceptions.ConflictException:
            print("⚠️  POST method already exists on /contacts/batch")
        
        # Get Lambda function ARN
        lambda_response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        lambda_arn = lambda_response['Configuration']['FunctionArn']
        print(f"Lambda ARN: {lambda_arn}")
        
        # Set up Lambda integration
        try:
            print("Setting up Lambda integration...")
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=batch_resource_id,
                httpMethod='POST',
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
                StatementId=f'apigateway-batch-{api_id}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f'arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/POST/contacts/batch'
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
                resourceId=batch_resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE'
            )
            
            apigateway.put_method_response(
                restApiId=api_id,
                resourceId=batch_resource_id,
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
                resourceId=batch_resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={'application/json': '{"statusCode": 200}'}
            )
            
            apigateway.put_integration_response(
                restApiId=api_id,
                resourceId=batch_resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
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
            description='Added /contacts/batch endpoint for batch CSV import'
        )
        print(f"✓ Deployment successful! (ID: {deployment['id']})")
        
        print("\n" + "="*60)
        print("✓ SUCCESS! /contacts/batch endpoint has been added")
        print("="*60)
        print(f"\nAPI Endpoint: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod")
        print(f"Batch endpoint: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/contacts/batch")
        print("\nYou can now use the batch CSV import feature!")
        print("- Upload CSVs with up to 20,000+ contacts")
        print("- Real-time progress bar")
        print("- Process 25 contacts per batch")
        print("- Completes in ~5-10 minutes for 20,000 contacts")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("Add /contacts/batch Endpoint to API Gateway")
    print("="*60)
    print()
    
    add_batch_endpoint()

