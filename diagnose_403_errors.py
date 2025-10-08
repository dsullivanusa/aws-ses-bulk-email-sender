#!/usr/bin/env python3
"""
Comprehensive 403 Error Diagnostics for Lambda Function
"""

import boto3
import json
from datetime import datetime, timedelta

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def check_lambda_role_permissions():
    """Check Lambda function's IAM role and permissions"""
    print("🔍 Checking Lambda IAM Role Permissions...")
    print("="*80)
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        iam_client = boto3.client('iam', region_name=REGION)
        
        # Get Lambda function configuration
        function_config = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        role_arn = function_config['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        
        print(f"📋 Lambda Function: {LAMBDA_FUNCTION_NAME}")
        print(f"🔐 IAM Role: {role_name}")
        print(f"🔗 Role ARN: {role_arn}")
        
        # Get role policies
        print(f"\n📜 Checking attached policies...")
        
        # Get inline policies
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        print(f"\n🔸 Inline Policies ({len(inline_policies['PolicyNames'])}):")
        for policy_name in inline_policies['PolicyNames']:
            print(f"   • {policy_name}")
            policy_doc = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policy_document = policy_doc['PolicyDocument']
            
            # Check for DynamoDB permissions
            for statement in policy_document.get('Statement', []):
                actions = statement.get('Action', [])
                resources = statement.get('Resource', [])
                
                if isinstance(actions, str):
                    actions = [actions]
                if isinstance(resources, str):
                    resources = [resources]
                
                dynamodb_actions = [a for a in actions if 'dynamodb' in a.lower()]
                if dynamodb_actions:
                    print(f"      DynamoDB Actions: {dynamodb_actions}")
                    print(f"      Resources: {resources}")
        
        # Get managed policies
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        print(f"\n🔸 Managed Policies ({len(attached_policies['AttachedPolicies'])}):")
        for policy in attached_policies['AttachedPolicies']:
            print(f"   • {policy['PolicyName']} ({policy['PolicyArn']})")
        
        return role_name
        
    except Exception as e:
        print(f"❌ Error checking Lambda role: {str(e)}")
        return None

def check_dynamodb_tables():
    """Check if DynamoDB tables exist and are accessible"""
    print("\n🗄️  Checking DynamoDB Tables...")
    print("="*80)
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    tables_to_check = ['EmailContacts', 'EmailCampaigns', 'EmailConfig']
    
    for table_name in tables_to_check:
        try:
            table = dynamodb.Table(table_name)
            table.load()  # This will raise an exception if table doesn't exist
            
            print(f"✅ {table_name}")
            print(f"   Status: {table.table_status}")
            print(f"   Item Count: {table.item_count}")
            
            # Test a simple scan operation
            try:
                response = table.scan(Limit=1)
                print(f"   Scan Test: ✅ Success")
            except Exception as scan_error:
                print(f"   Scan Test: ❌ {str(scan_error)}")
                if '403' in str(scan_error) or 'AccessDenied' in str(scan_error):
                    print(f"   🔴 403 ERROR DETECTED for {table_name}")
            
        except Exception as e:
            print(f"❌ {table_name}: {str(e)}")
            if 'ResourceNotFoundException' in str(e):
                print(f"   Table does not exist!")

def check_s3_bucket_access():
    """Check S3 bucket access for Cognito config"""
    print("\n🪣 Checking S3 Bucket Access...")
    print("="*80)
    
    s3_client = boto3.client('s3', region_name=REGION)
    bucket_name = 'jcdc-ses-contact-list'
    
    try:
        # Test bucket access
        response = s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' exists and is accessible")
        
        # Test cognito_config.json access
        try:
            obj = s3_client.get_object(Bucket=bucket_name, Key='cognito_config.json')
            print(f"✅ cognito_config.json exists")
        except s3_client.exceptions.NoSuchKey:
            print(f"⚠️  cognito_config.json not found (this is OK)")
        except Exception as s3_error:
            print(f"❌ Error accessing cognito_config.json: {str(s3_error)}")
            if '403' in str(s3_error) or 'AccessDenied' in str(s3_error):
                print(f"   🔴 403 ERROR DETECTED for S3")
        
    except Exception as e:
        print(f"❌ Bucket access error: {str(e)}")
        if '403' in str(e) or 'AccessDenied' in str(e):
            print(f"   🔴 403 ERROR DETECTED for S3 bucket")

def test_lambda_invocation():
    """Test Lambda function with a simple request"""
    print("\n🧪 Testing Lambda Function Invocation...")
    print("="*80)
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    # Test with a simple GET request to /contacts
    test_event = {
        'httpMethod': 'GET',
        'resource': '/contacts',
        'path': '/contacts',
        'queryStringParameters': {'limit': '1'},
        'headers': {},
        'body': None,
        'requestContext': {
            'apiId': 'test',
            'stage': 'test'
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Response Status: {status_code}")
        
        if status_code == 500:
            print("🔴 500 ERROR - Internal Server Error")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"Error: {error_message}")
            
            # Check for specific 403 patterns
            if '403' in error_message or 'AccessDenied' in error_message:
                print("🔴 403 ACCESS DENIED ERROR DETECTED!")
                print("This confirms the Lambda is getting 403 errors from AWS services")
                
        elif status_code == 200:
            print("✅ Lambda function executed successfully")
            
        else:
            print(f"⚠️  Unexpected status code: {status_code}")
            print(f"Response: {payload.get('body', 'No body')}")
            
    except Exception as e:
        print(f"❌ Lambda invocation failed: {str(e)}")

def check_cloudwatch_logs():
    """Check recent CloudWatch logs for 403 errors"""
    print("\n📋 Checking CloudWatch Logs for 403 Errors...")
    print("="*80)
    
    logs_client = boto3.client('logs', region_name=REGION)
    log_group_name = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'
    
    try:
        # Get log events from the last 30 minutes
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            filterPattern='403',  # Filter for 403 errors
            limit=50
        )
        
        events = response.get('events', [])
        if events:
            print(f"🔴 Found {len(events)} log entries containing '403':")
            for event in events[-5:]:  # Show last 5 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"\n[{timestamp}]")
                print(f"{message}")
        else:
            print("ℹ️  No 403 errors found in recent logs")
            
        # Also check for general errors
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            filterPattern='ERROR',
            limit=20
        )
        
        error_events = response.get('events', [])
        if error_events:
            print(f"\n⚠️  Found {len(error_events)} ERROR log entries:")
            for event in error_events[-3:]:  # Show last 3 errors
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"\n[{timestamp}]")
                print(f"{message}")
                
    except Exception as e:
        print(f"❌ Error checking logs: {str(e)}")

def main():
    """Run all diagnostics"""
    print("🔧 Lambda 403 Error Comprehensive Diagnostics")
    print("="*80)
    print(f"Function: {LAMBDA_FUNCTION_NAME}")
    print(f"Region: {REGION}")
    print(f"Time: {datetime.now()}")
    print("="*80)
    
    # Run all checks
    role_name = check_lambda_role_permissions()
    check_dynamodb_tables()
    check_s3_bucket_access()
    test_lambda_invocation()
    check_cloudwatch_logs()
    
    print("\n" + "="*80)
    print("🎯 DIAGNOSIS SUMMARY")
    print("="*80)
    print("Common causes of 403 errors in Lambda:")
    print("1. ❌ Missing DynamoDB permissions for EmailConfig table")
    print("2. ❌ Missing S3 permissions for jcdc-ses-contact-list bucket")
    print("3. ❌ Lambda execution role lacks required policies")
    print("4. ❌ DynamoDB tables don't exist in the specified region")
    print("5. ❌ Resource-based policies blocking access")
    
    print("\n💡 RECOMMENDED FIXES:")
    if role_name:
        print(f"1. Add DynamoDB permissions to role '{role_name}':")
        print("   aws iam put-role-policy --role-name", role_name, "--policy-name DynamoDBFullAccess \\")
        print("   --policy-document file://dynamodb_policy.json")
        
        print(f"\n2. Add S3 permissions to role '{role_name}':")
        print("   aws iam attach-role-policy --role-name", role_name, "\\")
        print("   --policy-arn arn:aws-us-gov:iam::aws:policy/AmazonS3ReadOnlyAccess")
    
    print("\n3. Verify all DynamoDB tables exist:")
    print("   python setup_all_tables.py")
    
    print("\n✅ Run this script again after applying fixes to verify resolution")

if __name__ == '__main__':
    main()