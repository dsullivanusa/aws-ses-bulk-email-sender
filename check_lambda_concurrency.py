#!/usr/bin/env python3
"""
Check Lambda Concurrency and SQS Performance
Shows if you need additional fan-out or if current setup is sufficient
"""

import boto3
from datetime import datetime, timedelta

def check_concurrency():
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    sqs = boto3.client('sqs', region_name='us-gov-west-1')
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')
    
    function_name = 'email-worker-function'
    queue_name = 'bulk-email-queue'
    
    print("=" * 80)
    print("🔍 Lambda Concurrency & Fan-Out Analysis")
    print("=" * 80)
    
    # Check Lambda concurrency settings
    print("\n📊 Lambda Configuration:")
    try:
        func_config = lambda_client.get_function_configuration(FunctionName=function_name)
        
        reserved_concurrency = func_config.get('ReservedConcurrentExecutions', 'Unreserved')
        timeout = func_config.get('Timeout', 'N/A')
        memory = func_config.get('MemorySize', 'N/A')
        
        print(f"   Function: {function_name}")
        print(f"   Timeout: {timeout} seconds")
        print(f"   Memory: {memory} MB")
        print(f"   Reserved Concurrency: {reserved_concurrency}")
        
        if reserved_concurrency == 'Unreserved':
            print(f"   ✅ Using account-level concurrency (typically 1000)")
        else:
            print(f"   ⚠️  Limited to {reserved_concurrency} concurrent executions")
            
    except Exception as e:
        print(f"   ❌ Could not retrieve Lambda config: {str(e)}")
    
    # Check SQS settings
    print("\n📨 SQS Queue Configuration:")
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['All']
        )
        
        queue_attrs = attrs['Attributes']
        print(f"   Queue: {queue_name}")
        print(f"   Visibility Timeout: {queue_attrs.get('VisibilityTimeout', 'N/A')} seconds")
        print(f"   Messages Available: {queue_attrs.get('ApproximateNumberOfMessages', '0')}")
        print(f"   Messages In Flight: {queue_attrs.get('ApproximateNumberOfMessagesNotVisible', '0')}")
        print(f"   Messages Delayed: {queue_attrs.get('ApproximateNumberOfMessagesDelayed', '0')}")
        
    except Exception as e:
        print(f"   ❌ Could not retrieve SQS config: {str(e)}")
    
    # Check recent concurrency from CloudWatch
    print("\n📈 Recent Lambda Concurrency (Last Hour):")
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='ConcurrentExecutions',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,  # 5 minute intervals
            Statistics=['Maximum', 'Average']
        )
        
        if response['Datapoints']:
            datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
            max_concurrent = max([dp['Maximum'] for dp in datapoints])
            avg_concurrent = sum([dp['Average'] for dp in datapoints]) / len(datapoints)
            
            print(f"   Maximum Concurrent: {int(max_concurrent)} executions")
            print(f"   Average Concurrent: {int(avg_concurrent)} executions")
            
            # Analysis
            if max_concurrent >= 50:
                print(f"   ✅ Good fan-out! Multiple Lambdas running in parallel")
            elif max_concurrent >= 10:
                print(f"   ⚠️  Moderate concurrency. Could be faster with more parallel executions")
            else:
                print(f"   ❌ Low concurrency! May need to increase limits or fix queue")
        else:
            print(f"   ℹ️  No recent executions in the last hour")
            
    except Exception as e:
        print(f"   ⚠️  Could not retrieve metrics: {str(e)}")
    
    # Check Lambda event source mapping
    print("\n🔗 SQS → Lambda Trigger Settings:")
    try:
        mappings = lambda_client.list_event_source_mappings(
            FunctionName=function_name
        )
        
        if mappings['EventSourceMappings']:
            mapping = mappings['EventSourceMappings'][0]
            batch_size = mapping.get('BatchSize', 'N/A')
            max_batching_window = mapping.get('MaximumBatchingWindowInSeconds', 0)
            scaling_config = mapping.get('ScalingConfig', {})
            max_concurrency = scaling_config.get('MaximumConcurrency', 'No limit')
            
            print(f"   Batch Size: {batch_size} messages per Lambda execution")
            print(f"   Batching Window: {max_batching_window} seconds")
            print(f"   Maximum Concurrency: {max_concurrency}")
            
            if batch_size == 10:
                print(f"   ✅ Good batch size for email sending")
            
    except Exception as e:
        print(f"   ⚠️  Could not retrieve trigger settings: {str(e)}")
    
    # Performance calculation
    print("\n🎯 Fan-Out Performance Analysis:")
    print("=" * 80)
    
    # Estimate with different concurrency levels
    total_emails = 20000
    batch_size = 10
    time_per_batch = 20  # seconds
    
    print(f"   Scenario: {total_emails} emails, {batch_size} per batch, {time_per_batch}s per batch")
    print("")
    
    for concurrency in [10, 50, 100, 200]:
        total_batches = total_emails / batch_size
        batches_per_wave = concurrency
        num_waves = total_batches / batches_per_wave
        total_time_seconds = num_waves * time_per_batch
        total_time_minutes = total_time_seconds / 60
        
        print(f"   With {concurrency} concurrent Lambdas:")
        print(f"      Total time: {total_time_minutes:.1f} minutes ({total_time_seconds:.0f} seconds)")
        
        if concurrency >= 100:
            print(f"      ✅ Excellent performance!")
        elif concurrency >= 50:
            print(f"      ✅ Good performance")
        else:
            print(f"      ⚠️  Slower performance")
        print("")
    
    print("=" * 80)
    print("📋 Summary:")
    print("=" * 80)
    print("✅ Your current architecture ALREADY has fan-out via SQS + Lambda")
    print("✅ Lambda automatically scales to process messages in parallel")
    print("")
    print("💡 To improve performance:")
    print("   1. Increase Lambda concurrency limit (if currently restricted)")
    print("   2. Monitor CloudWatch for actual concurrent executions")
    print("   3. Ensure SQS visibility timeout is set correctly")
    print("")
    print("🔧 Run: python fix_sqs_redelivery.py to optimize settings")

if __name__ == '__main__':
    check_concurrency()

