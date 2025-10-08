#!/usr/bin/env python3
"""
Fix Private Network Access to Private API Gateway
Updates API Gateway resource policy to allow access from private network IP ranges

Since your web UI is accessed from a private network, we need to configure
the API Gateway resource policy to allow access from your private IP ranges.
"""

import boto3
import json
import requests
from urllib.parse import urlparse

REGION = 'us-gov-west-1'

def get_current_api_gateway():
    """Get current API Gateway configuration"""
    
    print("="*80)
    print("🔍 CHECKING CURRENT API GATEWAY CONFIGURATION")
    print("="*80)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    # Find API Gateway
    apis = apigateway.get_rest_apis()['items']
    api_id = None
    api_name = None
    
    target_names = ['bulk-email-api', 'vpc-smtp-bulk-email-api', 'bulk-email-sender-api']
    
    for api in apis:
        if any(name in api['name'].lower() for name in target_names):
            api_id = api['id']
            api_name = api['name']
            break
    
    if not api_id:
        print("❌ No bulk email API Gateway found")
        print("Available APIs:")
        for api in apis:
            print(f"   - {api['name']} ({api['id']})")
        return None, None, None
    
    print(f"✅ Found API Gateway: {api_name} ({api_id})")
    
    # Check endpoint configuration
    endpoint_config = apigateway.get_rest_api(restApiId=api_id).get('endpointConfiguration', {})
    if 'PRIVATE' in endpoint_config.get('types', []):
        print("✅ API Gateway is configured as PRIVATE")
    else:
        print("⚠️  API Gateway is not configured as PRIVATE")
    
    # Check current policy
    try:
        current_policy = apigateway.get_rest_api(restApiId=api_id).get('policy', None)
        if current_policy:
            policy_obj = json.loads(current_policy)
            print("✅ Current resource policy exists")
            print(f"   Policy statements: {len(policy_obj.get('Statement', []))}")
        else:
            print("⚠️  No resource policy found")
    except Exception as e:
        print(f"⚠️  Could not read current policy: {e}")
    
    return api_id, api_name, current_policy

def get_private_network_ranges():
    """Get common private network IP ranges"""
    
    print(f"\n" + "="*80)
    print(f"🌐 PRIVATE NETWORK IP RANGES")
    print("="*80)
    
    # Common private network ranges
    private_ranges = [
        "10.0.0.0/8",        # Class A private
        "172.16.0.0/12",     # Class B private  
        "192.168.0.0/16",    # Class C private
        "127.0.0.0/8",       # Loopback
        "169.254.0.0/16",    # Link-local
        "100.64.0.0/10",     # Carrier-grade NAT
        "198.18.0.0/15",     # Benchmarking
    ]
    
    print("📋 Common private network IP ranges:")
    for i, range_ip in enumerate(private_ranges, 1):
        print(f"   {i}. {range_ip}")
    
    print(f"\n💡 These ranges will be added to allow access from private networks.")
    print(f"   If you have specific IP ranges, you can customize them later.")
    
    return private_ranges

def update_api_gateway_policy(api_id, ip_ranges):
    """Update API Gateway resource policy to allow private network access"""
    
    print(f"\n" + "="*80)
    print(f"🔧 UPDATING API GATEWAY RESOURCE POLICY")
    print("="*80)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        # Create resource policy that allows private network access
        resource_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "execute-api:Invoke",
                    "Resource": f"arn:aws-us-gov:execute-api:{REGION}:*:{api_id}/*",
                    "Condition": {
                        "IpAddress": {
                            "aws:sourceIp": ip_ranges
                        }
                    }
                }
            ]
        }
        
        # Update API Gateway with resource policy
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
        
        print(f"✅ Updated API Gateway resource policy")
        print(f"   Allowed IP ranges: {len(ip_ranges)} ranges")
        for i, range_ip in enumerate(ip_ranges, 1):
            print(f"      {i}. {range_ip}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating API Gateway policy: {e}")
        return False

def redeploy_api(api_id):
    """Redeploy API Gateway to apply changes"""
    
    print(f"\n" + "="*80)
    print(f"🔧 REDEPLOYING API GATEWAY")
    print("="*80)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Allow private network access'
        )
        
        print(f"✅ API Gateway redeployed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error redeploying API Gateway: {e}")
        return False

def get_api_url(api_id):
    """Get API Gateway URL"""
    
    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    web_ui_url = f"{api_url}/"
    
    return api_url, web_ui_url

def test_access(api_url, web_ui_url):
    """Test API access"""
    
    print(f"\n" + "="*80)
    print(f"🧪 TESTING API ACCESS")
    print("="*80)
    
    print(f"📋 Testing URLs:")
    print(f"   API URL: {api_url}")
    print(f"   Web UI URL: {web_ui_url}")
    
    # Test API endpoints
    test_endpoints = [
        ("/", "Web UI"),
        ("/contacts?limit=1", "Contacts API"),
        ("/config", "Config API"),
        ("/groups", "Groups API")
    ]
    
    print(f"\n📋 Test Results:")
    for endpoint, name in test_endpoints:
        test_url = f"{api_url}{endpoint}"
        try:
            response = requests.get(test_url, timeout=10)
            status = response.status_code
            
            if status == 200:
                print(f"   ✅ {name}: {status} OK")
            elif status == 403:
                print(f"   ❌ {name}: {status} Forbidden (still blocked)")
            else:
                print(f"   ⚠️  {name}: {status} {response.reason}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {name}: Connection error - {e}")
        except Exception as e:
            print(f"   ❌ {name}: Error - {e}")

def main():
    """Main function"""
    
    print("🚀 FIXING PRIVATE NETWORK ACCESS TO API GATEWAY")
    print("="*80)
    print()
    print("Since your web UI is accessed from a private network, we need to")
    print("configure the API Gateway resource policy to allow access from")
    print("private network IP ranges.")
    print()
    
    # Step 1: Check current API Gateway
    api_id, api_name, current_policy = get_current_api_gateway()
    
    if not api_id:
        print("\n❌ Cannot proceed - no API Gateway found")
        return
    
    # Step 2: Get private network ranges
    ip_ranges = get_private_network_ranges()
    
    # Step 3: Update API Gateway policy
    print(f"\n🔧 Updating API Gateway policy to allow private network access...")
    policy_success = update_api_gateway_policy(api_id, ip_ranges)
    
    if not policy_success:
        print("\n❌ Failed to update API Gateway policy")
        return
    
    # Step 4: Redeploy API
    print(f"\n🔧 Redeploying API Gateway...")
    deploy_success = redeploy_api(api_id)
    
    if not deploy_success:
        print("\n❌ Failed to redeploy API Gateway")
        return
    
    # Step 5: Get URLs and test
    api_url, web_ui_url = get_api_url(api_id)
    
    print(f"\n🌐 ACCESS INFORMATION")
    print(f"="*80)
    print(f"Your API Gateway is now configured to allow access from private networks.")
    print(f"")
    print(f"📋 Access URLs:")
    print(f"   API URL: {api_url}")
    print(f"   Web UI URL: {web_ui_url}")
    print(f"")
    print(f"📋 Allowed IP Ranges:")
    for i, range_ip in enumerate(ip_ranges, 1):
        print(f"   {i}. {range_ip}")
    
    # Step 6: Test access
    import time
    time.sleep(5)  # Wait for deployment to complete
    test_access(api_url, web_ui_url)
    
    print(f"\n✅ SETUP COMPLETE!")
    print(f"="*80)
    print(f"The 403 error should now be resolved for access from private networks.")
    print(f"")
    print(f"Next steps:")
    print(f"1. Test the web UI from your private network")
    print(f"2. Try loading contacts and other data")
    print(f"3. If issues persist, check browser console for errors")
    print(f"4. Verify your network IP is within the allowed ranges")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


