#!/usr/bin/env python3
"""
Test Lambda Function After 403 Fixes
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def test_lambda_with_better_logging():
    """Test Lambda function to see detailed error messages"""
    print("🧪 Testing Lambda Function with Enhanced Error Logging")
    print("="*70)
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    # Test event that should trigger DynamoDB access
    test_event = {
        'httpMethod': 'GET',
        'resource': '/contacts',
        'path': '/contacts',
        'queryStringParameters': {'limit': '1'},
        'headers': {},
        'body': None,
        'requestContext': {
            'apiId': 'test-api',
            'stage': 'test'
        }
    }
    
    try:
        print("📤 Invoking Lambda function...")
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Response Status Code: {status_code}")
        
        if status_code == 500:
            print("\n🔴 ERROR RESPONSE:")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"Error Message: {error_message}")
            
            # The enhanced error logging should now show specific 403 details
            print("\n💡 Check CloudWatch Logs for detailed 403 error information:")
            print(f"   Log Group: /aws/lambda/{LAMBDA_FUNCTION_NAME}")
            print("   Look for messages starting with '🔴 403 PERMISSION ERROR'")
            
        elif status_code == 200:
            print("\n✅ SUCCESS! Lambda executed without errors")
            body = json.loads(payload.get('body', '{}'))
            contacts = body.get('contacts', [])
            print(f"   Returned {len(contacts)} contacts")
            
        else:
            print(f"\n⚠️  Unexpected status: {status_code}")
            print(f"Response body: {payload.get('body', 'No body')}")
            
    except Exception as e:
        print(f"\n❌ Lambda invocation failed: {str(e)}")

def check_recent_logs():
    """Check recent CloudWatch logs for the enhanced error messages"""
    print("\n📋 Checking Recent CloudWatch Logs")
    print("="*70)
    
    logs_client = boto3.client('logs', region_name=REGION)
    log_group_name = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'
    
    try:
        from datetime import datetime, timedelta
        
        # Get logs from last 10 minutes
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
        
        # Look for our enhanced error messages
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            limit=50
        )
        
        events = response.get('events', [])
        if events:
            print(f"📋 Found {len(events)} recent log entries:")
            
            for event in events[-10:]:  # Show last 10 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                
                # Highlight our enhanced error messages
                if any(marker in message for marker in ['🔴', '⚠️', '403', 'AccessDenied']):
                    print(f"\n🔴 [{timestamp}] IMPORTANT:")
                    print(f"   {message}")
                elif 'ERROR' in message:
                    print(f"\n⚠️  [{timestamp}] ERROR:")
                    print(f"   {message}")
                else:
                    print(f"   [{timestamp}] {message}")
        else:
            print("ℹ️  No recent log entries found")
            print("   Try invoking the Lambda function first")
            
    except Exception as e:
        print(f"❌ Error checking logs: {str(e)}")

def main():
    """Run the test"""
    print("🔧 Testing Lambda 403 Error Fixes")
    print("="*70)
    
    # Test the Lambda function
    test_lambda_with_better_logging()
    
    # Check logs for enhanced error messages
    check_recent_logs()
    
    print("\n" + "="*70)
    print("🎯 WHAT TO LOOK FOR:")
    print("="*70)
    print("✅ If you see '🔴 403 PERMISSION ERROR DETECTED!' in logs:")
    print("   - The enhanced logging is working")
    print("   - You'll see specific service (DynamoDB/S3) causing the issue")
    print("   - Run: python fix_403_permissions.py")
    
    print("\n✅ If you see 'SUCCESS! Lambda executed without errors':")
    print("   - The 403 errors are resolved!")
    print("   - Your Lambda function is working properly")
    
    print("\n⚠️  If you still see generic errors:")
    print("   - Check IAM permissions manually")
    print("   - Verify DynamoDB tables exist")
    print("   - Run: python diagnose_403_errors.py")

if __name__ == '__main__':
    main()