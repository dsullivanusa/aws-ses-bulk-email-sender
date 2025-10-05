#!/usr/bin/env python3
"""
Clean up Lambda permissions and add single wildcard permission
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def cleanup_permissions():
    """Remove all API Gateway permissions and add a single wildcard"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    apigateway = boto3.client('apigateway', region_name=REGION)
    sts = boto3.client('sts', region_name=REGION)
    
    account_id = sts.get_caller_identity()['Account']
    
    print("🔍 Finding API Gateway...")
    apis = apigateway.get_rest_apis()
    api_id = None
    
    for api in apis['items']:
        if 'bulk-email' in api['name'].lower():
            api_id = api['id']
            break
    
    if not api_id:
        print("❌ API Gateway not found!")
        return
    
    print(f"✅ Found API ID: {api_id}")
    
    # Get current policy
    print("\n📋 Getting current Lambda permissions...")
    try:
        policy_response = lambda_client.get_policy(FunctionName=LAMBDA_FUNCTION_NAME)
        policy = json.loads(policy_response['Policy'])
        statements = policy.get('Statement', [])
        
        print(f"   Current policy has {len(statements)} statement(s)")
        print(f"   Policy size: {len(policy_response['Policy'])} bytes")
        
        # Find API Gateway related statements
        apigateway_statements = []
        for stmt in statements:
            sid = stmt.get('Sid', '')
            if 'apigateway' in sid.lower() or stmt.get('Principal', {}).get('Service') == 'apigateway.amazonaws.com':
                apigateway_statements.append(sid)
        
        print(f"\n🗑️  Found {len(apigateway_statements)} API Gateway permission(s) to remove:")
        for sid in apigateway_statements:
            print(f"   - {sid}")
        
        # Remove old API Gateway permissions
        print("\n🧹 Removing old API Gateway permissions...")
        removed = 0
        for sid in apigateway_statements:
            try:
                lambda_client.remove_permission(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    StatementId=sid
                )
                print(f"   ✅ Removed: {sid}")
                removed += 1
            except Exception as e:
                print(f"   ⚠️  Could not remove {sid}: {e}")
        
        print(f"\n✅ Removed {removed} permission(s)")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print("   No existing policy found (that's OK)")
    except Exception as e:
        print(f"   Error reading policy: {e}")
    
    # Add single wildcard permission
    print("\n➕ Adding single wildcard permission for all API Gateway endpoints...")
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId='apigateway-invoke-all',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/*/*"
        )
        print("✅ Wildcard permission added successfully!")
        print(f"   Covers: arn:aws-us-gov:execute-api:{REGION}:{account_id}:{api_id}/*/*/*")
        print("   This allows all methods on all paths")
        
    except lambda_client.exceptions.ResourceConflictException:
        print("✅ Wildcard permission already exists")
    except Exception as e:
        print(f"❌ Error adding permission: {e}")
        return
    
    # Verify new policy size
    print("\n📏 Checking new policy size...")
    try:
        policy_response = lambda_client.get_policy(FunctionName=LAMBDA_FUNCTION_NAME)
        policy = json.loads(policy_response['Policy'])
        policy_size = len(policy_response['Policy'])
        
        print(f"✅ New policy size: {policy_size} bytes (limit: 20480)")
        print(f"   Statements: {len(policy.get('Statement', []))}")
        
        if policy_size < 20480:
            print("   ✅ Within limit!")
        else:
            print("   ⚠️  Still too large - may need manual cleanup")
            
    except Exception as e:
        print(f"   Could not verify: {e}")
    
    print("\n" + "="*80)
    print("✅ CLEANUP COMPLETE!")
    print("="*80)
    print("\n🎉 All API Gateway endpoints should now work, including /contacts/search")
    print("   Test in browser with hard refresh (Ctrl+Shift+R)\n")

if __name__ == '__main__':
    print("\n🧹 Cleaning Up Lambda Permissions\n")
    print("="*80)
    
    response = input("⚠️  This will remove old API Gateway permissions. Continue? (yes/no): ")
    if response.lower() == 'yes':
        cleanup_permissions()
    else:
        print("Cancelled.")

