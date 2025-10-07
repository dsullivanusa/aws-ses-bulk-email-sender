#!/usr/bin/env python3
"""
Diagnose 502 Internal Server Error
This script helps identify why the Lambda function is returning 502 errors
"""

import json
import boto3
import time
from datetime import datetime, timedelta

def check_lambda_logs():
    """Check recent Lambda logs for errors"""
    print("🔍 Checking Lambda logs for errors...")
    
    try:
        logs_client = boto3.client('logs')
        
        # Get recent log events
        log_group = '/aws/lambda/bulk-email-api'
        
        # Get logs from the last 10 minutes
        start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
        
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=50
        )
        
        events = response.get('events', [])
        
        if not events:
            print("❌ No recent log events found")
            print("   This might indicate the Lambda isn't being invoked at all")
            return False
        
        print(f"✅ Found {len(events)} recent log events")
        
        # Look for error patterns
        errors = []
        for event in events:
            message = event.get('message', '')
            if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '502']):
                errors.append({
                    'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                    'message': message.strip()
                })
        
        if errors:
            print(f"\n🚨 Found {len(errors)} error messages:")
            for error in errors[-5:]:  # Show last 5 errors
                print(f"   {error['timestamp']}: {error['message'][:100]}...")
        else:
            print("✅ No obvious error messages found in recent logs")
        
        return len(errors) > 0
        
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False

def check_lambda_function():
    """Check Lambda function configuration and status"""
    print("\n🔍 Checking Lambda function status...")
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Get function configuration
        response = lambda_client.get_function(FunctionName='bulk-email-api')
        config = response['Configuration']
        
        print(f"✅ Function exists: {config['FunctionName']}")
        print(f"   Runtime: {config['Runtime']}")
        print(f"   Last Modified: {config['LastModified']}")
        print(f"   State: {config['State']}")
        print(f"   State Reason: {config.get('StateReason', 'N/A')}")
        
        # Check if function is active
        if config['State'] != 'Active':
            print(f"❌ Function is not active: {config['State']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Lambda function: {e}")
        return False

def test_lambda_invocation():
    """Test Lambda function with a simple invocation"""
    print("\n🔍 Testing Lambda function invocation...")
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Test with a simple GET request
        test_event = {
            'httpMethod': 'GET',
            'path': '/',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': None
        }
        
        print("   Invoking Lambda with test event...")
        response = lambda_client.invoke(
            FunctionName='bulk-email-api',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        status_code = response['StatusCode']
        print(f"   Invocation status code: {status_code}")
        
        if status_code == 200:
            payload = json.loads(response['Payload'].read())
            print(f"   Response: {payload}")
            
            if 'errorMessage' in payload:
                print(f"❌ Lambda returned error: {payload['errorMessage']}")
                return False
            else:
                print("✅ Lambda invocation successful")
                return True
        else:
            print(f"❌ Lambda invocation failed with status: {status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Lambda invocation: {e}")
        return False

def check_api_gateway():
    """Check API Gateway configuration"""
    print("\n🔍 Checking API Gateway...")
    
    try:
        apigw_client = boto3.client('apigateway')
        
        # List APIs
        apis = apigw_client.get_rest_apis()
        
        # Find our API (look for one with 'bulk' or 'email' in the name)
        target_api = None
        for api in apis['items']:
            if 'bulk' in api['name'].lower() or 'email' in api['name'].lower():
                target_api = api
                break
        
        if not target_api:
            print("❌ Could not find API Gateway for bulk email")
            return False
        
        print(f"✅ Found API: {target_api['name']} (ID: {target_api['id']})")
        
        # Check deployments
        deployments = apigw_client.get_deployments(restApiId=target_api['id'])
        if deployments['items']:
            latest_deployment = deployments['items'][0]
            print(f"   Latest deployment: {latest_deployment['id']}")
            print(f"   Created: {latest_deployment['createdDate']}")
        else:
            print("❌ No deployments found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking API Gateway: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🚨 502 Internal Server Error Diagnostic")
    print("=" * 50)
    
    # Check Lambda function status
    lambda_ok = check_lambda_function()
    
    # Check recent logs
    logs_ok = check_lambda_logs()
    
    # Test Lambda invocation
    invocation_ok = test_lambda_invocation()
    
    # Check API Gateway
    apigw_ok = check_api_gateway()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY:")
    print(f"   Lambda Function: {'✅ OK' if lambda_ok else '❌ ISSUE'}")
    print(f"   Recent Logs: {'✅ OK' if logs_ok else '❌ ISSUE'}")
    print(f"   Lambda Invocation: {'✅ OK' if invocation_ok else '❌ ISSUE'}")
    print(f"   API Gateway: {'✅ OK' if apigw_ok else '❌ ISSUE'}")
    
    if not lambda_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Check if the Lambda function was deployed successfully")
        print("2. Verify the function code has no syntax errors")
        print("3. Check IAM permissions for the Lambda execution role")
    
    if not invocation_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Check Lambda function logs for Python syntax errors")
        print("2. Verify all required Python packages are included")
        print("3. Test the function locally if possible")
    
    if not apigw_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Check API Gateway deployment status")
        print("2. Verify the Lambda integration is configured correctly")
        print("3. Check API Gateway logs for additional details")

if __name__ == '__main__':
    main()
