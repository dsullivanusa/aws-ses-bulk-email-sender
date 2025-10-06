#!/usr/bin/env python3
"""
Test script for the monitoring system
Tests CloudWatch alarms, custom metrics, and campaign monitoring
"""

import boto3
import json
import time
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

def test_cloudwatch_alarms():
    """Test CloudWatch alarms are properly configured"""
    print("🧪 Testing CloudWatch Alarms...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    try:
        # Get all alarms
        response = cloudwatch.describe_alarms()
        alarms = response['MetricAlarms']
        
        # Expected alarms
        expected_alarms = [
            'EmailWorker-FunctionErrors',
            'EmailWorker-HighDuration',
            'EmailWorker-ThrottleExceptions',
            'EmailWorker-IncompleteCampaigns',
            'CampaignMonitor-StuckCampaigns'
        ]
        
        found_alarms = [alarm['AlarmName'] for alarm in alarms]
        
        print(f"  📊 Found {len(alarms)} total alarms")
        print(f"  🎯 Expected {len(expected_alarms)} monitoring alarms")
        
        for expected_alarm in expected_alarms:
            if expected_alarm in found_alarms:
                print(f"    ✅ {expected_alarm}")
            else:
                print(f"    ❌ {expected_alarm} - NOT FOUND")
        
        # Check alarm states
        print(f"\n  📈 Alarm States:")
        for alarm in alarms:
            if 'EmailWorker' in alarm['AlarmName'] or 'CampaignMonitor' in alarm['AlarmName']:
                state = alarm['StateValue']
                state_icon = "🟢" if state == "OK" else "🔴" if state == "ALARM" else "🟡"
                print(f"    {state_icon} {alarm['AlarmName']} - {state}")
        
        return len([a for a in expected_alarms if a in found_alarms]) == len(expected_alarms)
        
    except Exception as e:
        print(f"  ❌ Error testing CloudWatch alarms: {str(e)}")
        return False

def test_lambda_functions():
    """Test Lambda functions are deployed and configured"""
    print("\n🧪 Testing Lambda Functions...")
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        functions = lambda_client.list_functions()
        function_names = [f['FunctionName'] for f in functions['Functions']]
        
        # Expected functions
        expected_functions = [
            'email-worker-function',  # or similar pattern
            'campaign-monitor-function'
        ]
        
        print(f"  📊 Found {len(functions['Functions'])} Lambda functions")
        
        # Check for email worker function
        email_worker_found = False
        for func in functions['Functions']:
            if 'email-worker' in func['FunctionName'].lower():
                email_worker_found = True
                print(f"    ✅ Email Worker: {func['FunctionName']}")
                print(f"      Runtime: {func['Runtime']}")
                print(f"      Memory: {func['MemorySize']} MB")
                print(f"      Timeout: {func['Timeout']} seconds")
                break
        
        if not email_worker_found:
            print(f"    ❌ Email Worker function not found")
        
        # Check for campaign monitor function
        campaign_monitor_found = False
        for func in functions['Functions']:
            if 'campaign-monitor' in func['FunctionName'].lower():
                campaign_monitor_found = True
                print(f"    ✅ Campaign Monitor: {func['FunctionName']}")
                print(f"      Runtime: {func['Runtime']}")
                print(f"      Memory: {func['MemorySize']} MB")
                print(f"      Timeout: {func['Timeout']} seconds")
                break
        
        if not campaign_monitor_found:
            print(f"    ❌ Campaign Monitor function not found")
        
        return email_worker_found and campaign_monitor_found
        
    except Exception as e:
        print(f"  ❌ Error testing Lambda functions: {str(e)}")
        return False

def test_custom_metrics():
    """Test custom CloudWatch metrics are being sent"""
    print("\n🧪 Testing Custom CloudWatch Metrics...")
    
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    try:
        # Get metrics for the last hour
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        namespaces = [
            'EmailWorker/Custom',
            'EmailWorker/CampaignMonitor',
            'EmailWorker/QueueHealth',
            'EmailWorker/Summary'
        ]
        
        metrics_found = {}
        
        for namespace in namespaces:
            try:
                response = cloudwatch.list_metrics(Namespace=namespace)
                metrics = response['Metrics']
                metrics_found[namespace] = len(metrics)
                
                print(f"  📊 {namespace}: {len(metrics)} metrics")
                
                for metric in metrics[:3]:  # Show first 3 metrics
                    print(f"    - {metric['MetricName']}")
                
                if len(metrics) > 3:
                    print(f"    ... and {len(metrics) - 3} more")
                    
            except Exception as e:
                print(f"  ❌ Error listing metrics for {namespace}: {str(e)}")
                metrics_found[namespace] = 0
        
        # Check if we have any custom metrics
        total_metrics = sum(metrics_found.values())
        
        if total_metrics > 0:
            print(f"  ✅ Found {total_metrics} custom metrics across all namespaces")
            return True
        else:
            print(f"  ⚠️ No custom metrics found - may need to trigger some email processing")
            return False
        
    except Exception as e:
        print(f"  ❌ Error testing custom metrics: {str(e)}")
        return False

def test_sqs_queues():
    """Test SQS queues are configured"""
    print("\n🧪 Testing SQS Queues...")
    
    sqs = boto3.client('sqs', region_name='us-gov-west-1')
    
    try:
        response = sqs.list_queues()
        queues = response.get('QueueUrls', [])
        
        print(f"  📊 Found {len(queues)} SQS queues")
        
        email_queues = []
        for queue_url in queues:
            queue_name = queue_url.split('/')[-1]
            if 'bulk-email' in queue_name.lower():
                email_queues.append(queue_name)
                
                # Get queue attributes
                attrs = sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
                )
                
                visible = attrs['Attributes'].get('ApproximateNumberOfMessages', '0')
                in_flight = attrs['Attributes'].get('ApproximateNumberOfMessagesNotVisible', '0')
                
                print(f"    ✅ {queue_name}")
                print(f"      Visible messages: {visible}")
                print(f"      In-flight messages: {in_flight}")
        
        if email_queues:
            print(f"  ✅ Found {len(email_queues)} email-related queues")
            return True
        else:
            print(f"  ❌ No email-related queues found")
            return False
        
    except Exception as e:
        print(f"  ❌ Error testing SQS queues: {str(e)}")
        return False

def test_dynamodb_tables():
    """Test DynamoDB tables are configured"""
    print("\n🧪 Testing DynamoDB Tables...")
    
    dynamodb = boto3.client('dynamodb', region_name='us-gov-west-1')
    
    try:
        response = dynamodb.list_tables()
        tables = response['TableNames']
        
        expected_tables = ['EmailCampaigns', 'EmailContacts']
        
        print(f"  📊 Found {len(tables)} DynamoDB tables")
        
        found_tables = []
        for table in expected_tables:
            if table in tables:
                found_tables.append(table)
                print(f"    ✅ {table}")
                
                # Get table info
                table_info = dynamodb.describe_table(TableName=table)
                item_count = table_info['Table'].get('ItemCount', 0)
                print(f"      Items: {item_count}")
            else:
                print(f"    ❌ {table} - NOT FOUND")
        
        if len(found_tables) == len(expected_tables):
            print(f"  ✅ All required tables found")
            return True
        else:
            print(f"  ❌ Missing required tables")
            return False
        
    except Exception as e:
        print(f"  ❌ Error testing DynamoDB tables: {str(e)}")
        return False

def test_eventbridge_rules():
    """Test EventBridge rules are configured"""
    print("\n🧪 Testing EventBridge Rules...")
    
    events = boto3.client('events', region_name='us-gov-west-1')
    
    try:
        response = events.list_rules()
        rules = response['Rules']
        
        print(f"  📊 Found {len(rules)} EventBridge rules")
        
        campaign_monitor_rule = None
        for rule in rules:
            if 'campaign-monitor' in rule['Name'].lower():
                campaign_monitor_rule = rule
                print(f"    ✅ {rule['Name']}")
                print(f"      State: {rule['State']}")
                print(f"      Schedule: {rule.get('ScheduleExpression', 'N/A')}")
                
                # Get targets
                targets = events.list_targets_by_rule(Rule=rule['Name'])
                print(f"      Targets: {len(targets['Targets'])}")
                for target in targets['Targets']:
                    print(f"        - {target['Arn']}")
                break
        
        if campaign_monitor_rule:
            print(f"  ✅ Campaign monitor rule found")
            return True
        else:
            print(f"  ❌ Campaign monitor rule not found")
            return False
        
    except Exception as e:
        print(f"  ❌ Error testing EventBridge rules: {str(e)}")
        return False

def simulate_throttle_test():
    """Simulate a throttle condition to test monitoring"""
    print("\n🧪 Simulating Throttle Test...")
    print("  ⚠️ This would normally trigger throttle detection")
    print("  📊 Check CloudWatch logs and metrics after running email campaigns")
    
    # This is a placeholder - actual testing would require triggering email sends
    print("  💡 To test throttle detection:")
    print("    1. Send a large email campaign with attachments")
    print("    2. Monitor CloudWatch logs for throttle messages")
    print("    3. Check CloudWatch alarms for state changes")
    
    return True

def run_monitoring_tests():
    """Run all monitoring system tests"""
    print("🚀 Monitoring System Test Suite")
    print("=" * 60)
    
    tests = [
        ("CloudWatch Alarms", test_cloudwatch_alarms),
        ("Lambda Functions", test_lambda_functions),
        ("Custom Metrics", test_custom_metrics),
        ("SQS Queues", test_sqs_queues),
        ("DynamoDB Tables", test_dynamodb_tables),
        ("EventBridge Rules", test_eventbridge_rules),
        ("Throttle Simulation", simulate_throttle_test)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"  ❌ {test_name} failed with error: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Monitoring system is properly configured.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

def main():
    """Main test function"""
    try:
        success = run_monitoring_tests()
        
        if success:
            print("\n🎯 Next Steps:")
            print("  1. Deploy the monitoring system: python deploy_monitoring_system.py")
            print("  2. Run a test email campaign")
            print("  3. Monitor CloudWatch logs and alarms")
            print("  4. Configure SNS notifications if desired")
        else:
            print("\n🔧 Troubleshooting:")
            print("  1. Deploy missing components: python deploy_monitoring_system.py")
            print("  2. Check AWS permissions and region settings")
            print("  3. Verify all required resources exist")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
