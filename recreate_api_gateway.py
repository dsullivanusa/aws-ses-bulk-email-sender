#!/usr/bin/env python3
"""
Recreate Private API Gateway
Creates new PRIVATE API Gateway with all endpoints and Lambda integrations

IMPORTANT: Private API Gateways require a VPC Endpoint to be accessible.
- The API can only be accessed from within the VPC via the VPC endpoint
- You need to create a VPC endpoint for execute-api service in your VPC
- Update the resource policy below if you want to restrict access to specific VPC endpoints
"""

import boto3
import json
import time

REGION = 'us-gov-west-1'
API_NAME = 'bulk-email-api'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'
STAGE_NAME = 'prod'

# Get AWS account ID
sts = boto3.client('sts', region_name=REGION)
ACCOUNT_ID = sts.get_caller_identity()['Account']

def create_api_gateway():
    """Create new API Gateway with all endpoints"""
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    print("="*80)
    print("RECREATING API GATEWAY")
    print("="*80)
    print(f"\nAPI Name: {API_NAME}")
    print(f"Lambda Function: {LAMBDA_FUNCTION_NAME}")
    print(f"Region: {REGION}")
    print(f"Account ID: {ACCOUNT_ID}")
    print()
    
    # Step 1: Create REST API (PRIVATE)
    print("Step 1: Creating Private REST API...")
    api_response = apigateway.create_rest_api(
        name=API_NAME,
        description='Bulk Email Campaign Management API - Private',
        endpointConfiguration={
            'types': ['PRIVATE']
        }
    )
    
    api_id = api_response['id']
    print(f"✅ Private API Created: {api_id}")
    
    # Get root resource
    resources_response = apigateway.get_resources(restApiId=api_id)
    root_id = resources_response['items'][0]['id']
    print(f"✅ Root Resource ID: {root_id}")
    
    # Step 2: Create resources (paths)
    print("\nStep 2: Creating resources...")
    resources = {}
    
    # Create /config
    config_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='config'
    )
    resources['config'] = config_resource['id']
    print(f"✅ Created /config")
    
    # Create /contacts
    contacts_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='contacts'
    )
    resources['contacts'] = contacts_resource['id']
    print(f"✅ Created /contacts")
    
    # Create /contacts/batch
    contacts_batch_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=resources['contacts'],
        pathPart='batch'
    )
    resources['contacts_batch'] = contacts_batch_resource['id']
    print(f"✅ Created /contacts/batch")
    
    # Create /contacts/search
    contacts_search_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=resources['contacts'],
        pathPart='search'
    )
    resources['contacts_search'] = contacts_search_resource['id']
    print(f"✅ Created /contacts/search")
    
    # Create /groups
    groups_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='groups'
    )
    resources['groups'] = groups_resource['id']
    print(f"✅ Created /groups")
    
    # Create /upload-attachment
    upload_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='upload-attachment'
    )
    resources['upload'] = upload_resource['id']
    print(f"✅ Created /upload-attachment")
    
    # Create /campaign
    campaign_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='campaign'
    )
    resources['campaign'] = campaign_resource['id']
    print(f"✅ Created /campaign")
    
    # Create /campaign/{campaign_id}
    campaign_id_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=resources['campaign'],
        pathPart='{campaign_id}'
    )
    resources['campaign_id'] = campaign_id_resource['id']
    print(f"✅ Created /campaign/{{campaign_id}}")
    
    # Lambda URI
    lambda_uri = f"arn:aws-us-gov:apigateway:{REGION}:lambda:path/2015-03-31/functions/arn:aws-us-gov:lambda:{REGION}:{ACCOUNT_ID}:function:{LAMBDA_FUNCTION_NAME}/invocations"
    
    # Step 3: Create methods and integrations
    print("\nStep 3: Creating methods and Lambda integrations...")
    
    methods_to_create = [
        # Root - Web UI
        (root_id, 'GET', '/'),
        
        # Config
        (resources['config'], 'GET', '/config'),
        (resources['config'], 'POST', '/config'),
        
        # Contacts
        (resources['contacts'], 'GET', '/contacts'),
        (resources['contacts'], 'POST', '/contacts'),
        (resources['contacts'], 'PUT', '/contacts'),
        (resources['contacts'], 'DELETE', '/contacts'),
        
        # Contacts Batch
        (resources['contacts_batch'], 'POST', '/contacts/batch'),
        
        # Contacts Search
        (resources['contacts_search'], 'POST', '/contacts/search'),
        
        # Groups
        (resources['groups'], 'GET', '/groups'),
        
        # Upload Attachment
        (resources['upload'], 'POST', '/upload-attachment'),
        
        # Campaign
        (resources['campaign'], 'POST', '/campaign'),
        (resources['campaign_id'], 'GET', '/campaign/{campaign_id}'),
    ]
    
    for resource_id, http_method, path in methods_to_create:
        # Create method
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        # Create integration
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )
        
        print(f"✅ Created {http_method} {path}")
    
    # Step 4: Enable CORS
    print("\nStep 4: Enabling CORS...")
    
    cors_resources = [
        root_id,
        resources['config'],
        resources['contacts'],
        resources['contacts_batch'],
        resources['contacts_search'],
        resources['groups'],
        resources['upload'],
        resources['campaign'],
        resources['campaign_id']
    ]
    
    for resource_id in cors_resources:
        try:
            # Create OPTIONS method
            apigateway.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE'
            )
            
            # Create mock integration
            apigateway.put_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={
                    'application/json': '{"statusCode": 200}'
                }
            )
            
            # Create method response
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
            
            # Create integration response
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
        except Exception as e:
            pass  # OPTIONS might already exist
    
    print(f"✅ CORS enabled")
    
    # Step 5: Add Lambda permissions
    print("\nStep 5: Adding Lambda invoke permissions...")
    
    permission_methods = ['GET', 'POST', 'PUT', 'DELETE']
    permission_paths = [
        '/',
        '/config',
        '/contacts',
        '/contacts/batch',
        '/contacts/search',
        '/groups',
        '/upload-attachment',
        '/campaign',
        '/campaign/{campaign_id}'
    ]
    
    for path in permission_paths:
        for method in permission_methods:
            try:
                statement_id = f"apigateway-{method}-{path.replace('/', '-').replace('{', '').replace('}', '')}-{int(time.time())}"
                
                lambda_client.add_permission(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    StatementId=statement_id,
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f"arn:aws-us-gov:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/{method}{path}"
                )
            except lambda_client.exceptions.ResourceConflictException:
                pass  # Permission already exists
            except Exception as e:
                pass  # Some combinations don't exist
    
    print(f"✅ Lambda permissions added")
    
    # Step 6: Set Private API Resource Policy
    print("\nStep 6: Setting Private API resource policy...")
    
    # Create a resource policy that allows access from your VPC endpoint
    # You can also allow access from specific VPC endpoints or allow all
    resource_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": f"arn:aws-us-gov:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*"
            }
        ]
    }
    
    try:
        apigateway.update_rest_api(
            restApiId=api_id,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/policy',
                    'value': json.dumps(resource_policy)
                }
            ]
        )
        print(f"✅ Private API resource policy set")
    except Exception as e:
        print(f"⚠️  Warning: Could not set resource policy: {str(e)}")
    
    # Step 7: Deploy API
    print("\nStep 7: Deploying API...")
    deployment = apigateway.create_deployment(
        restApiId=api_id,
        stageName=STAGE_NAME,
        description='Initial deployment'
    )
    print(f"✅ API deployed to stage: {STAGE_NAME}")
    
    # Step 8: Save configuration
    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}"
    
    config = {
        'api_id': api_id,
        'api_name': API_NAME,
        'region': REGION,
        'stage': STAGE_NAME,
        'api_url': api_url,
        'lambda_function': LAMBDA_FUNCTION_NAME,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'endpoints': {
            'web_ui': f"{api_url}/",
            'config_get': f"{api_url}/config",
            'config_post': f"{api_url}/config",
            'contacts_get': f"{api_url}/contacts",
            'contacts_post': f"{api_url}/contacts",
            'contacts_put': f"{api_url}/contacts",
            'contacts_delete': f"{api_url}/contacts",
            'contacts_batch': f"{api_url}/contacts/batch",
            'contacts_search': f"{api_url}/contacts/search",
            'groups': f"{api_url}/groups",
            'upload_attachment': f"{api_url}/upload-attachment",
            'campaign_post': f"{api_url}/campaign",
            'campaign_get': f"{api_url}/campaign/{{campaign_id}}"
        }
    }
    
    with open('api_gateway_info.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n" + "="*80)
    print("✅ PRIVATE API GATEWAY CREATED SUCCESSFULLY!")
    print("="*80)
    print(f"\nAPI ID:       {api_id}")
    print(f"API Type:     PRIVATE")
    print(f"API URL:      {api_url}")
    print(f"Web UI:       {api_url}/")
    print(f"\n⚠️  IMPORTANT: This is a PRIVATE API")
    print(f"   - Can only be accessed from within your VPC via VPC Endpoint")
    print(f"   - You need a VPC endpoint for execute-api service")
    print(f"\nConfiguration saved to: api_gateway_info.json")
    print("\n" + "="*80)
    print("ENDPOINTS CREATED:")
    print("="*80)
    print(f"GET    {api_url}/                           (Web UI)")
    print(f"GET    {api_url}/config                     (Get email config)")
    print(f"POST   {api_url}/config                     (Save email config)")
    print(f"GET    {api_url}/contacts                   (Get all contacts)")
    print(f"POST   {api_url}/contacts                   (Add contact)")
    print(f"PUT    {api_url}/contacts                   (Update contact)")
    print(f"DELETE {api_url}/contacts                   (Delete contact)")
    print(f"POST   {api_url}/contacts/batch             (Batch add contacts)")
    print(f"POST   {api_url}/contacts/search            (Search contacts)")
    print(f"GET    {api_url}/groups                     (Get groups)")
    print(f"POST   {api_url}/upload-attachment          (Upload attachment)")
    print(f"POST   {api_url}/campaign                   (Send campaign)")
    print(f"GET    {api_url}/campaign/{{campaign_id}}    (Get campaign status)")
    print("="*80)
    print("\nNext Steps:")
    print("1. Ensure you have a VPC Endpoint for execute-api service")
    print("2. Access the API only from within your VPC")
    print("3. Test Web UI: Open the API URL from within your VPC")
    print("4. Update any saved bookmarks with new URL")
    print("5. Test sending a campaign")
    print("="*80)
    
    return config

def main():
    print()
    print("⚠️  This will create a NEW PRIVATE API Gateway")
    print("   Private APIs require VPC Endpoint for access")
    response = input(f"\nContinue? (yes/no): ")
    
    if response.lower() == 'yes':
        try:
            config = create_api_gateway()
            
            print("\n✅ Setup complete!")
            print(f"\nYour new Web UI URL:")
            print(f"  {config['api_url']}/")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("Cancelled.")

if __name__ == '__main__':
    main()

