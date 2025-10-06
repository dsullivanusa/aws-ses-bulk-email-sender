#!/usr/bin/env python3
"""
Tail Lambda Function Logs in Real-Time
Similar to 'tail -f' for Lambda CloudWatch logs
"""

import boto3
import time
from datetime import datetime
import sys

def tail_logs(function_name, follow=True):
    """Tail Lambda function logs"""
    logs_client = boto3.client('logs')
    log_group_name = f"/aws/lambda/{function_name}"
    
    print(f"🔍 Tailing logs for: {function_name}")
    print(f"📋 Log group: {log_group_name}")
    print("=" * 80)
    
    last_timestamp = int((datetime.now().timestamp() - 60) * 1000)  # Start from 1 minute ago
    seen_event_ids = set()
    
    try:
        while True:
            try:
                # Get latest log streams
                streams_response = logs_client.describe_log_streams(
                    logGroupName=log_group_name,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=5
                )
                
                log_streams = streams_response.get('logStreams', [])
                
                if not log_streams:
                    if not follow:
                        print("⚠️  No log streams found")
                        break
                    time.sleep(2)
                    continue
                
                # Fetch events from latest streams
                for stream in log_streams:
                    stream_name = stream['logStreamName']
                    
                    try:
                        events_response = logs_client.get_log_events(
                            logGroupName=log_group_name,
                            logStreamName=stream_name,
                            startTime=last_timestamp,
                            startFromHead=True
                        )
                        
                        events = events_response.get('events', [])
                        
                        for event in events:
                            event_id = f"{event['timestamp']}_{event['message'][:50]}"
                            
                            if event_id not in seen_event_ids:
                                seen_event_ids.add(event_id)
                                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                                
                                # Color code based on content
                                message = event['message'].strip()
                                
                                if 'ERROR' in message.upper() or 'EXCEPTION' in message.upper():
                                    prefix = "🔴"
                                elif 'WARNING' in message.upper() or 'WARN' in message.upper():
                                    prefix = "🟡"
                                elif 'START RequestId' in message:
                                    prefix = "🚀"
                                elif 'END RequestId' in message:
                                    prefix = "✅"
                                elif 'REPORT RequestId' in message:
                                    prefix = "📊"
                                else:
                                    prefix = "📝"
                                
                                print(f"{prefix} [{timestamp.strftime('%H:%M:%S')}] {message}")
                                
                                # Update last timestamp
                                if event['timestamp'] > last_timestamp:
                                    last_timestamp = event['timestamp']
                    
                    except Exception as e:
                        if 'ResourceNotFoundException' not in str(e):
                            print(f"⚠️  Error reading stream: {str(e)}")
                
            except logs_client.exceptions.ResourceNotFoundException:
                print(f"❌ Log group not found: {log_group_name}")
                print("💡 Make sure the Lambda function has been invoked at least once")
                break
            except Exception as e:
                print(f"⚠️  Error: {str(e)}")
                if not follow:
                    break
            
            if not follow:
                break
            
            time.sleep(2)  # Poll every 2 seconds
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped tailing logs")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python tail_lambda_logs.py <function-name> [--no-follow]")
        print("\nExamples:")
        print("  python tail_lambda_logs.py BulkEmailAPI")
        print("  python tail_lambda_logs.py EmailWorker --no-follow")
        return
    
    function_name = sys.argv[1]
    follow = '--no-follow' not in sys.argv
    
    tail_logs(function_name, follow=follow)

if __name__ == "__main__":
    main()

