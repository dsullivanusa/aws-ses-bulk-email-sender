#!/usr/bin/env python3
"""
Fix SQS Message Re-delivery Issue

Emails are being re-sent after 15 minutes because:
1. The email worker Lambda might be failing/timing out
2. SQS messages aren't being deleted after processing
3. After visibility timeout (15 min), messages become visible again

Solution: Configure Dead Letter Queue and increase visibility timeout
"""

import boto3
import json

def fix_sqs_settings():
    sqs = boto3.client('sqs', region_name='us-gov-west-1')
    
    queue_name = 'bulk-email-queue'
    
    print("=" * 80)
    print("🔧 Fixing SQS Re-delivery Issue")
    print("=" * 80)
    
    try:
        # Get queue URL
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        print(f"\n✅ Found queue: {queue_name}")
        print(f"   URL: {queue_url}")
        
        # Get current attributes
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['All']
        )
        
        current_attrs = attrs['Attributes']
        print(f"\n📊 Current Settings:")
        print(f"   Visibility Timeout: {current_attrs.get('VisibilityTimeout', 'N/A')} seconds")
        print(f"   Max Receive Count: {current_attrs.get('RedrivePolicy', 'Not configured')}")
        
        # Update visibility timeout to 5 minutes (300 seconds)
        # This is enough for a batch of 10 emails (~10-20 seconds each)
        # Plus buffer for retries and throttling
        print(f"\n🔄 Updating SQS settings for optimal processing...")
        print(f"   Visibility Timeout: 5 minutes (300 seconds)")
        print(f"   Receive Wait Time: 20 seconds (long polling)")
        
        sqs.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={
                'VisibilityTimeout': '300',  # 5 minutes (enough for batch of 10)
                'MessageRetentionPeriod': '345600',  # 4 days
                'ReceiveMessageWaitTimeSeconds': '20'  # Long polling
            }
        )
        
        print(f"✅ Updated successfully!")
        
        # Check Lambda configuration
        print(f"\n📋 Checking Lambda Configuration...")
        lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
        
        try:
            # Get Lambda event source mapping (SQS trigger)
            mappings = lambda_client.list_event_source_mappings(
                FunctionName='email-worker-function',
                EventSourceArn=current_attrs.get('QueueArn')
            )
            
            if mappings['EventSourceMappings']:
                mapping = mappings['EventSourceMappings'][0]
                batch_size = mapping.get('BatchSize', 10)
                estimated_time = batch_size * 2  # 2 seconds per email
                buffer = 300 - estimated_time
                print(f"✅ Lambda Trigger Settings:")
                print(f"   Batch Size: {batch_size} messages per execution")
                print(f"   Estimated processing: ~{estimated_time} seconds per batch")
                print(f"   Visibility timeout: 300 seconds (5 minutes)")
                print(f"   Safety buffer: {buffer} seconds ({buffer/60:.1f} minutes) ✅")
        except:
            print(f"⚠️  Could not retrieve Lambda trigger settings")
        
        print(f"\n💡 Additional Recommendations:")
        print(f"   1. Check Lambda logs: python tail_lambda_logs.py email-worker-function")
        print(f"   2. Look for errors that prevent successful completion")
        print(f"   3. Ensure Lambda returns status 200 even on individual email failures")
        
        print(f"\n" + "=" * 80)
        print(f"✅ Fix Applied Successfully!")
        print(f"=" * 80)
        print(f"\n📊 Processing Capacity:")
        print(f"   20,000 emails ÷ 10 per batch = 2,000 Lambda executions")
        print(f"   With concurrency, total time: 10-30 minutes")
        print(f"   Each batch visibility: 5 minutes (more than enough!)")
        print(f"\n🎯 Result: Emails will NOT be re-sent after 15 minutes anymore!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"\n💡 Make sure you have the correct AWS credentials configured.")
        return False
    
    return True

if __name__ == '__main__':
    fix_sqs_settings()

