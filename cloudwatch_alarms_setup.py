#!/usr/bin/env python3
"""
Setup CloudWatch alarms for email worker monitoring
Creates alarms for throttle exceptions and incomplete campaigns
"""

import boto3
import json
from datetime import datetime, timedelta

def create_cloudwatch_alarms():
    """Create CloudWatch alarms for email worker monitoring"""
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    print("🚨 Setting up CloudWatch Alarms for Email Worker")
    print("=" * 60)
    
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
        print("Available functions:")
        for func in functions['Functions']:
            print(f"  - {func['FunctionName']}")
        return False
    
    print(f"✓ Found function: {function_name}")
    
    alarms_created = []
    
    # Alarm 1: Lambda Function Errors
    print("\n📊 Creating Lambda Function Errors Alarm...")
    try:
        alarm1 = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-FunctionErrors',
            AlarmDescription='Email Worker Lambda function errors',
            MetricName='Errors',
            Namespace='AWS/Lambda',
            Statistic='Sum',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': function_name
                }
            ],
            Period=300,  # 5 minutes
            EvaluationPeriods=2,
            Threshold=1.0,
            ComparisonOperator='GreaterThanOrEqualToThreshold',
            TreatMissingData='notBreaching'
        )
        alarms_created.append('EmailWorker-FunctionErrors')
        print("  ✓ Created: EmailWorker-FunctionErrors")
    except Exception as e:
        print(f"  ❌ Failed to create function errors alarm: {str(e)}")
    
    # Alarm 2: Lambda Function Duration (High Duration = Potential Issues)
    print("\n⏱️ Creating Lambda Function Duration Alarm...")
    try:
        alarm2 = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-HighDuration',
            AlarmDescription='Email Worker Lambda function taking too long',
            MetricName='Duration',
            Namespace='AWS/Lambda',
            Statistic='Average',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': function_name
                }
            ],
            Period=300,  # 5 minutes
            EvaluationPeriods=3,
            Threshold=600000.0,  # 10 minutes in milliseconds
            ComparisonOperator='GreaterThanThreshold',
            TreatMissingData='notBreaching'
        )
        alarms_created.append('EmailWorker-HighDuration')
        print("  ✓ Created: EmailWorker-HighDuration")
    except Exception as e:
        print(f"  ❌ Failed to create duration alarm: {str(e)}")
    
    # Alarm 3: Lambda Function Invocations (No Activity = Potential Stop)
    print("\n📈 Creating Lambda Function Activity Alarm...")
    try:
        alarm3 = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-NoActivity',
            AlarmDescription='Email Worker Lambda function has no activity (potential stop)',
            MetricName='Invocations',
            Namespace='AWS/Lambda',
            Statistic='Sum',
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': function_name
                }
            ],
            Period=600,  # 10 minutes
            EvaluationPeriods=3,
            Threshold=1.0,
            ComparisonOperator='LessThanThreshold',
            TreatMissingData='breaching'  # Treat missing data as breach (no activity)
        )
        alarms_created.append('EmailWorker-NoActivity')
        print("  ✓ Created: EmailWorker-NoActivity")
    except Exception as e:
        print(f"  ❌ Failed to create activity alarm: {str(e)}")
    
    # Alarm 4: SQS Queue Depth (Messages Stuck in Queue)
    print("\n📬 Creating SQS Queue Depth Alarm...")
    try:
        sqs = boto3.client('sqs', region_name='us-gov-west-1')
        queues = sqs.list_queues()
        
        queue_url = None
        for url in queues.get('QueueUrls', []):
            if 'bulk-email-queue' in url:
                queue_url = url
                break
        
        if queue_url:
            # Get queue name from URL
            queue_name = queue_url.split('/')[-1]
            
            alarm4 = cloudwatch.put_metric_alarm(
                AlarmName='EmailWorker-QueueBacklog',
                AlarmDescription='SQS queue has too many messages (potential processing stop)',
                MetricName='ApproximateNumberOfVisibleMessages',
                Namespace='AWS/SQS',
                Statistic='Average',
                Dimensions=[
                    {
                        'Name': 'QueueName',
                        'Value': queue_name
                    }
                ],
                Period=300,  # 5 minutes
                EvaluationPeriods=2,
                Threshold=100.0,  # More than 100 messages in queue
                ComparisonOperator='GreaterThanThreshold',
                TreatMissingData='notBreaching'
            )
            alarms_created.append('EmailWorker-QueueBacklog')
            print("  ✓ Created: EmailWorker-QueueBacklog")
        else:
            print("  ⚠️ Could not find bulk-email-queue for monitoring")
    except Exception as e:
        print(f"  ❌ Failed to create SQS queue alarm: {str(e)}")
    
    # Alarm 5: Dead Letter Queue Messages
    print("\n💀 Creating Dead Letter Queue Alarm...")
    try:
        if queue_url:
            # Look for DLQ
            dlq_url = None
            for url in queues.get('QueueUrls', []):
                if 'bulk-email-dlq' in url or 'dlq' in url:
                    dlq_url = url
                    break
            
            if dlq_url:
                dlq_name = dlq_url.split('/')[-1]
                
                alarm5 = cloudwatch.put_metric_alarm(
                    AlarmName='EmailWorker-DLQMessages',
                    AlarmDescription='Dead Letter Queue has messages (email processing failures)',
                    MetricName='ApproximateNumberOfVisibleMessages',
                    Namespace='AWS/SQS',
                    Statistic='Sum',
                    Dimensions=[
                        {
                            'Name': 'QueueName',
                            'Value': dlq_name
                        }
                    ],
                    Period=300,  # 5 minutes
                    EvaluationPeriods=1,
                    Threshold=1.0,  # Any messages in DLQ
                    ComparisonOperator='GreaterThanThreshold',
                    TreatMissingData='notBreaching'
                )
                alarms_created.append('EmailWorker-DLQMessages')
                print("  ✓ Created: EmailWorker-DLQMessages")
            else:
                print("  ⚠️ Could not find Dead Letter Queue for monitoring")
    except Exception as e:
        print(f"  ❌ Failed to create DLQ alarm: {str(e)}")
    
    print(f"\n✅ Created {len(alarms_created)} CloudWatch alarms:")
    for alarm in alarms_created:
        print(f"  - {alarm}")
    
    return alarms_created

def create_custom_metrics_alarms():
    """Create alarms for custom metrics (requires Lambda code updates)"""
    print("\n📊 Setting up Custom Metrics Alarms...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    # These alarms will only work after we update the Lambda function to send custom metrics
    custom_alarms = [
        {
            'name': 'EmailWorker-ThrottleExceptions',
            'description': 'Email Worker detected throttle exceptions',
            'metric': 'ThrottleExceptions',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold'
        },
        {
            'name': 'EmailWorker-IncompleteCampaigns',
            'description': 'Email campaigns not completed within expected time',
            'metric': 'IncompleteCampaigns',
            'threshold': 1.0,
            'operator': 'GreaterThanOrEqualToThreshold'
        },
        {
            'name': 'EmailWorker-HighAttachmentDelays',
            'description': 'High attachment delays detected (large files)',
            'metric': 'AttachmentDelays',
            'threshold': 10.0,
            'operator': 'GreaterThanThreshold'
        }
    ]
    
    alarms_created = []
    
    for alarm_config in custom_alarms:
        try:
            alarm = cloudwatch.put_metric_alarm(
                AlarmName=alarm_config['name'],
                AlarmDescription=alarm_config['description'],
                MetricName=alarm_config['metric'],
                Namespace='EmailWorker/Custom',
                Statistic='Sum',
                Period=300,  # 5 minutes
                EvaluationPeriods=2,
                Threshold=alarm_config['threshold'],
                ComparisonOperator=alarm_config['operator'],
                TreatMissingData='notBreaching'
            )
            alarms_created.append(alarm_config['name'])
            print(f"  ✓ Created: {alarm_config['name']}")
        except Exception as e:
            print(f"  ❌ Failed to create {alarm_config['name']}: {str(e)}")
    
    return alarms_created

def setup_sns_notifications():
    """Setup SNS topic for alarm notifications"""
    print("\n📧 Setting up SNS Notifications...")
    
    sns = boto3.client('sns', region_name='us-gov-west-1')
    
    try:
        # Create SNS topic for email worker alarms
        topic_response = sns.create_topic(
            Name='email-worker-alarms'
        )
        
        topic_arn = topic_response['TopicArn']
        print(f"  ✓ Created SNS topic: {topic_arn}")
        
        # Subscribe to email notifications (you'll need to confirm the subscription)
        subscription = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint='your-email@example.com'  # Replace with actual email
        )
        
        print(f"  ✓ Created email subscription: {subscription['SubscriptionArn']}")
        print("  ⚠️ Please check your email and confirm the subscription")
        
        return topic_arn
        
    except Exception as e:
        print(f"  ❌ Failed to setup SNS notifications: {str(e)}")
        return None

def list_existing_alarms():
    """List existing CloudWatch alarms"""
    print("\n📋 Existing CloudWatch Alarms:")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    try:
        response = cloudwatch.describe_alarms()
        
        if response['MetricAlarms']:
            for alarm in response['MetricAlarms']:
                state = alarm['StateValue']
                state_icon = "🟢" if state == "OK" else "🔴" if state == "ALARM" else "🟡"
                print(f"  {state_icon} {alarm['AlarmName']} - {state}")
        else:
            print("  No alarms found")
            
    except Exception as e:
        print(f"  ❌ Failed to list alarms: {str(e)}")

def main():
    """Main setup function"""
    print("🚨 CloudWatch Alarms Setup for Email Worker")
    print("=" * 60)
    
    try:
        # Create standard alarms
        standard_alarms = create_cloudwatch_alarms()
        
        # Create custom metrics alarms (will be active after Lambda update)
        custom_alarms = create_custom_metrics_alarms()
        
        # Setup SNS notifications (optional)
        print("\n" + "=" * 60)
        response = input("Do you want to setup SNS email notifications? (y/n): ")
        if response.lower() == 'y':
            setup_sns_notifications()
        
        # List all alarms
        list_existing_alarms()
        
        print("\n" + "=" * 60)
        print("✅ CLOUDWATCH ALARMS SETUP COMPLETE!")
        print("=" * 60)
        
        total_alarms = len(standard_alarms) + len(custom_alarms)
        print(f"\nCreated {total_alarms} alarms:")
        print(f"  📊 Standard AWS metrics: {len(standard_alarms)}")
        print(f"  📈 Custom metrics: {len(custom_alarms)}")
        
        print("\n📋 Next Steps:")
        print("  1. Update Lambda function to send custom metrics")
        print("  2. Configure SNS notifications if desired")
        print("  3. Test alarms by triggering conditions")
        print("  4. Monitor alarm states in CloudWatch console")
        
        print("\n🔍 Monitoring Commands:")
        print("  # View all alarms:")
        print("  aws cloudwatch describe-alarms --region us-gov-west-1")
        print()
        print("  # View alarm history:")
        print("  aws cloudwatch describe-alarm-history --region us-gov-west-1")
        print()
        print("  # Test alarm (simulate error):")
        print("  aws lambda invoke --function-name email-worker-function --payload '{}' test-response.json")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
