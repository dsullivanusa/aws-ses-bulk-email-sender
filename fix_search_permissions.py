#!/usr/bin/env python3
"""
Add Lambda invoke permission for /contacts/search endpoint
"""

import boto3
import time

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def fix_permissions():
    """Add Lambda permission for search endpoint"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    sts = boto3.client('sts', region_name=REGION)
    
    # Get account ID
    account_id = sts.get_caller_identity()['Account']
    
    print("🔍 Finding API Gateway...")
    
    # Find the API
    apis = apigateway.get_rest_apis()
    api_id = None
    api_name = None
    
    for api in apis['items']:
        if 'bulk-email' in api['name'].lower():
            api_id = api['id']
            api_name = api['name']
            break
    
    if not api_id:
        print("❌ API Gateway not found!")
        return
    
    print(f"✅ Found API: {api_name} (ID: {api_id})")
    print(f"   Account ID: {account_id}")
    
    # Add Lambda permission for /contacts/search POST
    print("\n🔧 Adding Lambda invoke permission for /contacts/search...")
    
    statement_id = f"apigateway-search-{int(time.time())}"
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/POST/contacts/search"
        )
        print(f"✅ Permission added successfully!")
        print(f"   Statement ID: {statement_id}")
        
    except lambda_client.exceptions.ResourceConflictException:
        print("⚠️  Permission already exists (that's OK)")
        
        # Try with wildcard
        statement_id = f"apigateway-search-wildcard-{int(time.time())}"
        try:
            lambda_client.add_permission(
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/*/contacts/search"
            )
            print(f"✅ Added wildcard permission")
        except lambda_client.exceptions.ResourceConflictException:
            print("✅ Wildcard permission already exists")
        
    except Exception as e:
        print(f"❌ Error adding permission: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Deploy API to activate changes
    print("\n🚀 Deploying API to 'prod' stage...")
    try:
        apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Added search endpoint permissions'
        )
        print("✅ API deployed successfully!")
    except Exception as e:
        print(f"⚠️  Deployment warning: {str(e)}")
    
    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    print(f"\n🌐 API URL: {api_url}/contacts/search")
    print("\n✅ Search endpoint should now work!")
    print("   Test in browser with hard refresh (Ctrl+Shift+R)")

if __name__ == '__main__':
    print("\n🔧 Fixing Lambda Permissions for Search Endpoint\n")
    print("="*80)
    fix_permissions()
    print("="*80)

