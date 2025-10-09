#!/usr/bin/env python3
"""
Create CloudWatch Alarms for Email Sending Failures
Monitors custom metrics from email worker to detect email-level failures
"""

import boto3
import sys
from datetime import datetime

def create_email_failure_alarms():
    """Create alarms for email sending failures"""
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    print("=" * 80)
    print("🚨 Creating Email Failure CloudWatch Alarms")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: us-gov-west-1")
    print(f"Namespace: EmailWorker/Custom")
    print()
    
    alarms_created = []
    alarms_failed = []
    
    # Alarm 1: EmailsFailed - Individual email send failures
    print("📧 Creating EmailsFailed Alarm...")
    try:
        response = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-EmailsFailed',
            AlarmDescription='Email Worker - Individual emails failed to send',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='EmailsFailed',
            Namespace='EmailWorker/Custom',
            Period=300,  # 5 minutes
            Statistic='Sum',
            Threshold=5.0,  # Alert if 5+ emails failed in 10 minutes (2 periods)
            ActionsEnabled=True,
            TreatMissingData='notBreaching',
            Tags=[
                {'Key': 'Purpose', 'Value': 'EmailMonitoring'},
                {'Key': 'Severity', 'Value': 'High'}
            ]
        )
        alarms_created.append('EmailWorker-EmailsFailed')
        print("  ✅ Created: EmailWorker-EmailsFailed")
        print(f"     Threshold: 5+ failed emails in 10 minutes")
        print(f"     Period: 5 minutes (2 evaluation periods)")
    except Exception as e:
        alarms_failed.append(('EmailWorker-EmailsFailed', str(e)))
        print(f"  ❌ Failed: {str(e)}")
    
    # Alarm 2: FailureRate - High percentage of failures
    print("\n📊 Creating FailureRate Alarm...")
    try:
        response = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-HighFailureRate',
            AlarmDescription='Email Worker - High percentage of email failures',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='FailureRate',
            Namespace='EmailWorker/Custom',
            Period=300,  # 5 minutes
            Statistic='Average',
            Threshold=10.0,  # Alert if >10% failure rate
            ActionsEnabled=True,
            TreatMissingData='notBreaching',
            Tags=[
                {'Key': 'Purpose', 'Value': 'EmailMonitoring'},
                {'Key': 'Severity', 'Value': 'High'}
            ]
        )
        alarms_created.append('EmailWorker-HighFailureRate')
        print("  ✅ Created: EmailWorker-HighFailureRate")
        print(f"     Threshold: >10% failure rate")
        print(f"     Period: 5 minutes (2 evaluation periods)")
    except Exception as e:
        alarms_failed.append(('EmailWorker-HighFailureRate', str(e)))
        print(f"  ❌ Failed: {str(e)}")
    
    # Alarm 3: Critical Failure Rate - Very high failures
    print("\n🔴 Creating Critical Failure Rate Alarm...")
    try:
        response = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-CriticalFailureRate',
            AlarmDescription='Email Worker - CRITICAL: Very high email failure rate',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=1,  # Trigger faster for critical issues
            MetricName='FailureRate',
            Namespace='EmailWorker/Custom',
            Period=300,  # 5 minutes
            Statistic='Average',
            Threshold=50.0,  # Alert if >50% failure rate (critical)
            ActionsEnabled=True,
            TreatMissingData='notBreaching',
            Tags=[
                {'Key': 'Purpose', 'Value': 'EmailMonitoring'},
                {'Key': 'Severity', 'Value': 'Critical'}
            ]
        )
        alarms_created.append('EmailWorker-CriticalFailureRate')
        print("  ✅ Created: EmailWorker-CriticalFailureRate")
        print(f"     Threshold: >50% failure rate (CRITICAL)")
        print(f"     Period: 5 minutes (1 evaluation period - fast trigger)")
    except Exception as e:
        alarms_failed.append(('EmailWorker-CriticalFailureRate', str(e)))
        print(f"  ❌ Failed: {str(e)}")
    
    # Alarm 4: ThrottleExceptions - AWS SES throttling
    print("\n⏱️  Creating ThrottleExceptions Alarm...")
    try:
        response = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-ThrottleExceptions',
            AlarmDescription='Email Worker - AWS SES throttle exceptions detected',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='ThrottleExceptions',
            Namespace='EmailWorker/Custom',
            Period=300,  # 5 minutes
            Statistic='Sum',
            Threshold=1.0,  # Alert on any throttle exceptions
            ActionsEnabled=True,
            TreatMissingData='notBreaching',
            Tags=[
                {'Key': 'Purpose', 'Value': 'EmailMonitoring'},
                {'Key': 'Severity', 'Value': 'Medium'}
            ]
        )
        alarms_created.append('EmailWorker-ThrottleExceptions')
        print("  ✅ Created: EmailWorker-ThrottleExceptions")
        print(f"     Threshold: Any throttle exceptions in 10 minutes")
        print(f"     Period: 5 minutes (2 evaluation periods)")
    except Exception as e:
        alarms_failed.append(('EmailWorker-ThrottleExceptions', str(e)))
        print(f"  ❌ Failed: {str(e)}")
    
    # Alarm 5: IncompleteCampaigns - Campaigns not finishing
    print("\n📉 Creating IncompleteCampaigns Alarm...")
    try:
        response = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-IncompleteCampaigns',
            AlarmDescription='Email Worker - Campaigns not completing successfully',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=1,
            MetricName='IncompleteCampaigns',
            Namespace='EmailWorker/Custom',
            Period=300,  # 5 minutes
            Statistic='Sum',
            Threshold=1.0,  # Alert on any incomplete campaigns
            ActionsEnabled=True,
            TreatMissingData='notBreaching',
            Tags=[
                {'Key': 'Purpose', 'Value': 'EmailMonitoring'},
                {'Key': 'Severity', 'Value': 'Medium'}
            ]
        )
        alarms_created.append('EmailWorker-IncompleteCampaigns')
        print("  ✅ Created: EmailWorker-IncompleteCampaigns")
        print(f"     Threshold: Any incomplete campaigns")
        print(f"     Period: 5 minutes")
    except Exception as e:
        alarms_failed.append(('EmailWorker-IncompleteCampaigns', str(e)))
        print(f"  ❌ Failed: {str(e)}")
    
    # Alarm 6: High AttachmentDelays - Large attachments causing delays
    print("\n📎 Creating AttachmentDelays Alarm...")
    try:
        response = cloudwatch.put_metric_alarm(
            AlarmName='EmailWorker-HighAttachmentDelays',
            AlarmDescription='Email Worker - High attachment processing delays',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='AttachmentDelays',
            Namespace='EmailWorker/Custom',
            Period=300,  # 5 minutes
            Statistic='Sum',
            Threshold=10.0,  # Alert if 10+ attachment delays in 10 minutes
            ActionsEnabled=True,
            TreatMissingData='notBreaching',
            Tags=[
                {'Key': 'Purpose', 'Value': 'EmailMonitoring'},
                {'Key': 'Severity', 'Value': 'Low'}
            ]
        )
        alarms_created.append('EmailWorker-HighAttachmentDelays')
        print("  ✅ Created: EmailWorker-HighAttachmentDelays")
        print(f"     Threshold: 10+ attachment delays in 10 minutes")
        print(f"     Period: 5 minutes (2 evaluation periods)")
    except Exception as e:
        alarms_failed.append(('EmailWorker-HighAttachmentDelays', str(e)))
        print(f"  ❌ Failed: {str(e)}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 ALARM CREATION SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully Created: {len(alarms_created)}")
    print(f"❌ Failed: {len(alarms_failed)}")
    
    if alarms_created:
        print("\n✅ Created Alarms:")
        for alarm in alarms_created:
            print(f"   • {alarm}")
    
    if alarms_failed:
        print("\n❌ Failed Alarms:")
        for alarm_name, error in alarms_failed:
            print(f"   • {alarm_name}: {error}")
    
    # Show how to view alarms
    print("\n" + "=" * 80)
    print("📋 VIEW ALARMS")
    print("=" * 80)
    print("AWS Console:")
    print("  https://console.aws.amazon.com/cloudwatch/home?region=us-gov-west-1#alarmsV2:")
    print()
    print("AWS CLI:")
    print("  aws cloudwatch describe-alarms --region us-gov-west-1 --alarm-names \\")
    for alarm in alarms_created:
        print(f"    {alarm} \\")
    print()
    
    # Show how to test alarms
    print("=" * 80)
    print("🧪 TEST ALARMS")
    print("=" * 80)
    print("To verify alarms are working, check alarm state:")
    print()
    print("  aws cloudwatch describe-alarms --region us-gov-west-1 \\")
    print("    --query 'MetricAlarms[?starts_with(AlarmName, `EmailWorker`)].{Name:AlarmName,State:StateValue}' \\")
    print("    --output table")
    print()
    
    # Show alarm thresholds
    print("=" * 80)
    print("⚙️  ALARM THRESHOLDS")
    print("=" * 80)
    print("│ Alarm Name                           │ Threshold                          │ Severity │")
    print("├" + "─" * 78 + "┤")
    print("│ EmailWorker-EmailsFailed             │ 5+ failed emails in 10 min         │ High     │")
    print("│ EmailWorker-HighFailureRate          │ >10% failure rate                  │ High     │")
    print("│ EmailWorker-CriticalFailureRate      │ >50% failure rate                  │ Critical │")
    print("│ EmailWorker-ThrottleExceptions       │ Any throttle in 10 min             │ Medium   │")
    print("│ EmailWorker-IncompleteCampaigns      │ Any incomplete campaign            │ Medium   │")
    print("│ EmailWorker-HighAttachmentDelays     │ 10+ attachment delays in 10 min    │ Low      │")
    print("└" + "─" * 78 + "┘")
    print()
    
    # Next steps
    print("=" * 80)
    print("📝 NEXT STEPS")
    print("=" * 80)
    print("1. Configure SNS notifications (optional):")
    print("   python setup_alarm_notifications.py")
    print()
    print("2. View current alarm states:")
    print("   python view_alarm_status.py")
    print()
    print("3. Monitor for triggered alarms:")
    print("   aws cloudwatch describe-alarm-history --region us-gov-west-1")
    print()
    print("4. Search for errors in logs:")
    print("   python search_lambda_errors_with_code.py email-worker-function")
    print()
    
    return len(alarms_created), len(alarms_failed)


def view_existing_alarms():
    """View existing email worker alarms"""
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    print("\n" + "=" * 80)
    print("📋 EXISTING EMAIL WORKER ALARMS")
    print("=" * 80)
    
    try:
        # Get all alarms
        response = cloudwatch.describe_alarms(
            AlarmNamePrefix='EmailWorker-'
        )
        
        alarms = response['MetricAlarms']
        
        if not alarms:
            print("⚠️  No EmailWorker alarms found")
            return
        
        print(f"Found {len(alarms)} alarm(s)\n")
        
        for alarm in alarms:
            state = alarm['StateValue']
            state_icon = {
                'OK': '🟢',
                'ALARM': '🔴',
                'INSUFFICIENT_DATA': '🟡'
            }.get(state, '⚪')
            
            print(f"{state_icon} {alarm['AlarmName']}")
            print(f"   State: {state}")
            print(f"   Metric: {alarm['Namespace']} / {alarm['MetricName']}")
            print(f"   Threshold: {alarm['ComparisonOperator']} {alarm['Threshold']}")
            
            if alarm.get('StateReason'):
                print(f"   Reason: {alarm['StateReason']}")
            
            if alarm.get('StateUpdatedTimestamp'):
                print(f"   Last Updated: {alarm['StateUpdatedTimestamp']}")
            
            print()
        
    except Exception as e:
        print(f"❌ Error fetching alarms: {str(e)}")


def delete_email_failure_alarms():
    """Delete email failure alarms (cleanup utility)"""
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    alarm_names = [
        'EmailWorker-EmailsFailed',
        'EmailWorker-HighFailureRate',
        'EmailWorker-CriticalFailureRate',
        'EmailWorker-ThrottleExceptions',
        'EmailWorker-IncompleteCampaigns',
        'EmailWorker-HighAttachmentDelays'
    ]
    
    print("\n" + "=" * 80)
    print("🗑️  DELETING EMAIL FAILURE ALARMS")
    print("=" * 80)
    
    deleted = []
    failed = []
    
    for alarm_name in alarm_names:
        try:
            cloudwatch.delete_alarms(AlarmNames=[alarm_name])
            deleted.append(alarm_name)
            print(f"  ✅ Deleted: {alarm_name}")
        except Exception as e:
            failed.append((alarm_name, str(e)))
            print(f"  ❌ Failed to delete {alarm_name}: {str(e)}")
    
    print(f"\n✅ Deleted: {len(deleted)}")
    print(f"❌ Failed: {len(failed)}")


def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'view':
            view_existing_alarms()
            return
        elif command == 'delete':
            print("⚠️  WARNING: This will delete all email failure alarms!")
            response = input("Are you sure? (yes/no): ").strip().lower()
            if response == 'yes':
                delete_email_failure_alarms()
            else:
                print("Cancelled.")
            return
        elif command == 'help':
            print("Usage: python create_email_failure_alarms.py [command]")
            print()
            print("Commands:")
            print("  (none)  - Create email failure alarms")
            print("  view    - View existing alarms")
            print("  delete  - Delete email failure alarms")
            print("  help    - Show this help")
            return
    
    # Default: create alarms
    created, failed = create_email_failure_alarms()
    
    if failed > 0:
        print("\n⚠️  Some alarms failed to create. Check errors above.")
        sys.exit(1)
    else:
        print("\n✅ All alarms created successfully!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

