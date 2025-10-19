#!/usr/bin/env python3
"""
Diagnose EmailWorker CloudWatch Alarms
Find what events are triggering the EmailWorker-FunctionErrors alarm
"""

import boto3
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def find_emailworker_alarms():
    """Find all EmailWorker related alarms"""
    print("=" * 80)
    print("Finding EmailWorker CloudWatch Alarms...")
    print("=" * 80)
    
    cw = boto3.client('cloudwatch')
    
    # Get alarms with EmailWorker in the name
    response = cw.describe_alarms(AlarmNamePrefix='EmailWorker')
    alarms = response.get('MetricAlarms', [])
    
    if not alarms:
        print("No EmailWorker alarms found. Searching all alarms...")
        response = cw.describe_alarms()
        alarms = [a for a in response.get('MetricAlarms', []) if 'emailworker' in a['AlarmName'].lower()]
    
    if not alarms:
        print("ERROR: No EmailWorker alarms found in CloudWatch")
        return None
    
    print(f"\nFound {len(alarms)} EmailWorker alarm(s):")
    for alarm in alarms:
        state_icon = "ALARM" if alarm['StateValue'] == 'ALARM' else "OK"
        print(f"\n  [{state_icon}] {alarm['AlarmName']}")
        print(f"      Namespace: {alarm.get('Namespace', 'N/A')}")
        print(f"      Metric: {alarm['MetricName']}")
        print(f"      State: {alarm['StateValue']}")
        print(f"      Reason: {alarm.get('StateReason', 'N/A')}")
        
        # Show ALL dimensions
        dimensions = alarm.get('Dimensions', [])
        if dimensions:
            print(f"      Dimensions:")
            for dim in dimensions:
                print(f"        - {dim['Name']}: {dim['Value']}")
                if dim['Name'] == 'FunctionName':
                    print(f"      --> Lambda Function Found: {dim['Value']}")
        else:
            print(f"      Dimensions: None (This might be a composite alarm)")
    
    return alarms


def get_lambda_function_name(alarm):
    """Extract Lambda function name from alarm dimensions"""
    for dim in alarm.get('Dimensions', []):
        if dim['Name'] == 'FunctionName':
            return dim['Value']
    return None


def get_lambda_errors(function_name, hours=24):
    """Get error logs from Lambda function"""
    print("\n" + "=" * 80)
    print(f"Fetching CloudWatch Logs for: {function_name}")
    print(f"Time Range: Last {hours} hours")
    print("=" * 80)
    
    logs_client = boto3.client('logs')
    log_group_name = f"/aws/lambda/{function_name}"
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    print(f"From: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"To:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Query for error events
        all_events = []
        next_token = None
        
        while True:
            kwargs = {
                'logGroupName': log_group_name,
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'filterPattern': '?ERROR ?Exception ?error ?Traceback ?failed',
            }
            
            if next_token:
                kwargs['nextToken'] = next_token
            
            response = logs_client.filter_log_events(**kwargs)
            events = response.get('events', [])
            all_events.extend(events)
            
            next_token = response.get('nextToken')
            if not next_token or len(all_events) > 500:  # Limit to 500 events
                break
        
        print(f"\nFound {len(all_events)} error-related log events")
        return all_events
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"ERROR: Log group not found: {log_group_name}")
        print("This means the Lambda function either doesn't exist or hasn't been invoked yet.")
        return []
    except Exception as e:
        print(f"ERROR fetching logs: {str(e)}")
        return []


def analyze_errors(events):
    """Analyze and categorize errors"""
    print("\n" + "=" * 80)
    print("Analyzing Errors...")
    print("=" * 80)
    
    error_categories = defaultdict(list)
    error_types = defaultdict(int)
    
    for event in events:
        message = event['message']
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        
        # Categorize by error type
        if 'KeyError' in message:
            category = 'KeyError'
        elif 'AttributeError' in message:
            category = 'AttributeError'
        elif 'TypeError' in message:
            category = 'TypeError'
        elif 'ValueError' in message:
            category = 'ValueError'
        elif 'Exception' in message:
            category = 'General Exception'
        elif 'Timeout' in message or 'timed out' in message:
            category = 'Timeout'
        elif 'Memory' in message or 'MemoryError' in message:
            category = 'Memory Error'
        elif 'ERROR' in message.upper():
            category = 'General Error'
        else:
            category = 'Other'
        
        error_categories[category].append({
            'timestamp': timestamp,
            'message': message
        })
        error_types[category] += 1
    
    return error_categories, error_types


def print_error_summary(error_categories, error_types):
    """Print summary of errors"""
    print("\n" + "=" * 80)
    print("ERROR SUMMARY")
    print("=" * 80)
    
    total_errors = sum(error_types.values())
    print(f"\nTotal Errors: {total_errors}\n")
    
    # Sort by count
    sorted_types = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
    
    for error_type, count in sorted_types:
        percentage = (count / total_errors * 100) if total_errors > 0 else 0
        print(f"  {error_type:25s}: {count:4d} ({percentage:5.1f}%)")
    
    print("\n" + "=" * 80)
    print("DETAILED ERROR SAMPLES (Most Recent)")
    print("=" * 80)
    
    for error_type, errors in error_categories.items():
        if errors:
            print(f"\n--- {error_type} ---")
            # Show up to 3 most recent examples
            recent_errors = sorted(errors, key=lambda x: x['timestamp'], reverse=True)[:3]
            
            for idx, error in enumerate(recent_errors, 1):
                print(f"\n  Example {idx} - {error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show first 5 lines of the error message
                lines = error['message'].split('\n')[:5]
                for line in lines:
                    if line.strip():
                        print(f"    {line}")
                
                if len(error['message'].split('\n')) > 5:
                    print(f"    ... (truncated)")


def get_lambda_metrics(function_name, hours=24):
    """Get Lambda function metrics from CloudWatch"""
    print("\n" + "=" * 80)
    print(f"Lambda Metrics for: {function_name}")
    print("=" * 80)
    
    cw = boto3.client('cloudwatch')
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    metrics_to_check = ['Errors', 'Invocations', 'Throttles', 'Duration', 'ConcurrentExecutions']
    
    for metric_name in metrics_to_check:
        try:
            response = cw.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'FunctionName',
                        'Value': function_name
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Sum', 'Average', 'Maximum']
            )
            
            datapoints = response.get('Datapoints', [])
            if datapoints:
                datapoints.sort(key=lambda x: x['Timestamp'])
                
                # Calculate totals
                if 'Sum' in datapoints[0]:
                    total = sum(d.get('Sum', 0) for d in datapoints)
                    avg = sum(d.get('Average', 0) for d in datapoints) / len(datapoints)
                    max_val = max(d.get('Maximum', 0) for d in datapoints)
                    
                    print(f"\n{metric_name}:")
                    print(f"  Total: {total:.0f}")
                    print(f"  Average: {avg:.2f}")
                    print(f"  Maximum: {max_val:.0f}")
                    
        except Exception as e:
            print(f"  Could not fetch {metric_name}: {str(e)}")


def main():
    """Main function"""
    print("=" * 80)
    print("EmailWorker CloudWatch Alarm Diagnostics")
    print("=" * 80)
    print()
    
    # Get hours from command line or use default
    hours = 24
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print(f"Invalid hours value '{sys.argv[1]}', using default (24 hours)")
    
    # Step 1: Find EmailWorker alarms
    alarms = find_emailworker_alarms()
    
    if not alarms:
        print("\nNo alarms found. Please check:")
        print("  1. Alarm name contains 'EmailWorker'")
        print("  2. You're connected to the correct AWS account/region")
        return
    
    # Step 2: Get the Lambda function name from alarm
    function_name = None
    for alarm in alarms:
        if 'FunctionErrors' in alarm['AlarmName']:
            function_name = get_lambda_function_name(alarm)
            if function_name:
                break
    
    # Allow manual function name override
    if len(sys.argv) > 2:
        function_name = sys.argv[2]
        print(f"\nUsing manually specified function name: {function_name}")
    
    if not function_name:
        print("\nERROR: Could not find Lambda function name in alarm dimensions")
        print("\nLet me list your Lambda functions to help you find the right one...")
        
        try:
            lambda_client = boto3.client('lambda')
            response = lambda_client.list_functions()
            functions = response.get('Functions', [])
            
            if functions:
                print("\nAvailable Lambda Functions:")
                print("-" * 80)
                for idx, func in enumerate(functions, 1):
                    print(f"  {idx}. {func['FunctionName']}")
                    print(f"     Runtime: {func['Runtime']} | Memory: {func['MemorySize']}MB")
                    print(f"     Last Modified: {func['LastModified']}")
                    print()
                
                print("\nPlease run the script again with the function name:")
                print(f"  python diagnose_emailworker_errors.py {hours} <function-name>")
                print("\nExample:")
                print(f"  python diagnose_emailworker_errors.py {hours} {functions[0]['FunctionName']}")
            else:
                print("\nNo Lambda functions found in this account/region")
                print("Please verify you're connected to the correct AWS account and region")
        except Exception as e:
            print(f"\nCouldn't list Lambda functions: {str(e)}")
            print("\nPlease specify the function name manually:")
            print(f"  python diagnose_emailworker_errors.py {hours} <function-name>")
        
        return
    
    # Step 3: Get Lambda error logs
    events = get_lambda_errors(function_name, hours)
    
    if not events:
        print("\nNo error events found in the specified time range.")
        print("The alarms might be:")
        print("  1. False positives")
        print("  2. Already resolved")
        print("  3. Occurring outside the time range")
        print(f"\nTry increasing the time range: python diagnose_emailworker_errors.py {hours*2}")
        return
    
    # Step 4: Analyze errors
    error_categories, error_types = analyze_errors(events)
    
    # Step 5: Print summary
    print_error_summary(error_categories, error_types)
    
    # Step 6: Get CloudWatch metrics
    get_lambda_metrics(function_name, hours)
    
    # Step 7: Save to file
    print("\n" + "=" * 80)
    filename = f"emailworker_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("EmailWorker Error Analysis Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Function: {function_name}\n")
        f.write(f"Time Range: Last {hours} hours\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total Errors: {sum(error_types.values())}\n\n")
        
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{error_type}: {count}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED ERRORS\n")
        f.write("=" * 80 + "\n\n")
        
        for error_type, errors in error_categories.items():
            f.write(f"\n--- {error_type} ({len(errors)} occurrences) ---\n\n")
            
            # Sort by timestamp
            sorted_errors = sorted(errors, key=lambda x: x['timestamp'], reverse=True)
            
            for idx, error in enumerate(sorted_errors[:10], 1):  # Save up to 10 examples
                f.write(f"[{error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(error['message'] + "\n")
                f.write("-" * 80 + "\n\n")
    
    print(f"Report saved to: {filename}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("To fix the errors:")
    print("  1. Review the error details above")
    print("  2. Check the Lambda function code for the reported issues")
    print("  3. Look at the most common error types first")
    print("  4. Check recent code deployments that might have introduced issues")
    print()
    print("To view real-time logs:")
    print(f"  python tail_lambda_logs.py {function_name}")
    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

