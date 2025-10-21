#!/usr/bin/env python3
"""
Update existing API Gateway with the new /log-csv-error endpoint
"""

import json
import boto3
import sys

# Initialize AWS clients
apigateway = boto3.client('apigateway', region_name='us-gov-west-1')

def find_api_gateway():
    """Find the Bulk Email Sender API Gateway"""
    print("🔍 Finding your API Gateway...")
    
    response = apigateway.get_rest_apis()
    
    for api in response['items']:
        if 'Bulk Email' in api['name'] or 'email' in api['name'].lower():
            print(f"✅ Found API: {api['name']} (ID: {api['id']})")
            return api['id'], api['name']
    
    # If not found, list all APIs
    print("\n❌ Could not auto-detect API Gateway. Available APIs:")
    for api in response['items']:
        print(f"   - {api['name']} (ID: {api['id']})")
    
    # Ask user to select
    api_id = input("\nEnter API Gateway ID: ").strip()
    if api_id:
        api_details = apigateway.get_rest_api(restApiId=api_id)
        return api_id, api_details['name']
    
    return None, None

def get_root_resource(api_id):
    """Get the root resource ID"""
    response = apigateway.get_resources(restApiId=api_id)
    
    for resource in response['items']:
        if resource['path'] == '/':
            return resource['id']
    
    return None

def check_endpoint_exists(api_id, path):
    """Check if endpoint already exists"""
    response = apigateway.get_resources(restApiId=api_id)
    
    for resource in response['items']:
        if resource['path'] == path:
            return True, resource['id']
    
    return False, None

def create_log_csv_error_endpoint(api_id, root_resource_id, lambda_arn):
    """Create the /log-csv-error endpoint"""
    
    # Check if endpoint already exists
    exists, resource_id = check_endpoint_exists(api_id, '/log-csv-error')
    
    if exists:
        print(f"⚠️  /log-csv-error endpoint already exists (Resource ID: {resource_id})")
        overwrite = input("Do you want to recreate it? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Skipping endpoint creation.")
            return resource_id
        else:
            # Delete existing resource
            print("Deleting existing resource...")
            apigateway.delete_resource(restApiId=api_id, resourceId=resource_id)
    
    # Create the /log-csv-error resource
    print("Creating /log-csv-error resource...")
    resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_resource_id,
        pathPart='log-csv-error'
    )
    resource_id = resource['id']
    print(f"✅ Resource created (ID: {resource_id})")
    
    # Create POST method
    print("Creating POST method...")
    apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE',
        apiKeyRequired=False
    )
    
    # Set up Lambda integration
    print("Setting up Lambda integration...")
    apigateway.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=lambda_arn
    )
    
    # Create OPTIONS method for CORS
    print("Creating OPTIONS method (CORS)...")
    apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        authorizationType='NONE',
        apiKeyRequired=False
    )
    
    # Set up CORS response
    apigateway.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        type='MOCK',
        requestTemplates={
            'application/json': '{"statusCode": 200}'
        }
    )
    
    apigateway.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Headers': False,
            'method.response.header.Access-Control-Allow-Methods': False,
            'method.response.header.Access-Control-Allow-Origin': False
        }
    )
    
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
    
    print("✅ /log-csv-error endpoint created successfully!")
    return resource_id

def deploy_api(api_id, stage_name='prod'):
    """Deploy API changes"""
    print(f"\n🚀 Deploying changes to '{stage_name}' stage...")
    
    response = apigateway.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
        description='Added /log-csv-error endpoint for CSV parsing error logging'
    )
    
    print(f"✅ Deployment successful! Deployment ID: {response['id']}")
    
    return response

def get_lambda_function_arn():
    """Get Lambda function ARN"""
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    # Try to find the Lambda function
    try:
        response = lambda_client.list_functions()
        
        print("\n📋 Available Lambda functions:")
        functions = []
        for idx, func in enumerate(response['Functions'], 1):
            if 'email' in func['FunctionName'].lower() or 'api' in func['FunctionName'].lower():
                print(f"   {idx}. {func['FunctionName']}")
                functions.append(func)
        
        if not functions:
            print("No Lambda functions found with 'email' or 'api' in name.")
            print("\nAll functions:")
            for idx, func in enumerate(response['Functions'], 1):
                print(f"   {idx}. {func['FunctionName']}")
            functions = response['Functions']
        
        # Ask user to select
        selection = input(f"\nSelect Lambda function (1-{len(functions)}): ").strip()
        selected_func = functions[int(selection) - 1]
        
        # Construct the integration URI
        arn = selected_func['FunctionArn']
        account_id = arn.split(':')[4]
        function_name = selected_func['FunctionName']
        
        integration_uri = f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{arn}/invocations"
        
        print(f"✅ Using Lambda: {function_name}")
        print(f"   ARN: {arn}")
        
        return integration_uri, function_name, arn
        
    except Exception as e:
        print(f"❌ Error getting Lambda functions: {str(e)}")
        return None, None, None

def add_lambda_permission(api_id, lambda_arn, function_name):
    """Add permission for API Gateway to invoke Lambda"""
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    print(f"\n🔐 Adding permission for API Gateway to invoke Lambda...")
    
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=f'apigateway-log-csv-error-{api_id}',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws-us-gov:execute-api:us-gov-west-1:*:{api_id}/*/*/log-csv-error'
        )
        print("✅ Lambda permission added")
    except lambda_client.exceptions.ResourceConflictException:
        print("ℹ️  Permission already exists, skipping")
    except Exception as e:
        print(f"⚠️  Error adding permission: {str(e)}")
        print("   You may need to add this manually in the Lambda console")

def main():
    print("=" * 60)
    print("API Gateway Updater - Add /log-csv-error Endpoint")
    print("=" * 60)
    print()
    
    # Find API Gateway
    api_id, api_name = find_api_gateway()
    
    if not api_id:
        print("❌ Could not find or select API Gateway. Exiting.")
        sys.exit(1)
    
    # Get Lambda ARN
    lambda_uri, lambda_name, lambda_arn = get_lambda_function_arn()
    
    if not lambda_uri:
        print("❌ Could not find or select Lambda function. Exiting.")
        sys.exit(1)
    
    # Get root resource
    root_resource_id = get_root_resource(api_id)
    
    if not root_resource_id:
        print("❌ Could not find root resource. Exiting.")
        sys.exit(1)
    
    print(f"\n✅ Setup complete. Ready to create endpoint.")
    print(f"   API: {api_name} ({api_id})")
    print(f"   Lambda: {lambda_name}")
    print()
    
    # Confirm
    proceed = input("Proceed with creating /log-csv-error endpoint? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("❌ Cancelled by user.")
        sys.exit(0)
    
    # Create endpoint
    resource_id = create_log_csv_error_endpoint(api_id, root_resource_id, lambda_uri)
    
    # Add Lambda permission
    add_lambda_permission(api_id, lambda_arn, lambda_name)
    
    # Deploy
    deploy = input("\nDeploy changes now? (y/n): ").strip().lower()
    
    if deploy == 'y':
        stage = input("Enter stage name (default: prod): ").strip() or 'prod'
        deploy_api(api_id, stage)
        
        # Get API URL
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print(f"\nNew endpoint available at:")
        print(f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/{stage}/log-csv-error")
        print()
        print("Test it with:")
        print(f"""
curl -X POST https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/{stage}/log-csv-error \\
  -H "Content-Type: application/json" \\
  -d '{{"row": 5, "error": "Test error", "rawLine": "test,line,data"}}'
        """)
    else:
        print("\n⚠️  Changes created but NOT deployed.")
        print("   Deploy manually in the API Gateway console or run:")
        print(f"   aws apigateway create-deployment --rest-api-id {api_id} --stage-name prod --region us-gov-west-1")
    
    print("\n✅ Done!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

