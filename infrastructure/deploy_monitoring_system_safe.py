#!/usr/bin/env python3
"""
Safe deployment script that handles ResourceConflictException
Waits for Lambda function updates to complete before proceeding
"""

import boto3
import zipfile
import os
import json
import sys
import time
from datetime import datetime

def wait_for_function_update(function_name, max_wait_minutes=10):
    """Wait for Lambda function update to complete"""
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    print(f"⏳ Waiting for {function_name} update to complete...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while time.time() - start_time < max_wait_seconds:
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            state = response['Configuration']['LastUpdateStatus']
            
            print(f"  Current state: {state}")
            
            if state == 'Successful':
                print(f"  ✅ Function update completed successfully")
                return True
            elif state == 'Failed':
                print(f"  ❌ Function update failed")
                return False
            elif state in ['InProgress', 'Pending']:
                print(f"  ⏳ Update still in progress, waiting...")
                time.sleep(10)  # Wait 10 seconds before checking again
            else:
                print(f"  ⚠️ Unknown state: {state}")
                time.sleep(10)
                
        except Exception as e:
            print(f"  ⚠️ Error checking function status: {str(e)}")
            time.sleep(10)
    
    print(f"  ⚠️ Timeout waiting for function update")
    return False

def create_lambda_package(filename, files_to_include):
    """Create a zip package for Lambda deployment"""
    print(f"📦 Creating Lambda deployment package for {filename}...")
    
    zip_filename = f'{filename}_{int(datetime.now().timestamp())}.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_include:
            if os.path.exists(file):
                zipf.write(file, file)
                print(f"  ✓ Added {file}")
            else:
                print(f"  ✗ File not found: {file}")
    
    print(f"  ✓ Created package: {zip_filename}")
    return zip_filename

def update_email_worker_lambda_safe():
    """Update the email worker Lambda function with conflict handling"""
    print("\n🚀 Updating Email Worker Lambda Function (Safe Mode)...")
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        # Find the email worker function
        functions = lambda_client.list_functions()
        function_name = None
        
        patterns = [
            'email-worker-function',
            'email-worker',
            'EmailWorker',
            'email_worker'
        ]
        
        for pattern in patterns:
            matches = [f for f in functions['Functions'] if pattern.lower() in f['FunctionName'].lower()]
            if matches:
                function_name = matches[0]['FunctionName']
                break
        
        if not function_name:
            print("❌ Could not find email worker Lambda function")
            return False
        
        print(f"✓ Found function: {function_name}")
        
        # Check current function status
        try:
            current_function = lambda_client.get_function(FunctionName=function_name)
            current_state = current_function['Configuration'].get('LastUpdateStatus', 'Unknown')
            print(f"Current function state: {current_state}")
            
            if current_state in ['InProgress', 'Pending']:
                print("⚠️ Function is currently being updated, waiting for completion...")
                if not wait_for_function_update(function_name):
                    print("❌ Function update did not complete successfully")
                    return False
        except Exception as e:
            print(f"⚠️ Could not check function status: {str(e)}")
        
        # Create package
        zip_filename = create_lambda_package(
            'email_worker_with_monitoring',
            ['email_worker_lambda.py']
        )
        
        try:
            # Update function code
            print("  📤 Uploading new code...")
            with open(zip_filename, 'rb') as zip_file:
                zip_content = zip_file.read()
            
            code_response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"  ✓ Code update initiated")
            
            # Wait for code update to complete
            if not wait_for_function_update(function_name):
                print("❌ Code update failed")
                return False
            
            # Update configuration
            print("  ⚙️ Updating function configuration...")
            config_response = lambda_client.update_function_configuration(
                FunctionName=function_name,
                Timeout=900,  # 15 minutes
                MemorySize=1024,  # 1GB memory
                Environment={
                    'Variables': {
                        'BASE_DELAY_SECONDS': '0.2',
                        'MAX_DELAY_SECONDS': '8.0',
                        'MIN_DELAY_SECONDS': '0.05'
                    }
                }
            )
            print(f"  ✓ Configuration update initiated")
            
            # Wait for configuration update to complete
            if not wait_for_function_update(function_name):
                print("❌ Configuration update failed")
                return False
            
            print(f"  ✅ Function updated successfully")
            print(f"  ✓ Timeout: {config_response['Timeout']} seconds")
            print(f"  ✓ Memory: {config_response['MemorySize']} MB")
            
            # Clean up
            os.remove(zip_filename)
            
            return function_name
            
        except lambda_client.exceptions.ResourceConflictException as e:
            print(f"❌ Resource conflict during update: {str(e)}")
            print("🔄 Retrying after waiting...")
            
            # Wait and retry once
            time.sleep(30)
            try:
                config_response = lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Timeout=900,
                    MemorySize=1024,
                    Environment={
                        'Variables': {
                            'BASE_DELAY_SECONDS': '0.2',
                            'MAX_DELAY_SECONDS': '8.0',
                            'MIN_DELAY_SECONDS': '0.05'
                        }
                    }
                )
                print(f"  ✅ Configuration updated on retry")
                os.remove(zip_filename)
                return function_name
            except Exception as retry_e:
                print(f"❌ Retry also failed: {str(retry_e)}")
                if os.path.exists(zip_filename):
                    os.remove(zip_filename)
                return False
        
    except Exception as e:
        print(f"❌ Error updating email worker Lambda: {str(e)}")
        return False

def create_cloudwatch_alarms_safe():
    """Create CloudWatch alarms with error handling"""
    print("\n🚨 Creating CloudWatch Alarms (Safe Mode)...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    # Standard alarms for Lambda function
    alarms = [
        {
            'name': 'EmailWorker-FunctionErrors',
            'description': 'Email Worker Lambda function errors',
            'metric': 'Errors',
            'namespace': 'AWS/Lambda',
            'statistic': 'Sum',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold',
            'period': 300,
            'evaluation_periods': 2
        },
        {
            'name': 'EmailWorker-ThrottleExceptions',
            'description': 'Email Worker detected throttle exceptions',
            'metric': 'ThrottleExceptions',
            'namespace': 'EmailWorker/Custom',
            'statistic': 'Sum',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold',
            'period': 300,
            'evaluation_periods': 2
        },
        {
            'name': 'EmailWorker-IncompleteCampaigns',
            'description': 'Email campaigns not completed within expected time',
            'metric': 'IncompleteCampaigns',
            'namespace': 'EmailWorker/Custom',
            'statistic': 'Sum',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold',
            'period': 300,
            'evaluation_periods': 2
        }
    ]
    
    created_alarms = []
    
    for alarm_config in alarms:
        try:
            print(f"  📊 Creating alarm: {alarm_config['name']}")
            
            alarm_params = {
                'AlarmName': alarm_config['name'],
                'AlarmDescription': alarm_config['description'],
                'MetricName': alarm_config['metric'],
                'Namespace': alarm_config['namespace'],
                'Statistic': alarm_config['statistic'],
                'Period': alarm_config['period'],
                'EvaluationPeriods': alarm_config['evaluation_periods'],
                'Threshold': alarm_config['threshold'],
                'ComparisonOperator': alarm_config['operator'],
                'TreatMissingData': 'notBreaching'
            }
            
            # Add dimensions for Lambda metrics
            if alarm_config['namespace'] == 'AWS/Lambda':
                lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
                functions = lambda_client.list_functions()
                function_name = None
                
                for func in functions['Functions']:
                    if 'email-worker' in func['FunctionName'].lower():
                        function_name = func['FunctionName']
                        break
                
                if function_name:
                    alarm_params['Dimensions'] = [
                        {'Name': 'FunctionName', 'Value': function_name}
                    ]
            
            cloudwatch.put_metric_alarm(**alarm_params)
            created_alarms.append(alarm_config['name'])
            print(f"    ✅ Created: {alarm_config['name']}")
            
        except Exception as e:
            print(f"    ⚠️ Could not create {alarm_config['name']}: {str(e)}")
    
    print(f"\n✓ Created {len(created_alarms)} CloudWatch alarms")
    return created_alarms

def main():
    """Main deployment function with conflict handling"""
    print("🚀 Safe Deployment of Email Monitoring System")
    print("=" * 60)
    
    try:
        # Step 1: Update email worker Lambda with conflict handling
        email_worker_function = update_email_worker_lambda_safe()
        if not email_worker_function:
            print("❌ Failed to update email worker Lambda")
            return False
        
        # Step 2: Create CloudWatch alarms
        created_alarms = create_cloudwatch_alarms_safe()
        
        print("\n" + "=" * 60)
        print("✅ SAFE DEPLOYMENT COMPLETE!")
        print("=" * 60)
        
        print(f"\n📊 Deployed Components:")
        print(f"  🔧 Email Worker Lambda: {email_worker_function}")
        print(f"  🚨 CloudWatch Alarms: {len(created_alarms)}")
        
        print(f"\n🎯 Monitoring Features Active:")
        print(f"  📈 Adaptive rate control with attachment detection")
        print(f"  🚨 Throttle exception detection and alerting")
        print(f"  📊 Campaign completion monitoring")
        print(f"  ⏱️ Lambda function performance monitoring")
        
        print(f"\n🔍 Next Steps:")
        print(f"  1. Monitor CloudWatch alarms in AWS console")
        print(f"  2. Test email campaigns with attachments")
        print(f"  3. Review CloudWatch metrics and logs")
        
        print(f"\n📋 Monitoring Commands:")
        print(f"  # View CloudWatch alarms:")
        print(f"  aws cloudwatch describe-alarms --region us-gov-west-1")
        print(f"")
        print(f"  # View Lambda logs:")
        print(f"  aws logs tail /aws/lambda/{email_worker_function} --follow --region us-gov-west-1")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Safe deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
