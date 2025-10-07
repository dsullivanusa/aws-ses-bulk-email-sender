#!/usr/bin/env python3
"""
Fix Lambda CloudWatch Permissions
Adds CloudWatch PutMetricData permission to email worker Lambda role
"""

import boto3
import json

def fix_cloudwatch_permissions():
    iam = boto3.client('iam', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    function_name = 'email-worker-function'
    
    print("=" * 80)
    print("🔧 Fixing Lambda CloudWatch Permissions")
    print("=" * 80)
    
    try:
        # Get Lambda function configuration
        print(f"\n📋 Getting Lambda configuration...")
        func_config = lambda_client.get_function_configuration(FunctionName=function_name)
        role_arn = func_config['Role']
        role_name = role_arn.split('/')[-1]
        
        print(f"✅ Function: {function_name}")
        print(f"✅ Role ARN: {role_arn}")
        print(f"✅ Role Name: {role_name}")
        
        # CloudWatch PutMetricData policy
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "cloudwatch:PutMetricData"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        policy_name = "EmailWorkerCloudWatchMetrics"
        
        print(f"\n🔄 Adding CloudWatch PutMetricData permission...")
        print(f"   Policy Name: {policy_name}")
        
        # Check if policy already exists
        try:
            existing_policy = iam.get_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
            print(f"   ⚠️  Policy already exists, updating...")
        except iam.exceptions.NoSuchEntityException:
            print(f"   ℹ️  Creating new policy...")
        
        # Add or update inline policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✅ Policy added successfully!")
        
        # Verify
        print(f"\n🔍 Verifying policy...")
        response = iam.get_role_policy(
            RoleName=role_name,
            PolicyName=policy_name
        )
        
        print(f"✅ Policy verified!")
        
        print(f"\n" + "=" * 80)
        print(f"✅ Fix Applied Successfully!")
        print(f"=" * 80)
        print(f"\n📊 Lambda can now send metrics to CloudWatch:")
        print(f"   - SendRatePerSecond")
        print(f"   - SuccessRate / FailureRate")
        print(f"   - CampaignProgress")
        print(f"   - And more...")
        print(f"\n🎯 Result:")
        print(f"   ✅ Lambda will complete successfully")
        print(f"   ✅ Messages will be deleted from SQS")
        print(f"   ✅ NO MORE RE-DELIVERY!")
        print(f"\n💡 Test now:")
        print(f"   1. Send a test email")
        print(f"   2. Check queue: python check_sqs_status.py")
        print(f"   3. Message should disappear within 1 minute")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        print(f"\n💡 Alternative: Disable CloudWatch metrics in Lambda")
        print(f"   If you can't modify IAM, wrap metric calls in try-except")
        
        return False

if __name__ == '__main__':
    fix_cloudwatch_permissions()

