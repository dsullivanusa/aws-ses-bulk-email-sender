#!/usr/bin/env python3
"""
Update API Gateway to add /log-csv-error endpoint
Configured for: bulk-email-api-function
"""

import boto3
import sys

# Configuration
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'
REGION = 'us-gov-west-1'

# Initialize AWS clients
apigateway = boto3.client('apigateway', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

def find_api_gateway():
    """Find the Bulk Email API Gateway"""
    print("🔍 Finding your API Gateway...")
    
    response = apigateway.get_rest_apis()
    
    print(f"\nFound {len(response['items'])} API Gateway(s):\n")
    
    for idx, api in enumerate(response['items'], 1):
        print(f"{idx}. {api['name']} (ID: {api['id']})")
    
    if len(response['items']) == 1:
        api = response['items'][0]
        print(f"\n✅ Using: {api['name']} (ID: {api['id']})")
        return api['id'], api['name']
    
    # Ask user to select
    selection = input(f"\nSelect API Gateway (1-{len(response['items'])}): ").strip()
    api = response['items'][int(selection) - 1]
    
    return api['id'], api['name']

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

def get_lambda_arn():
    """Get Lambda function ARN"""
    print(f"\n📦 Getting Lambda function: {LAMBDA_FUNCTION_NAME}")
    
    try:
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        arn = response['Configuration']['FunctionArn']
        
        print(f"✅ Found Lambda function")
        print(f"   ARN: {arn}")
        print(f"   Runtime: {response['Configuration']['Runtime']}")
        print(f"   Handler: {response['Configuration']['Handler']}")
        
        # Construct integration URI
        integration_uri = f"arn:aws-us-gov:apigateway:{REGION}:lambda:path/2015-03-31/functions/{arn}/invocations"
        
        return integration_uri, arn
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"❌ Lambda function '{LAMBDA_FUNCTION_NAME}' not found in {REGION}")
        print("\n💡 Check:")
        print("   1. Function name is correct")
        print("   2. Function exists in us-gov-west-1 region")
        print("   3. You have permission to access it")
        return None, None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, None

def create_log_csv_error_endpoint(api_id, root_resource_id, lambda_uri):
    """Create the /log-csv-error endpoint"""
    
    # Check if endpoint already exists
    exists, resource_id = check_endpoint_exists(api_id, '/log-csv-error')
    
    if exists:
        print(f"\n⚠️  /log-csv-error endpoint already exists (Resource ID: {resource_id})")
        overwrite = input("Do you want to recreate it? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("✅ Skipping endpoint creation - using existing endpoint")
            return resource_id
        else:
            # Delete existing resource
            print("Deleting existing resource...")
            apigateway.delete_resource(restApiId=api_id, resourceId=resource_id)
    
    print("\n📝 Creating /log-csv-error endpoint...")
    
    # Create the /log-csv-error resource
    print("   - Creating resource...")
    resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_resource_id,
        pathPart='log-csv-error'
    )
    resource_id = resource['id']
    print(f"   ✅ Resource created (ID: {resource_id})")
    
    # Create POST method
    print("   - Creating POST method...")
    apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE',
        apiKeyRequired=False
    )
    
    # Set up Lambda integration
    print("   - Setting up Lambda proxy integration...")
    apigateway.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=lambda_uri
    )
    
    # Create OPTIONS method for CORS
    print("   - Creating OPTIONS method (CORS)...")
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
    
    print("   ✅ /log-csv-error endpoint created successfully!")
    return resource_id

def add_lambda_permission(api_id, lambda_arn):
    """Add permission for API Gateway to invoke Lambda"""
    
    print(f"\n🔐 Adding permission for API Gateway to invoke Lambda...")
    
    # Extract account ID from Lambda ARN
    # ARN format: arn:aws-us-gov:lambda:us-gov-west-1:123456789012:function:function-name
    account_id = lambda_arn.split(':')[4]
    print(f"   Account ID: {account_id}")
    
    # Sanitize api_id for StatementId (only alphanumeric, hyphens, underscores)
    import re
    safe_api_id = re.sub(r'[^a-zA-Z0-9_-]', '', api_id)
    statement_id = f'apigateway-csv-error-{safe_api_id}'
    
    # Construct SourceArn with actual account ID
    source_arn = f'arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/*/log-csv-error'
    print(f"   SourceArn: {source_arn}")
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
        print(f"✅ Lambda permission added successfully (StatementId: {statement_id})")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"ℹ️  Permission already exists (StatementId: {statement_id}) - OK")
    except Exception as e:
        print(f"⚠️  Warning: {str(e)}")
        print(f"   StatementId attempted: {statement_id}")
        print(f"   SourceArn attempted: {source_arn}")
        print("   The endpoint may still work if permissions already exist")
        print("   You can add permission manually in AWS Console if needed")

def deploy_api(api_id, stage_name='prod'):
    """Deploy API changes"""
    print(f"\n🚀 Deploying changes to '{stage_name}' stage...")
    
    response = apigateway.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
        description='Added /log-csv-error endpoint for CSV parsing error logging'
    )
    
    print(f"✅ Deployment successful! (Deployment ID: {response['id']})")
    
    return response

def main():
    print("=" * 70)
    print("Add /log-csv-error Endpoint to API Gateway")
    print("=" * 70)
    print(f"\nLambda Function: {LAMBDA_FUNCTION_NAME}")
    print(f"Region: {REGION}")
    print()
    
    # Get Lambda ARN
    lambda_uri, lambda_arn = get_lambda_arn()
    
    if not lambda_uri:
        print("\n❌ Cannot proceed without Lambda function. Exiting.")
        sys.exit(1)
    
    # Find API Gateway
    api_id, api_name = find_api_gateway()
    
    if not api_id:
        print("❌ Could not find API Gateway. Exiting.")
        sys.exit(1)
    
    # Get root resource
    root_resource_id = get_root_resource(api_id)
    
    if not root_resource_id:
        print("❌ Could not find root resource. Exiting.")
        sys.exit(1)
    
    print(f"\n" + "=" * 70)
    print("READY TO CREATE ENDPOINT")
    print("=" * 70)
    print(f"API Gateway: {api_name} ({api_id})")
    print(f"Lambda: {LAMBDA_FUNCTION_NAME}")
    print(f"New Endpoint: /log-csv-error (POST)")
    print("=" * 70)
    
    # Confirm
    proceed = input("\nProceed? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("❌ Cancelled by user.")
        sys.exit(0)
    
    # Create endpoint
    resource_id = create_log_csv_error_endpoint(api_id, root_resource_id, lambda_uri)
    
    # Add Lambda permission
    add_lambda_permission(api_id, lambda_arn)
    
    # Deploy
    print()
    deploy = input("Deploy changes now? (y/n): ").strip().lower()
    
    if deploy == 'y':
        stage = input("Enter stage name (press Enter for 'prod'): ").strip() or 'prod'
        deploy_api(api_id, stage)
        
        # Success message
        print("\n" + "=" * 70)
        print("✅ SUCCESS! ENDPOINT DEPLOYED")
        print("=" * 70)
        print(f"\nYour new endpoint is live at:")
        print(f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{stage}/log-csv-error")
        print()
        print("🧪 Test it with:")
        print(f"""
curl -X POST https://{api_id}.execute-api.{REGION}.amazonaws.com/{stage}/log-csv-error \\
  -H "Content-Type: application/json" \\
  -d '{{"row": 5, "error": "Test error", "rawLine": "test,line,data"}}'
        """)
        print("\n📊 View logs in CloudWatch:")
        print(f"   Log Group: /aws/lambda/{LAMBDA_FUNCTION_NAME}")
        print(f"   Search for: ****CSV****")
        print()
        print("📝 Log format will show:")
        print("   🚨🚨🚨🚨 ****CSV**** PARSE ERROR DETECTED ****CSV**** 🚨🚨🚨🚨")
        print("   📍 CSV ROW NUMBER: [row number]")
        print("   ❌ ERROR MESSAGE: [error details]")
        print("   📄 ACTUAL CSV ROW CONTENT: [full row data]")
        print()
        print("✅ Your CSV uploads will now automatically log parsing errors!")
        
    else:
        print("\n⚠️  Endpoint created but NOT deployed.")
        print(f"   To deploy manually:")
        print(f"   aws apigateway create-deployment --rest-api-id {api_id} --stage-name prod --region {REGION}")
    
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

