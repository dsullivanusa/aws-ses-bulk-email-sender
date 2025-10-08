#!/usr/bin/env python3
"""
Fix 403 Error - API Gateway Configuration
The 403 error is caused by the API Gateway being configured as PRIVATE, 
which requires VPC endpoint access but the web UI is accessed from public internet.

This script will:
1. Check current API Gateway configuration
2. Convert from PRIVATE to REGIONAL (public) API Gateway
3. Update resource policies to allow public access
4. Redeploy the API
"""

import boto3
import json
import time

REGION = 'us-gov-west-1'

def get_current_api_gateway():
    """Get current API Gateway configuration"""
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    print("="*80)
    print("🔍 CHECKING CURRENT API GATEWAY CONFIGURATION")
    print("="*80)
    
    # Get all API Gateways
    apis = apigateway.get_rest_apis()['items']
    
    # Look for bulk email API
    target_apis = [
        'bulk-email-api',
        'vpc-smtp-bulk-email-api', 
        'bulk-email-sender-api',
        'email-api'
    ]
    
    api_id = None
    api_name = None
    api_endpoint_config = None
    
    for api in apis:
        if api['name'] in target_apis:
            api_id = api['id']
            api_name = api['name']
            api_endpoint_config = api.get('endpointConfiguration', {})
            break
    
    if not api_id:
        print("❌ No bulk email API Gateway found")
        print("Available APIs:")
        for api in apis:
            print(f"   - {api['name']} ({api['id']})")
        return None, None, None
    
    print(f"✅ Found API Gateway: {api_name} ({api_id})")
    
    # Check endpoint configuration
    if api_endpoint_config:
        endpoint_types = api_endpoint_config.get('types', [])
        print(f"   Endpoint Types: {endpoint_types}")
        
        if 'PRIVATE' in endpoint_types:
            print("❌ API Gateway is configured as PRIVATE - this causes 403 errors from public internet")
            return api_id, api_name, 'PRIVATE'
        elif 'REGIONAL' in endpoint_types:
            print("✅ API Gateway is configured as REGIONAL - should work from public internet")
            return api_id, api_name, 'REGIONAL'
        else:
            print(f"⚠️  Unknown endpoint configuration: {endpoint_types}")
            return api_id, api_name, 'UNKNOWN'
    else:
        print("⚠️  No endpoint configuration found")
        return api_id, api_name, None

def fix_api_gateway_endpoint(api_id, api_name):
    """Convert API Gateway from PRIVATE to REGIONAL"""
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    print(f"\n" + "="*80)
    print(f"🔧 FIXING API GATEWAY ENDPOINT CONFIGURATION")
    print("="*80)
    
    try:
        # Update endpoint configuration to REGIONAL (public)
        apigateway.update_rest_api(
            restApiId=api_id,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/endpointConfiguration/types/0',
                    'value': 'REGIONAL'
                }
            ]
        )
        
        print("✅ Updated endpoint configuration to REGIONAL")
        
        # Remove resource policy that restricts access
        try:
            apigateway.update_rest_api(
                restApiId=api_id,
                patchOperations=[
                    {
                        'op': 'remove',
                        'path': '/policy'
                    }
                ]
            )
            print("✅ Removed restrictive resource policy")
        except Exception as e:
            print(f"⚠️  Could not remove resource policy: {e}")
        
        # Redeploy API to apply changes
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Fix 403 error - convert to public API'
        )
        
        print("✅ Redeployed API to apply changes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating API Gateway: {e}")
        return False

def test_api_access(api_id):
    """Test if API is now accessible"""
    
    print(f"\n" + "="*80)
    print(f"🧪 TESTING API ACCESS")
    print("="*80)
    
    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    
    print(f"API URL: {api_url}")
    
    # Test with curl equivalent using Python
    try:
        import urllib.request
        import urllib.parse
        
        # Test root endpoint (web UI)
        request = urllib.request.Request(f"{api_url}/")
        request.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.getcode()
            content_type = response.headers.get('content-type', '')
            
            print(f"✅ Root endpoint test: {status_code} ({content_type})")
            
            if status_code == 200 and 'text/html' in content_type:
                print("✅ Web UI should now be accessible")
                return True
            else:
                print(f"❌ Unexpected response: {status_code}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def main():
    """Main function"""
    
    print("🚀 FIXING 403 ERROR - API GATEWAY CONFIGURATION")
    print("="*80)
    print()
    print("Problem: API Gateway is configured as PRIVATE, causing 403 errors")
    print("Solution: Convert to REGIONAL (public) API Gateway")
    print()
    
    # Step 1: Check current configuration
    api_id, api_name, endpoint_type = get_current_api_gateway()
    
    if not api_id:
        print("\n❌ Cannot proceed - no API Gateway found")
        return
    
    # Step 2: Fix configuration if needed
    if endpoint_type == 'PRIVATE':
        print(f"\n🔧 Converting {api_name} from PRIVATE to REGIONAL...")
        success = fix_api_gateway_endpoint(api_id, api_name)
        
        if success:
            # Step 3: Test access
            time.sleep(5)  # Wait for deployment to complete
            test_success = test_api_access(api_id)
            
            if test_success:
                print(f"\n✅ SUCCESS! 403 error should be fixed")
                print(f"   Web UI URL: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod/")
                print(f"   API URL: https://{api_id}.execute-api.{REGION}.amazonaws.com/prod")
                print()
                print("Next steps:")
                print("1. Test the web UI in your browser")
                print("2. Try loading contacts and other data")
                print("3. If still having issues, check browser console for errors")
            else:
                print(f"\n❌ API access test failed - may need additional configuration")
        else:
            print(f"\n❌ Failed to fix API Gateway configuration")
    else:
        print(f"\n✅ API Gateway is already configured correctly ({endpoint_type})")
        print("The 403 error may be caused by other issues:")
        print("1. Check IAM permissions for Lambda function")
        print("2. Check DynamoDB table permissions")
        print("3. Check Lambda function logs for errors")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


