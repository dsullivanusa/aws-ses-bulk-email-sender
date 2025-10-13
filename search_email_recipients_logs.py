#!/usr/bin/env python3
"""
Search CloudWatch Logs for email recipient addresses (To, CC, BCC)
Finds the print statements with 📧✉️ *** pattern from email_worker_lambda
"""

import boto3
import json
from datetime import datetime, timedelta
import argparse
import sys


def search_email_recipient_logs(
    log_group_name="/aws/lambda/email_worker_lambda",
    hours_back=24,
    filter_pattern=None,
    limit=100,
    region="us-gov-west-1"
):
    """
    Search CloudWatch logs for email recipient information
    
    Args:
        log_group_name: CloudWatch log group name
        hours_back: How many hours back to search
        filter_pattern: Optional filter pattern (default searches for emoji pattern)
        limit: Maximum number of results to return
        region: AWS region
    """
    try:
        # Create CloudWatch Logs client
        logs_client = boto3.client('logs', region_name=region)
        
        # Calculate time range (CloudWatch uses milliseconds since epoch)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        print(f"🔍 Searching CloudWatch Logs")
        print(f"📊 Log Group: {log_group_name}")
        print(f"⏰ Time Range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 Region: {region}")
        print("=" * 100)
        
        # Use filter pattern to find our email recipient lines
        if filter_pattern is None:
            # Search for our print statement pattern
            filter_pattern = "*** To:"
        
        print(f"🔎 Filter Pattern: '{filter_pattern}'")
        print("=" * 100)
        print()
        
        # Search logs
        results = []
        next_token = None
        total_scanned = 0
        
        while len(results) < limit:
            kwargs = {
                'logGroupName': log_group_name,
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'filterPattern': filter_pattern,
                'limit': min(100, limit - len(results))
            }
            
            if next_token:
                kwargs['nextToken'] = next_token
            
            try:
                response = logs_client.filter_log_events(**kwargs)
            except logs_client.exceptions.ResourceNotFoundException:
                print(f"❌ Error: Log group '{log_group_name}' not found")
                print(f"   Make sure the Lambda function name is correct and logs exist")
                return []
            
            events = response.get('events', [])
            total_scanned += len(events)
            
            for event in events:
                results.append(event)
            
            next_token = response.get('nextToken')
            
            if not next_token:
                break
            
            # Safety check to avoid infinite loops
            if total_scanned > limit * 10:
                break
        
        print(f"📧 Found {len(results)} email recipient log entries")
        print("=" * 100)
        print()
        
        # Display results
        if results:
            for idx, event in enumerate(results[:limit], 1):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message']
                log_stream = event.get('logStreamName', 'unknown')
                
                print(f"🕐 [{idx}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Log Stream: {log_stream}")
                
                # Parse and highlight the recipient information
                if "*** To:" in message:
                    # Extract the line with recipient info
                    for line in message.split('\n'):
                        if "*** To:" in line:
                            print(f"   {line.strip()}")
                            break
                else:
                    print(f"   {message.strip()}")
                
                print()
        else:
            print("ℹ️  No matching log entries found")
            print()
            print("💡 Possible reasons:")
            print("   - No emails have been sent in the time range")
            print("   - The log group name is incorrect")
            print("   - The Lambda function hasn't been deployed with the new code")
            print("   - The time range is too narrow")
        
        return results
        
    except Exception as e:
        print(f"❌ Error searching logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def export_to_json(results, filename="email_recipients.json"):
    """Export results to JSON file"""
    try:
        export_data = []
        for event in results:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message']
            
            # Try to extract recipient info
            to_addresses = []
            cc_addresses = []
            bcc_addresses = []
            
            if "*** To:" in message:
                for line in message.split('\n'):
                    if "*** To:" in line:
                        # Parse the line to extract addresses
                        # Format: 📧✉️ *** To: [email], CC: [list], BCC: [list]
                        try:
                            if "To:" in line:
                                to_part = line.split("To:")[1].split("CC:")[0].strip()
                                to_addresses = to_part
                            if "CC:" in line:
                                cc_part = line.split("CC:")[1].split("BCC:")[0].strip()
                                cc_addresses = cc_part
                            if "BCC:" in line:
                                bcc_part = line.split("BCC:")[1].strip()
                                bcc_addresses = bcc_part
                        except:
                            pass
                        break
            
            export_data.append({
                'timestamp': timestamp.isoformat(),
                'log_stream': event.get('logStreamName', 'unknown'),
                'to': to_addresses,
                'cc': cc_addresses,
                'bcc': bcc_addresses,
                'full_message': message
            })
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Exported {len(export_data)} results to {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error exporting to JSON: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Search CloudWatch Logs for email recipient addresses (To, CC, BCC)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search last 24 hours (default)
  python search_email_recipients_logs.py
  
  # Search last 6 hours
  python search_email_recipients_logs.py --hours 6
  
  # Search specific log group
  python search_email_recipients_logs.py --log-group /aws/lambda/my-email-worker
  
  # Get more results
  python search_email_recipients_logs.py --limit 500
  
  # Export to JSON
  python search_email_recipients_logs.py --export recipients.json
  
  # Different region
  python search_email_recipients_logs.py --region us-east-1
        """
    )
    
    parser.add_argument(
        '--log-group',
        default='/aws/lambda/email_worker_lambda',
        help='CloudWatch log group name (default: /aws/lambda/email_worker_lambda)'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Hours back to search (default: 24)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum number of results (default: 100)'
    )
    parser.add_argument(
        '--region',
        default='us-gov-west-1',
        help='AWS region (default: us-gov-west-1)'
    )
    parser.add_argument(
        '--filter',
        help='Custom filter pattern (default: "*** To:")'
    )
    parser.add_argument(
        '--export',
        help='Export results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Search logs
    results = search_email_recipient_logs(
        log_group_name=args.log_group,
        hours_back=args.hours,
        filter_pattern=args.filter,
        limit=args.limit,
        region=args.region
    )
    
    # Export if requested
    if args.export and results:
        export_to_json(results, args.export)
    
    print("=" * 100)
    print(f"✅ Search complete - Found {len(results)} entries")


if __name__ == "__main__":
    main()

