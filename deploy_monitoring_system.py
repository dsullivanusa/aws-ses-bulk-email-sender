#!/usr/bin/env python3
"""
Deploy the complete monitoring system including:
- Updated email worker Lambda with CloudWatch metrics
- Campaign monitor Lambda function
- CloudWatch alarms for throttle exceptions and incomplete campaigns
"""

import boto3
import zipfile
import os
import json
import sys
from datetime import datetime

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

def update_email_worker_lambda():
    """Update the email worker Lambda function"""
    print("\n🚀 Updating Email Worker Lambda Function...")
    
    # Create package
    zip_filename = create_lambda_package(
        'email_worker_with_monitoring',
        ['email_worker_lambda.py']
    )
    
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
        
        # Read the zip file
        with open(zip_filename, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        print("  📤 Uploading new code...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"  ✓ Code updated successfully")
        
        # Update configuration for monitoring
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
        
        print(f"  ✓ Configuration updated")
        print(f"  ✓ Timeout: {config_response['Timeout']} seconds")
        print(f"  ✓ Memory: {config_response['MemorySize']} MB")
        
        # Clean up
        os.remove(zip_filename)
        
        return function_name
        
    except Exception as e:
        print(f"❌ Error updating email worker Lambda: {str(e)}")
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        return None

def deploy_campaign_monitor_lambda():
    """Deploy the campaign monitor Lambda function"""
    print("\n🔍 Deploying Campaign Monitor Lambda Function...")
    
    # Create package
    zip_filename = create_lambda_package(
        'campaign_monitor',
        ['campaign_monitor.py']
    )
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    iam_client = boto3.client('iam', region_name='us-gov-west-1')
    
    try:
        function_name = 'campaign-monitor-function'
        
        # Create IAM role for campaign monitor
        print("  🔐 Creating IAM role...")
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            role_response = iam_client.create_role(
                RoleName='campaign-monitor-role',
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Role for campaign monitor Lambda function'
            )
            role_arn = role_response['Role']['Arn']
            print(f"  ✓ Created IAM role: {role_arn}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            role_arn = f"arn:aws-us-gov:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/campaign-monitor-role"
            print(f"  ✓ Using existing IAM role: {role_arn}")
        
        # Attach policies
        policies = [
            'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'arn:aws-us-gov:iam::aws:policy/CloudWatchFullAccess',
            'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess'
        ]
        
        for policy_arn in policies:
            try:
                iam_client.attach_role_policy(
                    RoleName='campaign-monitor-role',
                    PolicyArn=policy_arn
                )
                print(f"  ✓ Attached policy: {policy_arn}")
            except Exception as e:
                print(f"  ⚠️ Could not attach policy {policy_arn}: {str(e)}")
        
        # Wait for role to be ready
        import time
        time.sleep(10)
        
        # Read the zip file
        with open(zip_filename, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Create or update Lambda function
        try:
            print("  📤 Creating Lambda function...")
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.13',
                Role=role_arn,
                Handler='campaign_monitor.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Monitors email campaigns for completion status and sends alerts',
                Timeout=300,  # 5 minutes
                MemorySize=256
            )
            print(f"  ✓ Created function: {response['FunctionArn']}")
        except lambda_client.exceptions.ResourceConflictException:
            print("  📤 Updating existing Lambda function...")
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"  ✓ Updated function: {response['FunctionArn']}")
        
        # Clean up
        os.remove(zip_filename)
        
        return function_name
        
    except Exception as e:
        print(f"❌ Error deploying campaign monitor Lambda: {str(e)}")
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        return None

def create_cloudwatch_alarms():
    """Create CloudWatch alarms for monitoring"""
    print("\n🚨 Creating CloudWatch Alarms...")
    
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
            'name': 'EmailWorker-HighDuration',
            'description': 'Email Worker Lambda function taking too long',
            'metric': 'Duration',
            'namespace': 'AWS/Lambda',
            'statistic': 'Average',
            'threshold': 600000.0,  # 10 minutes
            'operator': 'GreaterThanThreshold',
            'period': 300,
            'evaluation_periods': 3
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
        },
        {
            'name': 'CampaignMonitor-StuckCampaigns',
            'description': 'Campaign Monitor detected stuck campaigns',
            'metric': 'StuckCampaigns',
            'namespace': 'EmailWorker/CampaignMonitor',
            'statistic': 'Sum',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold',
            'period': 300,
            'evaluation_periods': 1
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
                # Find the email worker function
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
            print(f"    ✓ Created: {alarm_config['name']}")
            
        except Exception as e:
            print(f"    ❌ Failed to create {alarm_config['name']}: {str(e)}")
    
    print(f"\n✓ Created {len(created_alarms)} CloudWatch alarms")
    return created_alarms

def setup_eventbridge_rule():
    """Setup EventBridge rule to trigger campaign monitor periodically"""
    print("\n⏰ Setting up EventBridge Rule for Campaign Monitor...")
    
    events_client = boto3.client('events', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        # Create EventBridge rule to run every 5 minutes
        rule_name = 'campaign-monitor-schedule'
        
        rule_response = events_client.put_rule(
            Name=rule_name,
            Description='Trigger campaign monitor every 5 minutes',
            ScheduleExpression='rate(5 minutes)',
            State='ENABLED'
        )
        
        print(f"  ✓ Created EventBridge rule: {rule_name}")
        
        # Add Lambda function as target
        function_name = 'campaign-monitor-function'
        
        # Get function ARN
        function_response = lambda_client.get_function(FunctionName=function_name)
        function_arn = function_response['Configuration']['FunctionArn']
        
        # Add permission for EventBridge to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=f'eventbridge-{rule_name}',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=rule_response['RuleArn']
            )
            print(f"  ✓ Added Lambda permission for EventBridge")
        except lambda_client.exceptions.ResourceConflictException:
            print(f"  ✓ Lambda permission already exists")
        
        # Add target to rule
        events_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': function_arn
                }
            ]
        )
        
        print(f"  ✓ Added Lambda function as target")
        print(f"  ✓ Campaign monitor will run every 5 minutes")
        
        return rule_name
        
    except Exception as e:
        print(f"❌ Error setting up EventBridge rule: {str(e)}")
        return None

def verify_deployment():
    """Verify the deployment"""
    print("\n🔍 Verifying Deployment...")
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    try:
        # Check email worker function
        functions = lambda_client.list_functions()
        email_worker_found = False
        campaign_monitor_found = False
        
        for func in functions['Functions']:
            if 'email-worker' in func['FunctionName'].lower():
                email_worker_found = True
                print(f"  ✓ Email Worker: {func['FunctionName']}")
            elif 'campaign-monitor' in func['FunctionName'].lower():
                campaign_monitor_found = True
                print(f"  ✓ Campaign Monitor: {func['FunctionName']}")
        
        if not email_worker_found:
            print("  ❌ Email Worker function not found")
        if not campaign_monitor_found:
            print("  ❌ Campaign Monitor function not found")
        
        # Check CloudWatch alarms
        response = cloudwatch.describe_alarms()
        email_worker_alarms = [alarm for alarm in response['MetricAlarms'] if 'EmailWorker' in alarm['AlarmName']]
        campaign_monitor_alarms = [alarm for alarm in response['MetricAlarms'] if 'CampaignMonitor' in alarm['AlarmName']]
        
        print(f"  ✓ Email Worker alarms: {len(email_worker_alarms)}")
        print(f"  ✓ Campaign Monitor alarms: {len(campaign_monitor_alarms)}")
        
        return email_worker_found and campaign_monitor_found
        
    except Exception as e:
        print(f"❌ Error verifying deployment: {str(e)}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Deploying Complete Email Monitoring System")
    print("=" * 60)
    
    try:
        # Step 1: Update email worker Lambda
        email_worker_function = update_email_worker_lambda()
        if not email_worker_function:
            print("❌ Failed to update email worker Lambda")
            return False
        
        # Step 2: Deploy campaign monitor Lambda
        campaign_monitor_function = deploy_campaign_monitor_lambda()
        if not campaign_monitor_function:
            print("❌ Failed to deploy campaign monitor Lambda")
            return False
        
        # Step 3: Create CloudWatch alarms
        created_alarms = create_cloudwatch_alarms()
        
        # Step 4: Setup EventBridge rule
        eventbridge_rule = setup_eventbridge_rule()
        
        # Step 5: Verify deployment
        if not verify_deployment():
            print("❌ Deployment verification failed")
            return False
        
        print("\n" + "=" * 60)
        print("✅ MONITORING SYSTEM DEPLOYMENT COMPLETE!")
        print("=" * 60)
        
        print(f"\n📊 Deployed Components:")
        print(f"  🔧 Email Worker Lambda: {email_worker_function}")
        print(f"  🔍 Campaign Monitor Lambda: {campaign_monitor_function}")
        print(f"  🚨 CloudWatch Alarms: {len(created_alarms)}")
        print(f"  ⏰ EventBridge Rule: {eventbridge_rule}")
        
        print(f"\n🎯 Monitoring Features:")
        print(f"  📈 Adaptive rate control with attachment detection")
        print(f"  🚨 Throttle exception detection and alerting")
        print(f"  📊 Campaign completion monitoring")
        print(f"  💀 Dead letter queue monitoring")
        print(f"  📬 SQS queue health monitoring")
        print(f"  ⏱️ Lambda function performance monitoring")
        
        print(f"\n📋 Next Steps:")
        print(f"  1. Monitor CloudWatch alarms in AWS console")
        print(f"  2. Test email campaigns with attachments")
        print(f"  3. Review CloudWatch metrics and logs")
        print(f"  4. Configure SNS notifications if desired")
        
        print(f"\n🔍 Monitoring Commands:")
        print(f"  # View CloudWatch alarms:")
        print(f"  aws cloudwatch describe-alarms --region us-gov-west-1")
        print(f"")
        print(f"  # View Lambda logs:")
        print(f"  aws logs tail /aws/lambda/{email_worker_function} --follow --region us-gov-west-1")
        print(f"  aws logs tail /aws/lambda/{campaign_monitor_function} --follow --region us-gov-west-1")
        print(f"")
        print(f"  # Test campaign monitor:")
        print(f"  python campaign_monitor.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
