#!/usr/bin/env python3
"""
Check Lambda CloudWatch Logs for Recent Errors
"""

import boto3
from datetime import datetime, timedelta

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def check_recent_errors():
    """Check CloudWatch logs for recent Lambda errors"""
    logs_client = boto3.client('logs', region_name=REGION)
    
    log_group_name = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'
    
    print(f"🔍 Checking logs for: {log_group_name}")
    print("="*80)
    
    try:
        # Get log events from the last 15 minutes
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(minutes=15)).timestamp() * 1000)
        
        # Filter for errors
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            limit=100
        )
        
        print(f"\n📋 Recent Log Entries (last 15 minutes):\n")
        
        error_found = False
        for event in response.get('events', []):
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            # Highlight errors and important messages
            if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed']):
                print(f"🔴 [{timestamp}]")
                print(f"   {message}")
                print()
                error_found = True
            elif 'get_contacts' in message.lower():
                print(f"🔍 [{timestamp}]")
                print(f"   {message}")
                print()
        
        if not error_found:
            print("⚠️  No error messages found in recent logs")
            print("\nThis could mean:")
            print("1. Lambda hasn't been invoked recently (try loading contacts again)")
            print("2. Lambda function code hasn't been updated yet")
            print("3. Error occurred before CloudWatch logging started")
        
        if not response.get('events'):
            print("⚠️  No log entries found")
            print("\nTroubleshooting steps:")
            print("1. Make sure Lambda has been invoked (refresh the web UI)")
            print("2. Check if Lambda name is correct")
            print("3. Verify CloudWatch Logs permissions")
    
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ Log group not found: {log_group_name}")
        print("\nThis means the Lambda function hasn't been invoked yet or doesn't exist")
        print("\nCheck Lambda function name:")
        lambda_client = boto3.client('lambda', region_name=REGION)
        functions = lambda_client.list_functions()
        print("\n📋 Available Lambda functions:")
        for func in functions['Functions']:
            if 'email' in func['FunctionName'].lower() or 'bulk' in func['FunctionName'].lower():
                print(f"  - {func['FunctionName']}")
    
    except Exception as e:
        print(f"❌ Error checking logs: {str(e)}")
        import traceback
        traceback.print_exc()

def test_contacts_endpoint():
    """Test the /contacts endpoint directly"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    print("\n" + "="*80)
    print("🧪 Testing /contacts endpoint directly...")
    print("="*80)
    
    test_event = {
        'httpMethod': 'GET',
        'resource': '/contacts',
        'path': '/contacts',
        'queryStringParameters': {'limit': '5'},
        'headers': {},
        'body': None
    }
    
    try:
        import json
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        print(f"\n📊 Response Status Code: {payload.get('statusCode')}")
        
        if payload.get('statusCode') == 500:
            print("\n❌ 500 ERROR DETECTED!")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"\n🔴 Error Message:")
            print(f"   {error_message}")
            
            print("\n💡 Common causes:")
            print("  1. EmailContacts table doesn't exist")
            print("  2. Lambda lacks DynamoDB scan permissions")
            print("  3. Syntax error in Lambda code")
            print("  4. Module import error")
            
        elif payload.get('statusCode') == 200:
            print("\n✅ SUCCESS!")
            body = json.loads(payload.get('body', '{}'))
            contacts = body.get('contacts', [])
            print(f"   Contacts returned: {len(contacts)}")
            if contacts:
                print(f"   First contact: {contacts[0].get('email', 'N/A')}")
        else:
            print(f"\n⚠️  Unexpected status: {payload.get('statusCode')}")
            print(f"   Response: {payload.get('body')}")
        
    except Exception as e:
        print(f"\n❌ Error invoking Lambda: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("\n🔧 Lambda Error Diagnostics\n")
    
    # Check recent logs
    check_recent_errors()
    
    # Test the endpoint
    test_contacts_endpoint()
    
    print("\n" + "="*80)
    print("✅ Diagnostics complete")
    print("="*80)

