#!/usr/bin/env python3
"""
Create AWS SQS Queue for Bulk Email Processing
"""

import boto3
import json

def create_email_queue():
    """Create SQS queue for bulk email processing"""
    
    sqs_client = boto3.client('sqs', region_name='us-gov-west-1')
    queue_name = 'bulk-email-queue'
    
    try:
        # Check if queue already exists
        try:
            response = sqs_client.get_queue_url(QueueName=queue_name)
            print(f"Queue '{queue_name}' already exists")
            print(f"  Queue URL: {response['QueueUrl']}")
            return response['QueueUrl']
        except sqs_client.exceptions.QueueDoesNotExist:
            pass
        
        # Create queue with appropriate settings for email processing
        print(f"Creating SQS queue: {queue_name}")
        
        response = sqs_client.create_queue(
            QueueName=queue_name,
            Attributes={
                # Visibility timeout - how long a message is invisible after being received
                # Set to 15 minutes to allow time for email sending
                'VisibilityTimeout': '900',
                
                # Message retention - how long messages stay in queue if not processed
                # Set to 4 days
                'MessageRetentionPeriod': '345600',
                
                # Receive message wait time (long polling)
                'ReceiveMessageWaitTimeSeconds': '20',
                
                # Maximum message size (256 KB - default)
                'MaximumMessageSize': '262144',
                
                # Delay delivery of messages
                'DelaySeconds': '0',
            },
            tags={
                'Purpose': 'Bulk Email Processing',
                'Application': 'Email Campaign Manager'
            }
        )
        
        queue_url = response['QueueUrl']
        print(f"Queue created successfully!")
        print(f"  Queue URL: {queue_url}")
        
        # Get queue ARN
        attrs = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['QueueArn']
        )
        queue_arn = attrs['Attributes']['QueueArn']
        print(f"  Queue ARN: {queue_arn}")
        
        return queue_url
        
    except Exception as e:
        print(f"Error creating queue: {e}")
        return None

def create_dead_letter_queue():
    """Create a Dead Letter Queue for failed messages"""
    
    sqs_client = boto3.client('sqs', region_name='us-gov-west-1')
    dlq_name = 'bulk-email-dlq'
    
    try:
        # Check if DLQ already exists
        try:
            response = sqs_client.get_queue_url(QueueName=dlq_name)
            print(f"Dead Letter Queue '{dlq_name}' already exists")
            print(f"  DLQ URL: {response['QueueUrl']}")
            return response['QueueUrl']
        except sqs_client.exceptions.QueueDoesNotExist:
            pass
        
        # Create Dead Letter Queue
        print(f"Creating Dead Letter Queue: {dlq_name}")
        
        response = sqs_client.create_queue(
            QueueName=dlq_name,
            Attributes={
                'MessageRetentionPeriod': '1209600',  # 14 days
                'ReceiveMessageWaitTimeSeconds': '20',
            },
            tags={
                'Purpose': 'Dead Letter Queue for Failed Emails',
                'Application': 'Email Campaign Manager'
            }
        )
        
        dlq_url = response['QueueUrl']
        print(f"Dead Letter Queue created successfully!")
        print(f"  DLQ URL: {dlq_url}")
        
        return dlq_url
        
    except Exception as e:
        print(f"Error creating DLQ: {e}")
        return None

def configure_dead_letter_queue(queue_url, dlq_url):
    """Configure main queue to use Dead Letter Queue"""
    
    sqs_client = boto3.client('sqs', region_name='us-gov-west-1')
    
    try:
        # Get DLQ ARN
        dlq_attrs = sqs_client.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=['QueueArn']
        )
        dlq_arn = dlq_attrs['Attributes']['QueueArn']
        
        # Configure main queue to use DLQ
        sqs_client.set_queue_attributes(
            QueueUrl=queue_url,
            Attributes={
                'RedrivePolicy': json.dumps({
                    'deadLetterTargetArn': dlq_arn,
                    'maxReceiveCount': '3'  # After 3 failed attempts, move to DLQ
                })
            }
        )
        
        print(f"Configured Dead Letter Queue")
        print(f"  Messages will move to DLQ after 3 failed processing attempts")
        
    except Exception as e:
        print(f"Error configuring DLQ: {e}")

def display_queue_info(queue_url):
    """Display queue information and statistics"""
    
    sqs_client = boto3.client('sqs', region_name='us-gov-west-1')
    
    try:
        # Get queue attributes
        response = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['All']
        )
        
        attrs = response['Attributes']
        
        print(f"\n{'='*70}")
        print(f"  Queue Information")
        print(f"{'='*70}")
        print(f"Queue URL: {queue_url}")
        print(f"Queue ARN: {attrs.get('QueueArn', 'N/A')}")
        print(f"Messages Available: {attrs.get('ApproximateNumberOfMessages', '0')}")
        print(f"Messages In Flight: {attrs.get('ApproximateNumberOfMessagesNotVisible', '0')}")
        print(f"Messages Delayed: {attrs.get('ApproximateNumberOfMessagesDelayed', '0')}")
        print(f"Visibility Timeout: {attrs.get('VisibilityTimeout', '0')} seconds")
        print(f"Message Retention: {int(attrs.get('MessageRetentionPeriod', '0')) // 86400} days")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"Error getting queue info: {e}")

def main():
    """Main function"""
    print("=== AWS SQS Queue Setup for Bulk Email System ===\n")
    
    # Create Dead Letter Queue first
    dlq_url = create_dead_letter_queue()
    print()
    
    # Create main queue
    queue_url = create_email_queue()
    print()
    
    # Configure DLQ if both queues were created
    if queue_url and dlq_url:
        configure_dead_letter_queue(queue_url, dlq_url)
        print()
    
    # Display queue information
    if queue_url:
        display_queue_info(queue_url)
    
    print("\nSQS Queue Setup Complete!")
    print("\nNext Steps:")
    print("1. Update Lambda IAM role with SQS permissions")
    print("2. Create a Lambda function to process messages from the queue")
    print("3. Deploy your updated bulk email API")
    
    print("\nTo add SQS permissions to Lambda role, run:")
    print("  aws iam attach-role-policy \\")
    print("    --role-name bulk-email-api-lambda-role \\")
    print("    --policy-arn arn:aws-us-gov:iam::aws:policy/AmazonSQSFullAccess \\")
    print("    --region us-gov-west-1")

if __name__ == "__main__":
    main()
