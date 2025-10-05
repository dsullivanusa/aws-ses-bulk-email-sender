#!/usr/bin/env python3
"""
Add /contacts/filter endpoint to API Gateway for filtering contacts
"""
import boto3
import json

# Lambda function name
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def add_filter_endpoint():
    """Add /contacts/filter POST endpoint to API Gateway"""
    
    client = boto3.client('apigateway', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        print("="*60)
        print(f"Using Lambda function: {LAMBDA_FUNCTION_NAME}")
        print("="*60)
        
        # Find the API
        print("\nLooking for API Gateway...")
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
        
        # Get Lambda function ARN
        print(f"\nGetting Lambda function: {LAMBDA_FUNCTION_NAME}...")
        try:
            lambda_function = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            lambda_arn = lambda_function['Configuration']['FunctionArn']
            account_id = lambda_arn.split(':')[4]
            region = 'us-gov-west-1'
            print(f"✓ Lambda ARN: {lambda_arn}")
        except Exception as e:
            print(f"\n❌ ERROR: Lambda function '{LAMBDA_FUNCTION_NAME}' not found!")
            print(f"Error: {str(e)}")
            return
        
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
        
        # Check if /contacts/filter already exists
        filter_resource = None
        for resource in resources['items']:
            if resource['path'] == '/contacts/filter':
                filter_resource = resource
                print(f"⚠ /contacts/filter already exists (ID: {resource['id']})")
                break
        
        # Create /contacts/filter resource if it doesn't exist
        if not filter_resource:
            print("\nCreating /contacts/filter resource...")
            filter_resource = client.create_resource(
                restApiId=api_id,
                parentId=contacts_resource_id,
                pathPart='filter'
            )
            filter_resource_id = filter_resource['id']
            print(f"✓ Created /contacts/filter resource (ID: {filter_resource_id})")
        else:
            filter_resource_id = filter_resource['id']
        
        # Check if POST method exists
        try:
            method = client.get_method(
                restApiId=api_id,
                resourceId=filter_resource_id,
                httpMethod='POST'
            )
            print("⚠ POST method already exists on /contacts/filter")
            
            # Ask if we should update it
            response = input("Do you want to update the existing POST method? (y/n): ")
            if response.lower() != 'y':
                print("Skipping method update")
                # Still deploy
                print("\nDeploying to prod stage...")
                deployment = client.create_deployment(
                    restApiId=api_id,
                    stageName='prod',
                    description='Updated /contacts/filter endpoint'
                )
                print(f"✓ Deployed to prod (Deployment ID: {deployment['id']})")
                return
            
            # Delete existing method to recreate
            client.delete_method(
                restApiId=api_id,
                resourceId=filter_resource_id,
                httpMethod='POST'
            )
            print("✓ Deleted existing POST method")
        except client.exceptions.NotFoundException:
            pass
        
        # Create POST method
        print("\nCreating POST method on /contacts/filter...")
        client.put_method(
            restApiId=api_id,
            resourceId=filter_resource_id,
            httpMethod='POST',
            authorizationType='NONE'
        )
        print("✓ Created POST method")
        
        # Create integration with Lambda
        print("Setting up Lambda integration...")
        uri = f'arn:aws-us-gov:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations'
        
        client.put_integration(
            restApiId=api_id,
            resourceId=filter_resource_id,
            httpMethod='POST',
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
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId=f'apigateway-filter-{api_id}',
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
            description='Added /contacts/filter endpoint'
        )
        print(f"✓ Deployed to prod (Deployment ID: {deployment['id']})")
        
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print(f"\nThe /contacts/filter endpoint has been added to API Gateway.")
        print(f"\nEndpoint URL:")
        print(f"  https://{api_id}.execute-api.{region}.amazonaws.com/prod/contacts/filter")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("="*60)
    print("Add /contacts/filter Endpoint to API Gateway")
    print("="*60)
    print(f"\nLambda Function: {LAMBDA_FUNCTION_NAME}")
    print("\nThis will add a new POST endpoint: /contacts/filter")
    print("Used to filter contacts from DynamoDB based on selected criteria")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        add_filter_endpoint()
    else:
        print("Cancelled")

