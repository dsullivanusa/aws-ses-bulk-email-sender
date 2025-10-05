#!/usr/bin/env python3
"""
Test the search endpoint directly
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def test_search():
    """Test the search endpoint"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    print("🧪 Testing /contacts/search endpoint...")
    print("="*80)
    
    test_event = {
        'httpMethod': 'POST',
        'resource': '/contacts/search',
        'path': '/contacts/search',
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'search_term': 'test'})
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        print(f"Status Code: {payload.get('statusCode')}")
        
        if payload.get('statusCode') == 500:
            print("\n❌ 500 ERROR!")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"\n🔴 Error Message:")
            print(f"   {error_message}")
            print("\nNow checking CloudWatch Logs for full traceback...")
            
        elif payload.get('statusCode') == 200:
            print("\n✅ SUCCESS!")
            body = json.loads(payload.get('body', '{}'))
            contacts = body.get('contacts', [])
            print(f"Contacts found: {len(contacts)}")
        else:
            print(f"\n⚠️ Status: {payload.get('statusCode')}")
            print(f"Body: {payload.get('body')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def check_logs():
    """Check recent CloudWatch logs"""
    logs_client = boto3.client('logs', region_name=REGION)
    from datetime import datetime, timedelta
    
    log_group_name = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'
    
    print("\n" + "="*80)
    print("📋 Recent Lambda Logs:")
    print("="*80)
    
    try:
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
        
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            limit=50
        )
        
        for event in response.get('events', []):
            message = event['message'].strip()
            if 'search' in message.lower() or 'error' in message.lower() or 'traceback' in message.lower():
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print(f"[{timestamp}] {message}")
                
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == '__main__':
    test_search()
    check_logs()

