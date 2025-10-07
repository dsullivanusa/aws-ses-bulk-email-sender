#!/usr/bin/env python3
"""
Diagnose Internal Server Error
This script helps identify why the Lambda function is returning 500 errors
"""

import boto3
import json
import time
from datetime import datetime, timedelta

def check_lambda_logs():
    """Check recent Lambda logs for errors"""
    print("🔍 Checking Lambda logs for errors...")
    
    try:
        logs_client = boto3.client('logs')
        
        # Get recent log events
        log_group = '/aws/lambda/bulk-email-api-function'
        
        # Get logs from the last 15 minutes
        start_time = int((datetime.now() - timedelta(minutes=15)).timestamp() * 1000)
        
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=100
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
            if any(keyword in message.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '500', 'internal server']):
                errors.append({
                    'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                    'message': message.strip()
                })
        
        if errors:
            print(f"\n🚨 Found {len(errors)} error messages:")
            for error in errors[-10:]:  # Show last 10 errors
                print(f"   {error['timestamp']}: {error['message'][:150]}...")
        else:
            print("✅ No obvious error messages found in recent logs")
        
        return len(errors) > 0
        
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        return False

def check_lambda_function_status():
    """Check Lambda function configuration and status"""
    print("\n🔍 Checking Lambda function status...")
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Get function configuration
        response = lambda_client.get_function(FunctionName='bulk-email-api-function')
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
        
        # Check environment variables
        env_vars = config.get('Environment', {}).get('Variables', {})
        if env_vars:
            print(f"\n📋 Environment Variables:")
            for key, value in env_vars.items():
                print(f"   {key} = {value}")
        else:
            print("\n📋 No environment variables set")
        
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
            'body': None,
            'requestContext': {
                'apiId': 'test-api-id'
            }
        }
        
        print("   Invoking Lambda with test event...")
        response = lambda_client.invoke(
            FunctionName='bulk-email-api-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        status_code = response['StatusCode']
        print(f"   Invocation status code: {status_code}")
        
        if status_code == 200:
            payload = json.loads(response['Payload'].read())
            print(f"   Response keys: {list(payload.keys())}")
            
            if 'errorMessage' in payload:
                print(f"❌ Lambda returned error: {payload['errorMessage']}")
                if 'errorType' in payload:
                    print(f"   Error type: {payload['errorType']}")
                if 'stackTrace' in payload:
                    print(f"   Stack trace: {payload['stackTrace'][:500]}...")
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

def check_python_syntax():
    """Check if the Lambda function has valid Python syntax"""
    print("\n🔍 Checking Python syntax...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the Python code
        import ast
        try:
            ast.parse(content)
            print("✅ Python syntax is valid")
            return True
        except SyntaxError as e:
            print(f"❌ Python syntax error found:")
            print(f"   Line {e.lineno}: {e.text}")
            print(f"   Error: {e.msg}")
            return False
        except Exception as e:
            print(f"❌ Error parsing Python code: {e}")
            return False
            
    except FileNotFoundError:
        print("❌ File bulk_email_api_lambda.py not found")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def check_javascript_syntax():
    """Check for obvious JavaScript syntax issues"""
    print("\n🔍 Checking JavaScript syntax...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for f-string syntax issues
        import re
        fstring_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if fstring_issues:
            issues.append(f"Found {len(fstring_issues)} f-string syntax issues: ${{}}")
        
        # Check for unclosed template literals
        template_literals = re.findall(r'`[^`]*`', content)
        for template in template_literals:
            if '${' in template and '}' not in template:
                issues.append(f"Unclosed template literal: {template[:50]}...")
        
        # Check for missing function definitions
        if 'function showTab(' not in content:
            issues.append("showTab function definition not found")
        
        if issues:
            print(f"❌ Found {len(issues)} JavaScript issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ No obvious JavaScript syntax issues found")
            return True
            
    except Exception as e:
        print(f"❌ Error checking JavaScript syntax: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🚨 Internal Server Error Diagnostic")
    print("=" * 50)
    
    # Check Python syntax
    python_ok = check_python_syntax()
    
    # Check JavaScript syntax
    js_ok = check_javascript_syntax()
    
    # Check Lambda function status
    lambda_ok = check_lambda_function_status()
    
    # Check recent logs
    logs_ok = check_lambda_logs()
    
    # Test Lambda invocation
    invocation_ok = test_lambda_invocation()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY:")
    print(f"   Python Syntax: {'✅ OK' if python_ok else '❌ ISSUE'}")
    print(f"   JavaScript Syntax: {'✅ OK' if js_ok else '❌ ISSUE'}")
    print(f"   Lambda Function: {'✅ OK' if lambda_ok else '❌ ISSUE'}")
    print(f"   Recent Logs: {'✅ OK' if logs_ok else '❌ ISSUE'}")
    print(f"   Lambda Invocation: {'✅ OK' if invocation_ok else '❌ ISSUE'}")
    
    if not python_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Fix Python syntax errors in bulk_email_api_lambda.py")
        print("2. Redeploy the Lambda function")
    
    if not js_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Run: python fix_api_url_undefined.py")
        print("2. Redeploy the Lambda function")
    
    if not lambda_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Check if the Lambda function was deployed successfully")
        print("2. Verify the function code has no syntax errors")
        print("3. Check IAM permissions for the Lambda execution role")
    
    if not invocation_ok:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Check Lambda function logs for detailed error messages")
        print("2. Verify all required Python packages are included")
        print("3. Test the function locally if possible")

if __name__ == '__main__':
    main()
