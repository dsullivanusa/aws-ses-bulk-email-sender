#!/usr/bin/env python3
"""
Quick Fix for Private Network Access
Simple script to immediately fix the 403 error for private network access
"""

import boto3
import json

REGION = 'us-gov-west-1'

def quick_fix():
    """Quick fix for private network access"""
    
    print("🚀 QUICK FIX: Private Network Access to API Gateway")
    print("="*60)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    # Find API Gateway
    apis = apigateway.get_rest_apis()['items']
    api_id = None
    
    for api in apis:
        if 'bulk-email' in api['name'].lower() or 'vpc-smtp' in api['name'].lower():
            api_id = api['id']
            break
    
    if not api_id:
        print("❌ No API Gateway found")
        return
    
    print(f"✅ Found API Gateway: {api_id}")
    
    # Update policy to allow private network access
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": f"arn:aws-us-gov:execute-api:{REGION}:*:{api_id}/*",
                "Condition": {
                    "IpAddress": {
                        "aws:sourceIp": [
                            "10.0.0.0/8",
                            "172.16.0.0/12", 
                            "192.168.0.0/16",
                            "127.0.0.0/8"
                        ]
                    }
                }
            }
        ]
    }
    
    try:
        # Update API Gateway policy
        apigateway.update_rest_api(
            restApiId=api_id,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/policy',
                    'value': json.dumps(policy)
                }
            ]
        )
        
        print("✅ Updated API Gateway policy")
        
        # Redeploy
        apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Quick fix for private network access'
        )
        
        print("✅ Redeployed API Gateway")
        
        # Show URLs
        api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
        print(f"\n🌐 Access URLs:")
        print(f"   API: {api_url}")
        print(f"   Web UI: {api_url}/")
        
        print(f"\n✅ 403 error should now be fixed!")
        print(f"   Test the web UI from your private network.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_fix()


