#!/usr/bin/env python3
"""
Check Lambda Logs for Groups Endpoint Error
Retrieves recent Lambda logs to diagnose the 500 error
"""

import boto3
import json
from datetime import datetime, timedelta

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def check_logs():
    """Check Lambda logs for errors"""
    logs_client = boto3.client('logs', region_name=REGION)
    
    log_group_name = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'
    
    print(f"Checking logs for: {log_group_name}")
    print("="*80)
    
    try:
        # Get log streams from the last hour
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
        
        # Get recent log events
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            limit=50
        )
        
        print(f"\n📋 Recent Log Entries (last 1 hour):\n")
        
        for event in response.get('events', []):
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            # Highlight errors
            if 'error' in message.lower() or 'exception' in message.lower():
                print(f"🔴 [{timestamp}] {message}")
            elif 'groups' in message.lower():
                print(f"🔍 [{timestamp}] {message}")
            else:
                print(f"   [{timestamp}] {message}")
        
        if not response.get('events'):
            print("⚠️  No recent log entries found")
            print("\nTroubleshooting steps:")
            print("1. Make sure the Lambda function has been invoked recently")
            print("2. Try accessing the /groups endpoint again")
            print("3. Check if CloudWatch Logs permissions are configured")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ Log group not found: {log_group_name}")
        print("\nThis means:")
        print("- Lambda function hasn't been invoked yet, OR")
        print("- Lambda function name is incorrect")
        print("\nCheck Lambda function name:")
        lambda_client = boto3.client('lambda', region_name=REGION)
        functions = lambda_client.list_functions()
        print("\nAvailable Lambda functions:")
        for func in functions['Functions']:
            if 'email' in func['FunctionName'].lower() or 'bulk' in func['FunctionName'].lower():
                print(f"  - {func['FunctionName']}")
    
    except Exception as e:
        print(f"❌ Error checking logs: {str(e)}")
        import traceback
        traceback.print_exc()

def test_groups_endpoint():
    """Test the groups endpoint directly via Lambda"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    print("\n" + "="*80)
    print("🧪 Testing /groups endpoint directly...")
    print("="*80)
    
    test_event = {
        'httpMethod': 'GET',
        'resource': '/groups',
        'path': '/groups',
        'headers': {},
        'body': None
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        print(f"\nResponse Status Code: {payload.get('statusCode')}")
        print(f"Response Body: {payload.get('body')}")
        
        if payload.get('statusCode') == 500:
            print("\n❌ 500 ERROR DETECTED!")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"\nError Message: {error_message}")
            
            print("\n🔍 Common causes:")
            if 'Table' in error_message or 'DynamoDB' in error_message:
                print("  - EmailContacts table doesn't exist")
                print("  - Solution: Run 'python setup_all_tables.py' to create tables")
            elif 'permission' in error_message.lower() or 'access' in error_message.lower():
                print("  - Lambda lacks DynamoDB permissions")
                print("  - Solution: Update Lambda IAM role to include DynamoDB access")
            elif 'timeout' in error_message.lower() or 'network' in error_message.lower():
                print("  - VPC/Network issue")
                print("  - Solution: Check VPC endpoint for DynamoDB")
        elif payload.get('statusCode') == 200:
            print("\n✅ SUCCESS!")
            body = json.loads(payload.get('body', '{}'))
            groups = body.get('groups', [])
            print(f"Groups found: {groups}")
            if not groups:
                print("\n⚠️  No groups found in database")
                print("This is normal if you haven't added contacts with groups yet")
        
    except Exception as e:
        print(f"❌ Error invoking Lambda: {str(e)}")
        import traceback
        traceback.print_exc()

def check_table_exists():
    """Check if EmailContacts table exists"""
    dynamodb = boto3.client('dynamodb', region_name=REGION)
    
    print("\n" + "="*80)
    print("📊 Checking DynamoDB Tables...")
    print("="*80)
    
    try:
        response = dynamodb.describe_table(TableName='EmailContacts')
        print("\n✅ EmailContacts table exists")
        print(f"   Status: {response['Table']['TableStatus']}")
        print(f"   Item Count: {response['Table']['ItemCount']}")
    except dynamodb.exceptions.ResourceNotFoundException:
        print("\n❌ EmailContacts table NOT FOUND!")
        print("\n🔧 Solution: Create the table")
        print("   Run: python setup_all_tables.py")
    except Exception as e:
        print(f"\n❌ Error checking table: {str(e)}")

if __name__ == '__main__':
    print("\n🔍 Diagnosing /groups endpoint 500 error...\n")
    
    # Check if table exists
    check_table_exists()
    
    # Test the endpoint
    test_groups_endpoint()
    
    # Check logs
    check_logs()
    
    print("\n" + "="*80)
    print("✅ Diagnosis complete")
    print("="*80)

