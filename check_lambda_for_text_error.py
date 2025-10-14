#!/usr/bin/env python3
"""
Check Lambda logs for 'text' related errors
"""

import boto3
import json
from datetime import datetime, timedelta

def search_lambda_logs(function_name='bulk_email_api_lambda', hours_back=1):
    """Search CloudWatch logs for text-related errors"""
    
    logs_client = boto3.client('logs', region_name='us-gov-west-1')
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)
    
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    log_group = f'/aws/lambda/{function_name}'
    
    print(f"🔍 Searching logs for: {log_group}")
    print(f"⏰ Time range: {start_time} to {end_time}")
    print("=" * 80)
    
    try:
        # Search for 'text' errors
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_ms,
            endTime=end_ms,
            filterPattern='text'
        )
        
        events = response.get('events', [])
        
        if events:
            print(f"📋 Found {len(events)} log entries with 'text':\n")
            for event in events[-10:]:  # Last 10 entries
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message']
                print(f"🕐 {timestamp}")
                print(f"   {message}")
                print()
        else:
            print("✅ No 'text' related errors found")
            
        # Also search for NameError
        print("\n" + "=" * 80)
        print("🔍 Searching for NameError...")
        print("=" * 80 + "\n")
        
        response2 = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_ms,
            endTime=end_ms,
            filterPattern='NameError'
        )
        
        events2 = response2.get('events', [])
        
        if events2:
            print(f"📋 Found {len(events2)} NameError entries:\n")
            for event in events2:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message']
                print(f"🕐 {timestamp}")
                print(f"   {message}")
                print()
        else:
            print("✅ No NameError found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    function_name = sys.argv[1] if len(sys.argv) > 1 else 'bulk_email_api_lambda'
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    search_lambda_logs(function_name, hours)

