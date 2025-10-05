#!/usr/bin/env python3
"""
Add /contacts/distinct endpoint to API Gateway for getting distinct field values
"""
import boto3
import json

def add_distinct_endpoint():
    """Add /contacts/distinct GET endpoint to API Gateway"""
    
    client = boto3.client('apigateway', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
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
        
        # Find the Lambda function - try multiple patterns
        print("\nLooking for Lambda function...")
        functions = lambda_client.list_functions()
        function_names = [f['FunctionName'] for f in functions['Functions']]
        
        patterns = [
            'bulk-email-api-function',
            'bulk-email',
            'BulkEmail',
            'bulk_email',
            'email-api'
        ]
        
        lambda_function_name = None
        
        for pattern in patterns:
            matches = [name for name in function_names if pattern.lower() in name.lower()]
            if matches:
                lambda_function_name = matches[0]
                print(f"✓ Found Lambda function: {lambda_function_name}")
                break
        
        if not lambda_function_name:
            print("\nAvailable Lambda functions:")
            for i, name in enumerate(function_names, 1):
                print(f"{i}. {name}")
            print("\nCould not find Lambda function automatically.")
            lambda_function_name = input("Enter the Lambda function name: ").strip()
        
        # Get Lambda function ARN
        lambda_function = lambda_client.get_function(FunctionName=lambda_function_name)
        lambda_arn = lambda_function['Configuration']['FunctionArn']
        account_id = lambda_arn.split(':')[4]
        region = 'us-gov-west-1'
        
        print(f"✓ Lambda ARN: {lambda_arn}")
        
        # Get resources
        print("\nGetting resources...")
        resources = client.get_resources(restApiId=api_id)
        
        # Find /contacts resource
        contacts_resource = None
        for resource in resources['items']:
            if resource['path'] == '/contacts':
                contacts_resource = resource
                break
        
        if not contacts_resource:
            print("ERROR: /contacts resource not found")
            return
        
        contacts_resource_id = contacts_resource['id']
        print(f"✓ Found /contacts resource (ID: {contacts_resource_id})")
        
        # Check if /contacts/distinct already exists
        distinct_resource = None
        for resource in resources['items']:
            if resource['path'] == '/contacts/distinct':
                distinct_resource = resource
                print(f"⚠ /contacts/distinct already exists (ID: {resource['id']})")
                break
        
        # Create /contacts/distinct resource if it doesn't exist
        if not distinct_resource:
            print("\nCreating /contacts/distinct resource...")
            distinct_resource = client.create_resource(
                restApiId=api_id,
                parentId=contacts_resource_id,
                pathPart='distinct'
            )
            distinct_resource_id = distinct_resource['id']
            print(f"✓ Created /contacts/distinct resource (ID: {distinct_resource_id})")
        else:
            distinct_resource_id = distinct_resource['id']
        
        # Check if GET method exists
        try:
            method = client.get_method(
                restApiId=api_id,
                resourceId=distinct_resource_id,
                httpMethod='GET'
            )
            print("⚠ GET method already exists on /contacts/distinct")
            
            # Ask if we should update it
            response = input("Do you want to update the existing GET method? (y/n): ")
            if response.lower() != 'y':
                print("Skipping method update")
                return
            
            # Delete existing method to recreate
            client.delete_method(
                restApiId=api_id,
                resourceId=distinct_resource_id,
                httpMethod='GET'
            )
            print("✓ Deleted existing GET method")
        except client.exceptions.NotFoundException:
            pass
        
        # Create GET method
        print("\nCreating GET method on /contacts/distinct...")
        client.put_method(
            restApiId=api_id,
            resourceId=distinct_resource_id,
            httpMethod='GET',
            authorizationType='NONE',
            requestParameters={
                'method.request.querystring.field': False
            }
        )
        print("✓ Created GET method")
        
        # Create integration with Lambda
        print("Setting up Lambda integration...")
        uri = f'arn:aws-us-gov:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        
        client.put_integration(
            restApiId=api_id,
            resourceId=distinct_resource_id,
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=uri
        )
        print("✓ Created Lambda integration")
        
        # Add Lambda permission for API Gateway to invoke
        print("\nAdding Lambda invocation permission...")
        source_arn = f'arn:aws-us-gov:execute-api:{region}:{account_id}:{api_id}/*/*/*'
        
        try:
            lambda_client.add_permission(
                FunctionName=lambda_function_name,
                StatementId=f'apigateway-distinct-{api_id}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=source_arn
            )
            print("✓ Added Lambda permission")
        except lambda_client.exceptions.ResourceConflictException:
            print("⚠ Permission already exists (this is fine)")
        
        # Deploy to prod stage
        print("\nDeploying to prod stage...")
        deployment = client.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Added /contacts/distinct endpoint'
        )
        print(f"✓ Deployed to prod (Deployment ID: {deployment['id']})")
        
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print(f"\nThe /contacts/distinct endpoint has been added to API Gateway.")
        print(f"\nEndpoint URL:")
        print(f"  https://{api_id}.execute-api.{region}.amazonaws.com/prod/contacts/distinct?field=<field_name>")
        print(f"\nExample:")
        print(f"  curl 'https://{api_id}.execute-api.{region}.amazonaws.com/prod/contacts/distinct?field=state'")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("Add /contacts/distinct Endpoint to API Gateway")
    print("="*60)
    print("\nThis will add a new GET endpoint: /contacts/distinct")
    print("Used to retrieve distinct values for a field from DynamoDB")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        add_distinct_endpoint()
    else:
        print("Cancelled")

