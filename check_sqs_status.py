#!/usr/bin/env python3
"""
Check SQS Queue Status
Shows real-time status of messages in queue
"""

import boto3
import time
from datetime import datetime

def check_queue_status():
    sqs = boto3.client('sqs', region_name='us-gov-west-1')
    queue_name = 'bulk-email-queue'
    
    print("=" * 80)
    print("🔍 SQS Queue Status Monitor")
    print("=" * 80)
    
    try:
        # Get queue URL
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        print(f"\n📨 Queue: {queue_name}")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 80)
        
        # Get queue attributes
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                'ApproximateNumberOfMessages',
                'ApproximateNumberOfMessagesNotVisible',
                'ApproximateNumberOfMessagesDelayed'
            ]
        )
        
        queue_attrs = attrs['Attributes']
        available = int(queue_attrs.get('ApproximateNumberOfMessages', 0))
        in_flight = int(queue_attrs.get('ApproximateNumberOfMessagesNotVisible', 0))
        delayed = int(queue_attrs.get('ApproximateNumberOfMessagesDelayed', 0))
        total = available + in_flight + delayed
        
        # Display status
        print(f"\n📊 Message Status:")
        print(f"   📬 Available (waiting): {available}")
        print(f"   ✈️  In Flight (processing): {in_flight}")
        print(f"   ⏳ Delayed: {delayed}")
        print(f"   📮 Total: {total}")
        
        # Analysis
        print(f"\n🔍 Analysis:")
        if in_flight > 0:
            print(f"   ⚙️  {in_flight} message(s) currently being processed by Lambda")
            print(f"   ⏱️  Expected completion: 1-60 seconds")
            print(f"   💡 If stuck for 5+ minutes, check Lambda logs")
        
        if available > 0:
            print(f"   📬 {available} message(s) waiting to be processed")
            print(f"   ⚙️  Lambda should pick these up automatically")
        
        if total == 0:
            print(f"   ✅ Queue is empty - all messages processed!")
        
        # Monitoring suggestion
        if in_flight > 0 or available > 0:
            print(f"\n💡 Monitor Progress:")
            print(f"   Run this script again in 30 seconds to see if 'In Flight' decreases")
            print(f"   Or watch logs: python tail_lambda_logs.py email-worker-function")
        
        print("\n" + "=" * 80)
        
        return {
            'available': available,
            'in_flight': in_flight,
            'delayed': delayed,
            'total': total
        }
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return None

def monitor_queue(duration_seconds=60, interval=5):
    """Monitor queue status over time"""
    
    print(f"📡 Monitoring queue for {duration_seconds} seconds (checking every {interval}s)")
    print(f"Press Ctrl+C to stop\n")
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration_seconds:
            status = check_queue_status()
            
            if status and status['total'] == 0:
                print("\n✅ All messages processed! Queue is empty.")
                break
            
            if status and status['in_flight'] == 0 and status['available'] == 0:
                print("\n✅ Processing complete!")
                break
            
            time.sleep(interval)
            print("\n" + "🔄 Refreshing..." + "\n")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--monitor':
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        monitor_queue(duration)
    else:
        check_queue_status()
        print("\n💡 To continuously monitor: python check_sqs_status.py --monitor 120")

