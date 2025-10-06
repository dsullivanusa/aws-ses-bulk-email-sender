#!/usr/bin/env python3
"""
Check existing CloudWatch alarms and create missing ones
"""

import boto3
import json

def check_existing_alarms():
    """Check what alarms currently exist"""
    print("🔍 Checking Existing CloudWatch Alarms...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    try:
        response = cloudwatch.describe_alarms()
        alarms = response['MetricAlarms']
        
        print(f"📊 Found {len(alarms)} total alarms:")
        
        email_worker_alarms = []
        campaign_monitor_alarms = []
        
        for alarm in alarms:
            alarm_name = alarm['AlarmName']
            state = alarm['StateValue']
            state_icon = "🟢" if state == "OK" else "🔴" if state == "ALARM" else "🟡"
            
            print(f"  {state_icon} {alarm_name} - {state}")
            
            if 'EmailWorker' in alarm_name:
                email_worker_alarms.append(alarm_name)
            elif 'CampaignMonitor' in alarm_name:
                campaign_monitor_alarms.append(alarm_name)
        
        print(f"\n📋 Email Worker Alarms: {len(email_worker_alarms)}")
        for alarm in email_worker_alarms:
            print(f"  ✓ {alarm}")
        
        print(f"\n📋 Campaign Monitor Alarms: {len(campaign_monitor_alarms)}")
        for alarm in campaign_monitor_alarms:
            print(f"  ✓ {alarm}")
        
        return email_worker_alarms, campaign_monitor_alarms
        
    except Exception as e:
        print(f"❌ Error checking alarms: {str(e)}")
        return [], []

def create_missing_campaign_monitor_alarms():
    """Create missing Campaign Monitor alarms"""
    print("\n🚨 Creating Missing Campaign Monitor Alarms...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    # Campaign Monitor alarms that should exist
    campaign_alarms = [
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
    
    for alarm_config in campaign_alarms:
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
            
            cloudwatch.put_metric_alarm(**alarm_params)
            created_alarms.append(alarm_config['name'])
            print(f"    ✅ Created: {alarm_config['name']}")
            
        except Exception as e:
            print(f"    ❌ Failed to create {alarm_config['name']}: {str(e)}")
    
    return created_alarms

def create_missing_email_worker_alarms():
    """Create missing Email Worker alarms"""
    print("\n🚨 Creating Missing Email Worker Alarms...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    # Find the email worker function
    functions = lambda_client.list_functions()
    function_name = None
    
    for func in functions['Functions']:
        if 'email-worker' in func['FunctionName'].lower():
            function_name = func['FunctionName']
            break
    
    if not function_name:
        print("❌ Could not find email worker function")
        return []
    
    print(f"✓ Found email worker function: {function_name}")
    
    # Email Worker alarms that should exist
    email_alarms = [
        {
            'name': 'EmailWorker-FunctionErrors',
            'description': 'Email Worker Lambda function errors',
            'metric': 'Errors',
            'namespace': 'AWS/Lambda',
            'statistic': 'Sum',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold',
            'period': 300,
            'evaluation_periods': 2,
            'dimensions': [{'Name': 'FunctionName', 'Value': function_name}]
        },
        {
            'name': 'EmailWorker-HighDuration',
            'description': 'Email Worker Lambda function taking too long',
            'metric': 'Duration',
            'namespace': 'AWS/Lambda',
            'statistic': 'Average',
            'threshold': 600000.0,  # 10 minutes in milliseconds
            'operator': 'GreaterThanThreshold',
            'period': 300,
            'evaluation_periods': 3,
            'dimensions': [{'Name': 'FunctionName', 'Value': function_name}]
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
    
    for alarm_config in email_alarms:
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
            
            # Add dimensions if specified
            if 'dimensions' in alarm_config:
                alarm_params['Dimensions'] = alarm_config['dimensions']
            
            cloudwatch.put_metric_alarm(**alarm_params)
            created_alarms.append(alarm_config['name'])
            print(f"    ✅ Created: {alarm_config['name']}")
            
        except Exception as e:
            print(f"    ❌ Failed to create {alarm_config['name']}: {str(e)}")
    
    return created_alarms

def create_sqs_alarms():
    """Create SQS-related alarms"""
    print("\n📬 Creating SQS Alarms...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    sqs = boto3.client('sqs', region_name='us-gov-west-1')
    
    try:
        # Get queue URLs
        queues = sqs.list_queues()
        queue_metrics = {}
        
        for queue_url in queues.get('QueueUrls', []):
            queue_name = queue_url.split('/')[-1]
            
            if 'bulk-email' in queue_name.lower():
                # Create queue backlog alarm
                try:
                    alarm_params = {
                        'AlarmName': f'EmailWorker-QueueBacklog-{queue_name}',
                        'AlarmDescription': f'SQS queue {queue_name} has too many messages',
                        'MetricName': 'ApproximateNumberOfVisibleMessages',
                        'Namespace': 'AWS/SQS',
                        'Statistic': 'Average',
                        'Dimensions': [{'Name': 'QueueName', 'Value': queue_name}],
                        'Period': 300,
                        'EvaluationPeriods': 2,
                        'Threshold': 100.0,
                        'ComparisonOperator': 'GreaterThanThreshold',
                        'TreatMissingData': 'notBreaching'
                    }
                    
                    cloudwatch.put_metric_alarm(**alarm_params)
                    print(f"  ✅ Created queue backlog alarm for {queue_name}")
                    
                except Exception as e:
                    print(f"  ❌ Failed to create queue alarm for {queue_name}: {str(e)}")
                
                # Check for DLQ
                if 'dlq' in queue_name.lower():
                    try:
                        alarm_params = {
                            'AlarmName': f'EmailWorker-DLQMessages-{queue_name}',
                            'AlarmDescription': f'Dead Letter Queue {queue_name} has messages',
                            'MetricName': 'ApproximateNumberOfVisibleMessages',
                            'Namespace': 'AWS/SQS',
                            'Statistic': 'Sum',
                            'Dimensions': [{'Name': 'QueueName', 'Value': queue_name}],
                            'Period': 300,
                            'EvaluationPeriods': 1,
                            'Threshold': 1.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'TreatMissingData': 'notBreaching'
                        }
                        
                        cloudwatch.put_metric_alarm(**alarm_params)
                        print(f"  ✅ Created DLQ alarm for {queue_name}")
                        
                    except Exception as e:
                        print(f"  ❌ Failed to create DLQ alarm for {queue_name}: {str(e)}")
        
    except Exception as e:
        print(f"❌ Error creating SQS alarms: {str(e)}")

def main():
    """Main function to check and create missing alarms"""
    print("🚨 CloudWatch Alarms Check and Creation")
    print("=" * 60)
    
    try:
        # Check existing alarms
        email_alarms, campaign_alarms = check_existing_alarms()
        
        # Create missing alarms
        created_email_alarms = create_missing_email_worker_alarms()
        created_campaign_alarms = create_missing_campaign_monitor_alarms()
        create_sqs_alarms()
        
        print("\n" + "=" * 60)
        print("✅ ALARM CHECK AND CREATION COMPLETE!")
        print("=" * 60)
        
        print(f"\n📊 Summary:")
        print(f"  📧 Email Worker alarms created: {len(created_email_alarms)}")
        print(f"  🔍 Campaign Monitor alarms created: {len(created_campaign_alarms)}")
        
        if created_campaign_alarms:
            print(f"\n🎯 Campaign Monitor Alarms:")
            for alarm in created_campaign_alarms:
                print(f"  ✅ {alarm}")
        
        print(f"\n🔍 Next Steps:")
        print(f"  1. Verify alarms in CloudWatch console")
        print(f"  2. Test campaign monitoring functionality")
        print(f"  3. Monitor alarm states")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
