#!/usr/bin/env python3
"""
View CloudWatch Alarm Status
Shows current state of all email worker alarms with details
"""

import boto3
import sys
from datetime import datetime
from collections import defaultdict

def view_alarm_status(show_all=False):
    """View status of email worker alarms"""
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    print("=" * 80)
    print("📊 CloudWatch Alarm Status - Email Worker")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: us-gov-west-1")
    print()
    
    try:
        # Get all alarms (or just EmailWorker alarms)
        if show_all:
            response = cloudwatch.describe_alarms()
            title = "All CloudWatch Alarms"
        else:
            response = cloudwatch.describe_alarms(
                AlarmNamePrefix='EmailWorker-'
            )
            title = "Email Worker Alarms"
        
        alarms = response['MetricAlarms']
        
        if not alarms:
            print(f"⚠️  No alarms found")
            return
        
        # Group by state
        grouped = defaultdict(list)
        for alarm in alarms:
            grouped[alarm['StateValue']].append(alarm)
        
        # Summary
        ok_count = len(grouped.get('OK', []))
        alarm_count = len(grouped.get('ALARM', []))
        insufficient_count = len(grouped.get('INSUFFICIENT_DATA', []))
        
        print(f"📋 {title}")
        print(f"   Total: {len(alarms)}")
        print(f"   🟢 OK: {ok_count}")
        print(f"   🔴 ALARM: {alarm_count}")
        print(f"   🟡 INSUFFICIENT_DATA: {insufficient_count}")
        print()
        
        # Show alarms in ALARM state first (most critical)
        if grouped.get('ALARM'):
            print("=" * 80)
            print("🔴 ALARMS TRIGGERED")
            print("=" * 80)
            for alarm in grouped['ALARM']:
                print_alarm_details(alarm, cloudwatch)
        
        # Show insufficient data (potential issues)
        if grouped.get('INSUFFICIENT_DATA'):
            print("=" * 80)
            print("🟡 INSUFFICIENT DATA")
            print("=" * 80)
            for alarm in grouped['INSUFFICIENT_DATA']:
                print_alarm_details(alarm, cloudwatch)
        
        # Show OK alarms
        if grouped.get('OK'):
            print("=" * 80)
            print("🟢 OK ALARMS")
            print("=" * 80)
            for alarm in grouped['OK']:
                print_alarm_details(alarm, cloudwatch, show_detail=False)
        
        # Action items if alarms triggered
        if alarm_count > 0:
            print("\n" + "=" * 80)
            print("🚨 ACTION REQUIRED")
            print("=" * 80)
            print("Alarms have been triggered! Recommended actions:")
            print()
            print("1. Search for errors in CloudWatch Logs:")
            print("   python search_lambda_errors_with_code.py email-worker-function")
            print()
            print("2. Check recent Lambda invocations:")
            print("   python tail_lambda_logs.py email-worker-function")
            print()
            print("3. View detailed alarm history:")
            print("   python view_alarm_status.py --history")
            print()
            print("4. Check campaign status in DynamoDB")
            print()
        
    except Exception as e:
        print(f"❌ Error fetching alarms: {str(e)}")
        import traceback
        traceback.print_exc()


def print_alarm_details(alarm, cloudwatch, show_detail=True):
    """Print detailed alarm information"""
    state = alarm['StateValue']
    state_icon = {
        'OK': '🟢',
        'ALARM': '🔴',
        'INSUFFICIENT_DATA': '🟡'
    }.get(state, '⚪')
    
    print(f"\n{state_icon} {alarm['AlarmName']}")
    print(f"   Description: {alarm.get('AlarmDescription', 'N/A')}")
    print(f"   State: {state}")
    
    if show_detail or state == 'ALARM':
        print(f"   Metric: {alarm['Namespace']} / {alarm['MetricName']}")
        print(f"   Threshold: {alarm['ComparisonOperator']} {alarm['Threshold']}")
        print(f"   Period: {alarm['Period']}s ({alarm['EvaluationPeriods']} periods)")
        print(f"   Statistic: {alarm['Statistic']}")
        
        if alarm.get('StateReason'):
            print(f"   Reason: {alarm['StateReason']}")
        
        if alarm.get('StateUpdatedTimestamp'):
            updated = alarm['StateUpdatedTimestamp']
            print(f"   Last Updated: {updated.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if alarm.get('StateTransitionedTimestamp'):
            transitioned = alarm['StateTransitionedTimestamp']
            print(f"   State Changed: {transitioned.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show recent datapoints if in ALARM state
        if state == 'ALARM' and show_detail:
            try:
                # Get recent metric data
                from datetime import timedelta
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=1)
                
                response = cloudwatch.get_metric_statistics(
                    Namespace=alarm['Namespace'],
                    MetricName=alarm['MetricName'],
                    Dimensions=alarm.get('Dimensions', []),
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=alarm['Period'],
                    Statistics=[alarm['Statistic']]
                )
                
                if response['Datapoints']:
                    print(f"   Recent Data (last hour):")
                    datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
                    for dp in datapoints[:5]:  # Show last 5 datapoints
                        value = dp.get(alarm['Statistic'], 0)
                        timestamp = dp['Timestamp'].strftime('%H:%M:%S')
                        print(f"     {timestamp}: {value:.2f}")
            except Exception as e:
                print(f"     (Could not fetch recent data: {str(e)})")


def view_alarm_history(hours=24):
    """View alarm history"""
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    from datetime import timedelta
    
    print("=" * 80)
    print("📜 CloudWatch Alarm History")
    print("=" * 80)
    print(f"Last {hours} hours")
    print()
    
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        response = cloudwatch.describe_alarm_history(
            AlarmNamePrefix='EmailWorker-',
            HistoryItemType='StateUpdate',
            StartDate=start_time,
            EndDate=end_time,
            MaxRecords=50
        )
        
        history_items = response.get('AlarmHistoryItems', [])
        
        if not history_items:
            print("✅ No alarm state changes in the last 24 hours")
            return
        
        print(f"Found {len(history_items)} state change(s)\n")
        
        for item in history_items:
            timestamp = item['Timestamp']
            alarm_name = item['AlarmName']
            
            # Parse history data
            import json
            try:
                history_data = json.loads(item['HistoryData'])
                old_state = history_data.get('oldState', {}).get('stateValue', 'UNKNOWN')
                new_state = history_data.get('newState', {}).get('stateValue', 'UNKNOWN')
                reason = history_data.get('newState', {}).get('stateReason', '')
                
                state_icon = {
                    'OK': '🟢',
                    'ALARM': '🔴',
                    'INSUFFICIENT_DATA': '🟡'
                }.get(new_state, '⚪')
                
                print(f"{state_icon} {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Alarm: {alarm_name}")
                print(f"   Change: {old_state} → {new_state}")
                if reason:
                    print(f"   Reason: {reason}")
                print()
                
            except Exception as e:
                print(f"⚠️  Could not parse history data: {str(e)}")
                print()
        
    except Exception as e:
        print(f"❌ Error fetching alarm history: {str(e)}")


def test_alarm(alarm_name):
    """Set alarm to ALARM state for testing"""
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    print(f"🧪 Testing alarm: {alarm_name}")
    print("⚠️  This will temporarily set the alarm to ALARM state")
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Cancelled.")
        return
    
    try:
        cloudwatch.set_alarm_state(
            AlarmName=alarm_name,
            StateValue='ALARM',
            StateReason='Manual test triggered by user'
        )
        print(f"✅ Alarm {alarm_name} set to ALARM state")
        print("💡 The alarm will automatically reset when metric data is evaluated")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == '--all':
            view_alarm_status(show_all=True)
        elif command == '--history':
            hours = 24
            if len(sys.argv) > 2:
                try:
                    hours = int(sys.argv[2])
                except ValueError:
                    pass
            view_alarm_history(hours=hours)
        elif command == '--test':
            if len(sys.argv) > 2:
                test_alarm(sys.argv[2])
            else:
                print("Usage: python view_alarm_status.py --test <alarm-name>")
        elif command == '--help':
            print("Usage: python view_alarm_status.py [option]")
            print()
            print("Options:")
            print("  (none)      - View EmailWorker alarm status")
            print("  --all       - View all CloudWatch alarms")
            print("  --history [hours] - View alarm history (default: 24 hours)")
            print("  --test <alarm-name> - Test alarm by setting to ALARM state")
            print("  --help      - Show this help")
            print()
            print("Examples:")
            print("  python view_alarm_status.py")
            print("  python view_alarm_status.py --all")
            print("  python view_alarm_status.py --history 48")
            print("  python view_alarm_status.py --test EmailWorker-EmailsFailed")
        else:
            print(f"Unknown option: {command}")
            print("Use --help for usage information")
    else:
        # Default: view EmailWorker alarms
        view_alarm_status(show_all=False)


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

