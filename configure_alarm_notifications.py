#!/usr/bin/env python3
"""
Configure CloudWatch Alarm Notifications
Adds SNS topic to existing email failure alarms for notifications
"""

import boto3
import sys
from datetime import datetime

def configure_alarm_notifications(sns_topic_arn):
    """Add SNS topic to all email worker alarms"""
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    sns = boto3.client('sns', region_name='us-gov-west-1')
    
    print("=" * 80)
    print("🔔 Configuring CloudWatch Alarm Notifications")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"SNS Topic ARN: {sns_topic_arn}")
    print()
    
    # Verify SNS topic exists
    print("📋 Verifying SNS topic...")
    try:
        topic_attrs = sns.get_topic_attributes(TopicArn=sns_topic_arn)
        print(f"   ✅ Topic exists: {topic_attrs['Attributes'].get('DisplayName', 'N/A')}")
        print(f"   Subscriptions: Check SNS console")
    except Exception as e:
        print(f"   ❌ ERROR: Cannot access SNS topic: {str(e)}")
        print(f"   Please verify the topic ARN is correct and you have permissions")
        return False
    
    # Get all EmailWorker alarms
    print("\n📊 Finding EmailWorker alarms...")
    try:
        response = cloudwatch.describe_alarms(AlarmNamePrefix='EmailWorker-')
        alarms = response['MetricAlarms']
        
        if not alarms:
            print("   ⚠️  No EmailWorker alarms found")
            print("   Run: python create_email_failure_alarms.py")
            return False
        
        print(f"   ✅ Found {len(alarms)} alarm(s)")
        for alarm in alarms:
            print(f"      • {alarm['AlarmName']}")
    
    except Exception as e:
        print(f"   ❌ Error finding alarms: {str(e)}")
        return False
    
    # Update each alarm with SNS topic
    print(f"\n🔧 Updating alarms with SNS topic...")
    updated = []
    failed = []
    
    for alarm in alarms:
        alarm_name = alarm['AlarmName']
        
        try:
            # Get current alarm configuration
            current_actions = alarm.get('AlarmActions', [])
            
            # Check if this SNS topic is already configured
            if sns_topic_arn in current_actions:
                print(f"   ℹ️  {alarm_name}: SNS topic already configured")
                updated.append(alarm_name)
                continue
            
            # Add SNS topic to alarm actions
            new_actions = current_actions + [sns_topic_arn]
            
            # Update the alarm with the new actions
            cloudwatch.put_metric_alarm(
                AlarmName=alarm['AlarmName'],
                AlarmDescription=alarm.get('AlarmDescription', ''),
                ComparisonOperator=alarm['ComparisonOperator'],
                EvaluationPeriods=alarm['EvaluationPeriods'],
                MetricName=alarm['MetricName'],
                Namespace=alarm['Namespace'],
                Period=alarm['Period'],
                Statistic=alarm['Statistic'],
                Threshold=alarm['Threshold'],
                ActionsEnabled=True,
                AlarmActions=new_actions,
                TreatMissingData=alarm.get('TreatMissingData', 'notBreaching'),
                Dimensions=alarm.get('Dimensions', [])
            )
            
            updated.append(alarm_name)
            print(f"   ✅ {alarm_name}: SNS topic added")
            
        except Exception as e:
            failed.append((alarm_name, str(e)))
            print(f"   ❌ {alarm_name}: Failed - {str(e)}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 CONFIGURATION SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully Updated: {len(updated)}")
    print(f"❌ Failed: {len(failed)}")
    
    if updated:
        print("\n✅ Updated Alarms:")
        for alarm in updated:
            print(f"   • {alarm}")
    
    if failed:
        print("\n❌ Failed Alarms:")
        for alarm_name, error in failed:
            print(f"   • {alarm_name}: {error}")
    
    # Next steps
    print("\n" + "=" * 80)
    print("📝 NEXT STEPS")
    print("=" * 80)
    print("1. Verify SNS subscriptions:")
    print(f"   aws sns list-subscriptions-by-topic --topic-arn {sns_topic_arn}")
    print()
    print("2. Test an alarm (optional):")
    print("   python view_alarm_status.py --test EmailWorker-EmailsFailed")
    print()
    print("3. View alarm status:")
    print("   python view_alarm_status.py")
    print()
    print("4. To trigger a notification, wait for actual email failures OR:")
    print("   aws cloudwatch set-alarm-state --alarm-name EmailWorker-EmailsFailed \\")
    print("     --state-value ALARM --state-reason 'Test notification'")
    print()
    
    return len(updated), len(failed)


def remove_notifications(sns_topic_arn=None):
    """Remove SNS topic from all alarms"""
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    print("=" * 80)
    print("🔕 Removing Alarm Notifications")
    print("=" * 80)
    
    if sns_topic_arn:
        print(f"Removing specific SNS topic: {sns_topic_arn}")
    else:
        print("Removing ALL SNS topics from alarms")
    
    # Get all EmailWorker alarms
    response = cloudwatch.describe_alarms(AlarmNamePrefix='EmailWorker-')
    alarms = response['MetricAlarms']
    
    if not alarms:
        print("⚠️  No EmailWorker alarms found")
        return
    
    updated = []
    
    for alarm in alarms:
        alarm_name = alarm['AlarmName']
        current_actions = alarm.get('AlarmActions', [])
        
        if not current_actions:
            print(f"   ℹ️  {alarm_name}: No actions configured")
            continue
        
        # Filter out the SNS topic
        if sns_topic_arn:
            new_actions = [action for action in current_actions if action != sns_topic_arn]
        else:
            new_actions = []  # Remove all
        
        if new_actions == current_actions:
            print(f"   ℹ️  {alarm_name}: No matching SNS topics to remove")
            continue
        
        try:
            # Update alarm without SNS actions
            cloudwatch.put_metric_alarm(
                AlarmName=alarm['AlarmName'],
                AlarmDescription=alarm.get('AlarmDescription', ''),
                ComparisonOperator=alarm['ComparisonOperator'],
                EvaluationPeriods=alarm['EvaluationPeriods'],
                MetricName=alarm['MetricName'],
                Namespace=alarm['Namespace'],
                Period=alarm['Period'],
                Statistic=alarm['Statistic'],
                Threshold=alarm['Threshold'],
                ActionsEnabled=True,
                AlarmActions=new_actions,
                TreatMissingData=alarm.get('TreatMissingData', 'notBreaching'),
                Dimensions=alarm.get('Dimensions', [])
            )
            
            updated.append(alarm_name)
            print(f"   ✅ {alarm_name}: Removed {len(current_actions) - len(new_actions)} action(s)")
            
        except Exception as e:
            print(f"   ❌ {alarm_name}: Failed - {str(e)}")
    
    print(f"\n✅ Updated {len(updated)} alarm(s)")


def create_sns_topic(topic_name, email_addresses):
    """Create SNS topic and subscribe email addresses"""
    
    sns = boto3.client('sns', region_name='us-gov-west-1')
    
    print("=" * 80)
    print("📧 Creating SNS Topic for Alarm Notifications")
    print("=" * 80)
    print(f"Topic Name: {topic_name}")
    print(f"Email Addresses: {', '.join(email_addresses)}")
    print()
    
    # Create topic
    print("📋 Creating SNS topic...")
    try:
        response = sns.create_topic(Name=topic_name)
        topic_arn = response['TopicArn']
        print(f"   ✅ Created topic: {topic_arn}")
    except Exception as e:
        print(f"   ❌ Failed to create topic: {str(e)}")
        return None
    
    # Subscribe email addresses
    print("\n📧 Subscribing email addresses...")
    subscribed = []
    failed = []
    
    for email in email_addresses:
        try:
            response = sns.subscribe(
                TopicArn=topic_arn,
                Protocol='email',
                Endpoint=email
            )
            subscribed.append(email)
            print(f"   ✅ Subscribed: {email}")
            print(f"      ⚠️  Check {email} inbox and confirm subscription!")
        except Exception as e:
            failed.append((email, str(e)))
            print(f"   ❌ Failed to subscribe {email}: {str(e)}")
    
    print(f"\n✅ Subscribed {len(subscribed)} email address(es)")
    if failed:
        print(f"❌ Failed: {len(failed)}")
    
    print("\n⚠️  IMPORTANT: Each email address must confirm their subscription!")
    print("   Check inbox for AWS SNS confirmation email and click the link")
    
    return topic_arn


def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("=" * 80)
        print("🔔 CloudWatch Alarm Notification Configuration")
        print("=" * 80)
        print()
        print("Usage: python configure_alarm_notifications.py <command> [options]")
        print()
        print("Commands:")
        print()
        print("  add <sns-topic-arn>")
        print("    Add SNS topic to all EmailWorker alarms")
        print("    Example: python configure_alarm_notifications.py add arn:aws-us-gov:sns:us-gov-west-1:123456:MyTopic")
        print()
        print("  create <topic-name> <email1> [email2] [email3] ...")
        print("    Create new SNS topic and subscribe emails, then add to alarms")
        print("    Example: python configure_alarm_notifications.py create EmailAlerts admin@agency.gov user@agency.gov")
        print()
        print("  remove [sns-topic-arn]")
        print("    Remove SNS topic from alarms (or remove all if no ARN provided)")
        print("    Example: python configure_alarm_notifications.py remove")
        print("    Example: python configure_alarm_notifications.py remove arn:aws-us-gov:sns:...")
        print()
        print("  list")
        print("    List current alarm notification configurations")
        print()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("❌ Error: SNS topic ARN required")
            print("Usage: python configure_alarm_notifications.py add <sns-topic-arn>")
            print()
            print("Example:")
            print("  python configure_alarm_notifications.py add arn:aws-us-gov:sns:us-gov-west-1:123456789012:EmailAlerts")
            sys.exit(1)
        
        sns_topic_arn = sys.argv[2]
        updated, failed = configure_alarm_notifications(sns_topic_arn)
        
        if failed > 0:
            sys.exit(1)
        else:
            print("\n✅ All alarms configured successfully!")
            sys.exit(0)
    
    elif command == 'create':
        if len(sys.argv) < 4:
            print("❌ Error: Topic name and at least one email address required")
            print("Usage: python configure_alarm_notifications.py create <topic-name> <email1> [email2] ...")
            print()
            print("Example:")
            print("  python configure_alarm_notifications.py create EmailAlerts admin@agency.gov ops@agency.gov")
            sys.exit(1)
        
        topic_name = sys.argv[2]
        email_addresses = sys.argv[3:]
        
        # Create SNS topic and subscribe emails
        topic_arn = create_sns_topic(topic_name, email_addresses)
        
        if not topic_arn:
            print("\n❌ Failed to create SNS topic")
            sys.exit(1)
        
        # Add topic to alarms
        print("\n" + "=" * 80)
        updated, failed = configure_alarm_notifications(topic_arn)
        
        if failed > 0:
            sys.exit(1)
        else:
            print("\n✅ SNS topic created and configured successfully!")
            print(f"\n⚠️  Don't forget: Check email inboxes and confirm SNS subscriptions!")
            sys.exit(0)
    
    elif command == 'remove':
        sns_topic_arn = sys.argv[2] if len(sys.argv) > 2 else None
        remove_notifications(sns_topic_arn)
    
    elif command == 'list':
        cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
        
        print("=" * 80)
        print("📋 Current Alarm Notification Configuration")
        print("=" * 80)
        
        response = cloudwatch.describe_alarms(AlarmNamePrefix='EmailWorker-')
        alarms = response['MetricAlarms']
        
        if not alarms:
            print("⚠️  No EmailWorker alarms found")
            return
        
        for alarm in alarms:
            actions = alarm.get('AlarmActions', [])
            print(f"\n{alarm['AlarmName']}")
            print(f"   State: {alarm['StateValue']}")
            if actions:
                print(f"   Notifications: {len(actions)} configured")
                for action in actions:
                    print(f"      • {action}")
            else:
                print(f"   Notifications: None configured")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run without arguments to see usage")
        sys.exit(1)


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

