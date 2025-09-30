#!/usr/bin/env python3
"""
Deploy Email Worker Lambda Function
This Lambda processes messages from SQS and sends emails
"""

import boto3
import zipfile
import json
import time

def deploy_email_worker_lambda():
    """Deploy the email worker Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    iam_client = boto3.client('iam')
    sqs_client = boto3.client('sqs', region_name='us-gov-west-1')
    
    # Create IAM role for worker Lambda
    role_name = 'email-worker-lambda-role'
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for email worker Lambda function'
        )
        print(f"✓ Created IAM role: {role_name}")
        time.sleep(10)  # Wait for propagation
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"✓ IAM role {role_name} already exists")
    
    # Attach policies
    policies = [
        'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSESFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSQSFullAccess'
    ]
    
    for policy in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy)
            print(f"✓ Attached policy: {policy.split('/')[-1]}")
        except Exception as e:
            if 'EntityAlreadyExists' not in str(e):
                print(f"⚠️  Policy warning: {e}")
    
    # Add Secrets Manager permissions
    try:
        with open('secrets_manager_policy.json', 'r') as f:
            secrets_policy = f.read()
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='SecretsManagerAccess',
            PolicyDocument=secrets_policy
        )
        print(f"✓ Added Secrets Manager permissions")
    except Exception as e:
        if 'EntityAlreadyExists' not in str(e):
            print(f"⚠️  Secrets Manager policy warning: {e}")
    
    # Get role ARN
    role_response = iam_client.get_role(RoleName=role_name)
    role_arn = role_response['Role']['Arn']
    account_id = role_arn.split(':')[4]
    
    # Add inline SQS policy with specific permissions for the queue
    sqs_inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:ChangeMessageVisibility"
                ],
                "Resource": f"arn:aws-us-gov:sqs:us-gov-west-1:{account_id}:bulk-email-queue"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:GetQueueUrl"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='SQSReceiveMessagePolicy',
            PolicyDocument=json.dumps(sqs_inline_policy)
        )
        print(f"✓ Added SQS receive permissions for Lambda execution role")
        time.sleep(5)  # Wait for policy to propagate
    except Exception as e:
        if 'EntityAlreadyExists' not in str(e):
            print(f"⚠️  SQS inline policy warning: {e}")
    
    # Create Lambda deployment package
    function_name = 'email-worker-function'
    
    print(f"\n📦 Creating deployment package...")
    with zipfile.ZipFile('email_worker_lambda.zip', 'w') as zip_file:
        zip_file.write('email_worker_lambda.py', 'lambda_function.py')
    print(f"✓ Package created")
    
    # Create or update Lambda function
    with open('email_worker_lambda.zip', 'rb') as zip_file:
        zip_data = zip_file.read()
        
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_data},
                Description='Email worker to process SQS messages and send emails',
                Timeout=300,  # 5 minutes
                MemorySize=512
            )
            print(f"✓ Created Lambda function: {function_name}")
        except lambda_client.exceptions.ResourceConflictException:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_data
            )
            print(f"✓ Updated Lambda function: {function_name}")
    
    # Get SQS queue ARN
    try:
        queue_url_response = sqs_client.get_queue_url(QueueName='bulk-email-queue')
        queue_url = queue_url_response['QueueUrl']
        
        queue_attrs = sqs_client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['QueueArn']
        )
        queue_arn = queue_attrs['Attributes']['QueueArn']
        
        print(f"\n⚙️  Configuring SQS trigger...")
        
        # Create event source mapping (SQS trigger)
        try:
            lambda_client.create_event_source_mapping(
                EventSourceArn=queue_arn,
                FunctionName=function_name,
                BatchSize=10,  # Process up to 10 messages at once
                MaximumBatchingWindowInSeconds=5,  # Wait up to 5 seconds to batch messages
                Enabled=True
            )
            print(f"✓ Created SQS trigger for Lambda function")
        except lambda_client.exceptions.ResourceConflictException:
            print(f"✓ SQS trigger already exists")
        
    except sqs_client.exceptions.QueueDoesNotExist:
        print(f"⚠️  Warning: SQS queue 'bulk-email-queue' not found")
        print(f"   Run 'python create_sqs_queue.py' to create the queue first")
    
    print(f"\n{'='*70}")
    print(f"  Email Worker Lambda Deployment Complete!")
    print(f"{'='*70}")
    print(f"\nFunction Name: {function_name}")
    print(f"Role ARN: {role_arn}")
    print(f"\nThe worker Lambda will automatically process messages from the SQS queue")
    print(f"and send emails via SES or SMTP based on the configuration.")
    
    return function_name

if __name__ == "__main__":
    try:
        deploy_email_worker_lambda()
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
