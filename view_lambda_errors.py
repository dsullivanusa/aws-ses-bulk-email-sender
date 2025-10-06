#!/usr/bin/env python3
"""
View Lambda Function Errors and Exceptions
Fetches CloudWatch logs for Lambda functions and highlights errors/exceptions
"""

import boto3
import json
from datetime import datetime, timedelta
import sys
import re
from collections import defaultdict

def list_lambda_functions():
    """List all Lambda functions"""
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.list_functions()
        functions = response['Functions']
        
        print("\n📋 Available Lambda Functions:")
        print("=" * 80)
        for idx, func in enumerate(functions, 1):
            print(f"{idx}. {func['FunctionName']}")
            print(f"   Runtime: {func['Runtime']} | Last Modified: {func['LastModified']}")
        
        return [f['FunctionName'] for f in functions]
    
    except Exception as e:
        print(f"❌ Error listing Lambda functions: {str(e)}")
        return []

def get_log_events(log_group_name, hours=1, filter_pattern=''):
    """Fetch log events from CloudWatch Logs"""
    logs_client = boto3.client('logs')
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    print(f"\n🔍 Fetching logs from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    events = []
    
    try:
        # Get all log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=50  # Get latest 50 streams
        )
        
        log_streams = streams_response.get('logStreams', [])
        
        if not log_streams:
            print(f"⚠️  No log streams found for {log_group_name}")
            return events
        
        print(f"📊 Found {len(log_streams)} log streams")
        
        # Fetch events from each stream
        for stream in log_streams:
            stream_name = stream['logStreamName']
            
            try:
                if filter_pattern:
                    # Use filter pattern for more efficient querying
                    events_response = logs_client.filter_log_events(
                        logGroupName=log_group_name,
                        logStreamNames=[stream_name],
                        startTime=start_timestamp,
                        endTime=end_timestamp,
                        filterPattern=filter_pattern
                    )
                else:
                    events_response = logs_client.filter_log_events(
                        logGroupName=log_group_name,
                        logStreamNames=[stream_name],
                        startTime=start_timestamp,
                        endTime=end_timestamp
                    )
                
                events.extend(events_response.get('events', []))
                
            except Exception as e:
                print(f"⚠️  Error fetching stream {stream_name}: {str(e)}")
                continue
        
        # Sort by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"❌ Log group not found: {log_group_name}")
        print(f"💡 Make sure the Lambda function has been invoked at least once.")
        return []
    except Exception as e:
        print(f"❌ Error fetching logs: {str(e)}")
        return []

def analyze_errors(events):
    """Analyze events and categorize errors"""
    errors = []
    exceptions = []
    warnings = []
    timeouts = []
    memory_errors = []
    
    error_patterns = {
        'error': r'(?i)(error|failed|failure)',
        'exception': r'(?i)(exception|traceback)',
        'warning': r'(?i)(warning|warn)',
        'timeout': r'(?i)(timeout|timed out)',
        'memory': r'(?i)(memory|out of memory|oom)'
    }
    
    for event in events:
        message = event['message']
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        
        # Check for different error types
        if re.search(error_patterns['exception'], message):
            exceptions.append({'timestamp': timestamp, 'message': message})
        elif re.search(error_patterns['timeout'], message):
            timeouts.append({'timestamp': timestamp, 'message': message})
        elif re.search(error_patterns['memory'], message):
            memory_errors.append({'timestamp': timestamp, 'message': message})
        elif re.search(error_patterns['error'], message):
            errors.append({'timestamp': timestamp, 'message': message})
        elif re.search(error_patterns['warning'], message):
            warnings.append({'timestamp': timestamp, 'message': message})
    
    return {
        'errors': errors,
        'exceptions': exceptions,
        'warnings': warnings,
        'timeouts': timeouts,
        'memory_errors': memory_errors
    }

def print_error_summary(analysis):
    """Print summary of errors found"""
    print("\n" + "=" * 80)
    print("📊 ERROR SUMMARY")
    print("=" * 80)
    
    print(f"🔴 Exceptions: {len(analysis['exceptions'])}")
    print(f"🟠 Errors: {len(analysis['errors'])}")
    print(f"🟡 Warnings: {len(analysis['warnings'])}")
    print(f"⏱️  Timeouts: {len(analysis['timeouts'])}")
    print(f"💾 Memory Errors: {len(analysis['memory_errors'])}")
    
    total_issues = sum(len(v) for v in analysis.values())
    print(f"\n📈 Total Issues Found: {total_issues}")

def print_detailed_errors(analysis, show_all=False):
    """Print detailed error messages"""
    
    # Print exceptions (most critical)
    if analysis['exceptions']:
        print("\n" + "=" * 80)
        print("🔴 EXCEPTIONS")
        print("=" * 80)
        for idx, exc in enumerate(analysis['exceptions'][:20 if not show_all else None], 1):
            print(f"\n[{idx}] {exc['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
            print(exc['message'])
    
    # Print timeouts
    if analysis['timeouts']:
        print("\n" + "=" * 80)
        print("⏱️  TIMEOUTS")
        print("=" * 80)
        for idx, timeout in enumerate(analysis['timeouts'][:10 if not show_all else None], 1):
            print(f"\n[{idx}] {timeout['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
            print(timeout['message'])
    
    # Print memory errors
    if analysis['memory_errors']:
        print("\n" + "=" * 80)
        print("💾 MEMORY ERRORS")
        print("=" * 80)
        for idx, mem in enumerate(analysis['memory_errors'][:10 if not show_all else None], 1):
            print(f"\n[{idx}] {mem['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
            print(mem['message'])
    
    # Print general errors
    if analysis['errors']:
        print("\n" + "=" * 80)
        print("🟠 ERRORS")
        print("=" * 80)
        for idx, err in enumerate(analysis['errors'][:10 if not show_all else None], 1):
            print(f"\n[{idx}] {err['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
            print(err['message'])
    
    # Print warnings
    if analysis['warnings']:
        print("\n" + "=" * 80)
        print("🟡 WARNINGS")
        print("=" * 80)
        for idx, warn in enumerate(analysis['warnings'][:5 if not show_all else None], 1):
            print(f"\n[{idx}] {warn['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
            print(warn['message'])

def main():
    """Main function"""
    print("=" * 80)
    print("🔍 Lambda Function Error Viewer")
    print("=" * 80)
    
    # Get command line arguments
    function_name = None
    hours = 1
    show_all = False
    
    if len(sys.argv) > 1:
        function_name = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            hours = int(sys.argv[2])
        except ValueError:
            print("⚠️  Invalid hours value, using default (1 hour)")
    if len(sys.argv) > 3 and sys.argv[3] == '--all':
        show_all = True
    
    # List functions if not specified
    if not function_name:
        functions = list_lambda_functions()
        
        if not functions:
            print("❌ No Lambda functions found")
            return
        
        print(f"\n📝 Enter function number (1-{len(functions)}) or name:")
        user_input = input("> ").strip()
        
        try:
            # Try as number first
            idx = int(user_input) - 1
            if 0 <= idx < len(functions):
                function_name = functions[idx]
            else:
                print("❌ Invalid number")
                return
        except ValueError:
            # Use as function name
            function_name = user_input
    
    print(f"\n🎯 Selected Lambda: {function_name}")
    
    # Log group name for Lambda is /aws/lambda/<function-name>
    log_group_name = f"/aws/lambda/{function_name}"
    
    # Fetch logs
    print(f"⏰ Time range: Last {hours} hour(s)")
    events = get_log_events(log_group_name, hours=hours)
    
    if not events:
        print(f"\n✅ No log events found in the last {hours} hour(s)")
        print("💡 Try increasing the time range with: python view_lambda_errors.py <function-name> <hours>")
        return
    
    print(f"\n📦 Total log events: {len(events)}")
    
    # Analyze errors
    analysis = analyze_errors(events)
    
    # Print summary
    print_error_summary(analysis)
    
    # Print detailed errors
    print_detailed_errors(analysis, show_all=show_all)
    
    # Save to file option
    total_issues = sum(len(v) for v in analysis.values())
    if total_issues > 0:
        print("\n" + "=" * 80)
        print("💾 Save detailed logs to file? (y/n)")
        save = input("> ").strip().lower()
        
        if save == 'y':
            filename = f"lambda_errors_{function_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Lambda Error Report: {function_name}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Time Range: Last {hours} hour(s)\n")
                f.write("=" * 80 + "\n\n")
                
                # Write all errors
                for category, items in analysis.items():
                    if items:
                        f.write(f"\n{category.upper()}\n")
                        f.write("=" * 80 + "\n")
                        for item in items:
                            f.write(f"\n[{item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}]\n")
                            f.write(item['message'] + "\n")
            
            print(f"✅ Saved to {filename}")
    
    print("\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("\n💡 Usage: python view_lambda_errors.py [function-name] [hours] [--all]")
    print("   Example: python view_lambda_errors.py BulkEmailAPI 24 --all")

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

