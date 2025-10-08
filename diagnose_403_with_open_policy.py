#!/usr/bin/env python3
"""
Diagnose 403 Error When API Gateway Policy is Already Open
If the resource policy has "Resource": "*" and "Principal": "*" but still getting 403 errors,
the issue is likely one of these:
1. VPC Endpoint requirement (PRIVATE API)
2. IAM Authorization on methods
3. Lambda permission issues
4. WAF rules blocking requests
5. Missing or incorrect deployment
"""

import boto3
import json

REGION = 'us-gov-west-1'

def check_api_gateway_config():
    """Check detailed API Gateway configuration"""
    
    print("="*80)
    print("🔍 DETAILED API GATEWAY DIAGNOSIS")
    print("="*80)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    # Find API Gateway
    apis = apigateway.get_rest_apis()['items']
    api_id = None
    api_name = None
    
    for api in apis:
        if 'bulk-email' in api['name'].lower() or 'vpc-smtp' in api['name'].lower():
            api_id = api['id']
            api_name = api['name']
            break
    
    if not api_id:
        print("❌ No API Gateway found")
        return None
    
    print(f"✅ Found API Gateway: {api_name} ({api_id})")
    
    # Get full API details
    api_details = apigateway.get_rest_api(restApiId=api_id)
    
    # Check endpoint configuration
    endpoint_config = api_details.get('endpointConfiguration', {})
    endpoint_types = endpoint_config.get('types', [])
    
    print(f"\n📋 ENDPOINT CONFIGURATION:")
    print(f"   Type: {endpoint_types}")
    
    if 'PRIVATE' in endpoint_types:
        print("   ⚠️  API is PRIVATE - requires VPC Endpoint access")
        print("   🔑 This is likely the cause of 403 errors!")
        check_vpc_endpoint_requirement(api_id)
    elif 'REGIONAL' in endpoint_types:
        print("   ✅ API is REGIONAL - publicly accessible")
    elif 'EDGE' in endpoint_types:
        print("   ✅ API is EDGE - publicly accessible")
    
    # Check resource policy
    policy = api_details.get('policy', None)
    if policy:
        policy_obj = json.loads(policy)
        print(f"\n📋 RESOURCE POLICY:")
        print(f"   Statements: {len(policy_obj.get('Statement', []))}")
        
        for i, statement in enumerate(policy_obj.get('Statement', []), 1):
            print(f"\n   Statement {i}:")
            print(f"      Effect: {statement.get('Effect')}")
            print(f"      Principal: {statement.get('Principal')}")
            print(f"      Action: {statement.get('Action')}")
            print(f"      Resource: {statement.get('Resource')}")
            
            condition = statement.get('Condition')
            if condition:
                print(f"      Condition: {json.dumps(condition, indent=10)}")
                
                # Check for IP restrictions
                if 'IpAddress' in condition:
                    print("      ⚠️  IP Address restriction found!")
                    ip_ranges = condition.get('IpAddress', {}).get('aws:sourceIp', [])
                    print(f"      Allowed IP ranges: {ip_ranges}")
                
                # Check for VPC Endpoint restrictions
                if 'StringEquals' in condition and 'aws:sourceVpce' in condition.get('StringEquals', {}):
                    vpce = condition['StringEquals']['aws:sourceVpce']
                    print(f"      ⚠️  VPC Endpoint restriction found!")
                    print(f"      Required VPC Endpoint: {vpce}")
    else:
        print(f"\n📋 RESOURCE POLICY:")
        print(f"   ⚠️  No resource policy found")
    
    # Check authorization on methods
    check_method_authorization(apigateway, api_id)
    
    # Check Lambda permissions
    check_lambda_permissions(api_id)
    
    # Check deployment stage
    check_deployment_stage(apigateway, api_id)
    
    return api_id

def check_vpc_endpoint_requirement(api_id):
    """Check if VPC endpoint is required and configured"""
    
    print(f"\n📋 VPC ENDPOINT CHECK:")
    
    ec2 = boto3.client('ec2', region_name=REGION)
    
    # Check if VPC endpoints exist
    try:
        vpc_endpoints = ec2.describe_vpc_endpoints(
            Filters=[
                {'Name': 'service-name', 'Values': [f'com.amazonaws.{REGION}.execute-api']}
            ]
        )
        
        if vpc_endpoints['VpcEndpoints']:
            for vpce in vpc_endpoints['VpcEndpoints']:
                print(f"   ✅ VPC Endpoint found: {vpce['VpcEndpointId']}")
                print(f"      State: {vpce['State']}")
                print(f"      VPC: {vpce['VpcId']}")
        else:
            print("   ❌ No VPC Endpoint found for execute-api service")
            print("   🔑 PRIVATE APIs require VPC Endpoint!")
            print("\n   💡 SOLUTION:")
            print("      Run: python setup_private_api_access.py")
            print("      Or create VPC endpoint manually")
    except Exception as e:
        print(f"   ⚠️  Error checking VPC endpoints: {e}")

def check_method_authorization(apigateway, api_id):
    """Check if methods have authorization requirements"""
    
    print(f"\n📋 METHOD AUTHORIZATION CHECK:")
    
    try:
        # Get all resources
        resources = apigateway.get_resources(restApiId=api_id)
        
        auth_issues = []
        for resource in resources['items']:
            path = resource.get('path', '/')
            
            # Check each HTTP method on this resource
            for method_key in resource.get('resourceMethods', {}).keys():
                method = apigateway.get_method(
                    restApiId=api_id,
                    resourceId=resource['id'],
                    httpMethod=method_key
                )
                
                auth_type = method.get('authorizationType', 'NONE')
                
                if auth_type != 'NONE':
                    auth_issues.append({
                        'path': path,
                        'method': method_key,
                        'auth_type': auth_type
                    })
        
        if auth_issues:
            print("   ⚠️  Authorization required on some methods:")
            for issue in auth_issues:
                print(f"      {issue['method']} {issue['path']} - Auth: {issue['auth_type']}")
            print("\n   🔑 This could cause 403 errors if auth is not provided")
        else:
            print("   ✅ All methods use authorizationType: NONE")
    
    except Exception as e:
        print(f"   ⚠️  Error checking methods: {e}")

def check_lambda_permissions(api_id):
    """Check if Lambda has permissions for API Gateway"""
    
    print(f"\n📋 LAMBDA PERMISSIONS CHECK:")
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        # Get Lambda function policy
        policy_response = lambda_client.get_policy(
            FunctionName='bulk-email-api-function'
        )
        
        policy = json.loads(policy_response['Policy'])
        statements = policy.get('Statement', [])
        
        # Check for API Gateway permissions
        api_perms = [s for s in statements if 'apigateway' in s.get('Principal', {}).get('Service', '')]
        
        if api_perms:
            print(f"   ✅ Found {len(api_perms)} API Gateway permission(s)")
            
            # Check if current API ID is in the permissions
            has_current_api = False
            for perm in api_perms:
                source_arn = perm.get('Condition', {}).get('ArnLike', {}).get('AWS:SourceArn', '')
                if api_id in source_arn:
                    has_current_api = True
                    print(f"   ✅ Permission exists for current API: {api_id}")
                    break
            
            if not has_current_api:
                print(f"   ⚠️  No permission found for API ID: {api_id}")
                print("   🔑 Lambda may not be invokable by this API Gateway")
        else:
            print("   ❌ No API Gateway permissions found on Lambda")
            print("   🔑 This will cause 403 errors!")
            print("\n   💡 SOLUTION:")
            print("      Run: python fix_lambda_permissions.py")
    
    except lambda_client.exceptions.ResourceNotFoundException:
        print("   ❌ Lambda function 'bulk-email-api-function' not found")
    except Exception as e:
        print(f"   ⚠️  Error checking Lambda permissions: {e}")

def check_deployment_stage(apigateway, api_id):
    """Check if API is deployed to stage"""
    
    print(f"\n📋 DEPLOYMENT STAGE CHECK:")
    
    try:
        stages = apigateway.get_stages(restApiId=api_id)
        
        if not stages.get('item', []):
            print("   ❌ No deployment stages found!")
            print("   🔑 API must be deployed to a stage")
            print("\n   💡 SOLUTION:")
            print("      aws apigateway create-deployment --rest-api-id {api_id} --stage-name prod --region us-gov-west-1")
        else:
            for stage in stages['item']:
                print(f"   ✅ Stage: {stage['stageName']}")
                print(f"      Created: {stage.get('createdDate', 'N/A')}")
                print(f"      Last Updated: {stage.get('lastUpdatedDate', 'N/A')}")
    
    except Exception as e:
        print(f"   ⚠️  Error checking deployment: {e}")

def provide_solution_summary(api_id):
    """Provide solution summary based on findings"""
    
    print(f"\n" + "="*80)
    print("💡 SOLUTION SUMMARY")
    print("="*80)
    
    print(f"\nBased on the diagnosis, the 403 error is likely caused by:")
    print(f"\n1. ⚠️  PRIVATE API Gateway Configuration")
    print(f"   - Your API is configured as PRIVATE")
    print(f"   - Even with open resource policy (Principal: *, Resource: *)")
    print(f"   - PRIVATE APIs REQUIRE VPC Endpoint access")
    print(f"")
    print(f"   SOLUTION:")
    print(f"   a) Create VPC Endpoint:")
    print(f"      python setup_private_api_access.py")
    print(f"")
    print(f"   b) OR Convert to REGIONAL (public) API:")
    print(f"      aws apigateway update-rest-api \\")
    print(f"        --rest-api-id {api_id} \\")
    print(f"        --region {REGION} \\")
    print(f"        --patch-ops op=replace,path=/endpointConfiguration/types/0,value=REGIONAL")
    print(f"")
    print(f"2. ⚠️  IP Address Restrictions in Resource Policy")
    print(f"   - Policy may have IP-based conditions")
    print(f"   - Your IP may not be in allowed ranges")
    print(f"")
    print(f"   SOLUTION:")
    print(f"   python fix_private_network_access.py")
    print(f"")
    print(f"3. ⚠️  Missing Lambda Permissions")
    print(f"   - Lambda may not have permission for this API Gateway")
    print(f"")
    print(f"   SOLUTION:")
    print(f"   aws lambda add-permission \\")
    print(f"     --function-name bulk-email-api-function \\")
    print(f"     --statement-id apigateway-invoke-{int(time.time())} \\")
    print(f"     --action lambda:InvokeFunction \\")
    print(f"     --principal apigateway.amazonaws.com \\")
    print(f"     --source-arn 'arn:aws-us-gov:execute-api:{REGION}:*:{api_id}/*' \\")
    print(f"     --region {REGION}")

def main():
    """Main function"""
    
    print("🚀 DIAGNOSING 403 ERROR WITH OPEN RESOURCE POLICY")
    print("="*80)
    print()
    print("When resource policy has 'Principal: *' and 'Resource: *' but still")
    print("getting 403 errors, the issue is usually the API endpoint type or")
    print("method-level restrictions.")
    print()
    
    import time
    
    api_id = check_api_gateway_config()
    
    if api_id:
        provide_solution_summary(api_id)
    
    print(f"\n" + "="*80)
    print("✅ DIAGNOSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
