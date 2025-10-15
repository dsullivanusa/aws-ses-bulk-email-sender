#!/usr/bin/env python3
"""
Consolidated Bulk Email API Deployment Script

This script provides five deployment modes:
- simple: Deploys API-only Lambda with basic API Gateway (assumes IAM role exists)
- full: Deploys complete solution with IAM role creation, private API Gateway, and web UI
- redeploy: Redeploys existing API Gateway to production stage without recreating resources
- worker: Deploys email worker Lambda with SQS trigger for processing queued email jobs
- monitoring: Adds monitoring system and CloudWatch alarms to existing email worker Lambda

Usage:
    python deployment/deploy.py --mode simple --account-id YOUR_ACCOUNT_ID
    python deployment/deploy.py --mode full
    python deployment/deploy.py --mode redeploy --api-name bulk-email-api
    python deployment/deploy.py --mode worker --queue-name my-queue
    python deployment/deploy.py --mode monitoring

Options:
    help='Deployment mode: simple (API-only), api (API infrastructure), full (complete infrastructure), redeploy (redeploy existing API), worker (email worker Lambda), or monitoring (add monitoring to existing deployment)')
    --account-id: AWS account ID (required for simple mode)
    --lambda-file: Lambda source file (defaults based on mode)
    --function-name: Lambda function name (defaults based on mode)
    --api-name: API Gateway name (defaults based on mode)
    --queue-name: SQS queue name (defaults to bulk-email-queue for worker mode)
"""

import boto3  # type: ignore
import json
import zipfile
import argparse
import time
import os
import sys
from typing import Optional

def deploy_simple_mode(account_id: str, lambda_file: str = 'api_gateway_lambda.py', function_name: str = 'email-api-function', api_name: str = 'bulk-email-api') -> Optional[str]:
    """Deploy API-only Lambda with basic public API Gateway"""

    print("🚀 Starting SIMPLE deployment mode...")
    print(f"   Lambda file: {lambda_file}")
    print(f"   Function name: {function_name}")
    print(f"   API name: {api_name}")
    print(f"   Account ID: {account_id}")

    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')  # type: ignore
    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')  # type: ignore

    # Create deployment package
    zip_filename = f'{function_name.replace("-", "_")}_lambda.zip'
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
        # Include lib modules if they exist
        if os.path.exists('lib'):
            for root, _, files in os.walk('lib'):
                for file in files:
                    if file.endswith('.py'):
                        zip_file.write(os.path.join(root, file), os.path.join(root, file))

    try:
        # Deploy Lambda function
        with open(zip_filename, 'rb') as zip_file:
            zip_content = zip_file.read()

        role_arn = f'arn:aws-us-gov:iam::{account_id}:role/lambda-email-sender-role'

        try:
            response = lambda_client.create_function(  # type: ignore
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='API Gateway Lambda for bulk email sender',
                Timeout=300,
                MemorySize=256
            )
            print(f"✅ Lambda function '{function_name}' created!")
        except lambda_client.exceptions.ResourceConflictException:  # type: ignore
            response = lambda_client.update_function_code(  # type: ignore
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"✅ Lambda function '{function_name}' updated!")

        # Create API Gateway
        api_response = apigateway_client.create_rest_api(  # type: ignore
            name=api_name,
            description='Bulk Email Sender API'
        )

        api_id = api_response['id']
        print(f"✅ API Gateway '{api_name}' created: {api_id}")

        # Get root resource
        resources = apigateway_client.get_resources(restApiId=api_id)  # type: ignore
        root_id = resources['items'][0]['id']

        # Create resources based on Lambda file
        if lambda_file == 'api_gateway_lambda.py':
            # API Gateway Lambda - comprehensive endpoints
            resources_to_create = [
                ('contacts', ['GET', 'POST', 'OPTIONS']),
                ('campaign', ['POST', 'OPTIONS']),
                ('groups', ['GET', 'POST', 'OPTIONS']),
                ('search', ['GET', 'OPTIONS']),
                ('config', ['GET', 'POST', 'OPTIONS'])
            ]
        else:
            # Bulk Email API Lambda - basic endpoints
            resources_to_create = [
                ('contacts', ['GET', 'POST', 'OPTIONS']),
                ('campaign', ['POST', 'OPTIONS']),
                ('config', ['GET', 'POST', 'OPTIONS'])
            ]

        for resource_name, methods in resources_to_create:
            resource = apigateway_client.create_resource(  # type: ignore
                restApiId=api_id,
                parentId=root_id,
                pathPart=resource_name
            )

            for method in methods:
                apigateway_client.put_method(  # type: ignore
                    restApiId=api_id,
                    resourceId=resource['id'],
                    httpMethod=method,
                    authorizationType='NONE'
                )

                apigateway_client.put_integration(  # type: ignore
                    restApiId=api_id,
                    resourceId=resource['id'],
                    httpMethod=method,
                    type='AWS_PROXY',
                    integrationHttpMethod='POST',
                    uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/arn:aws-us-gov:lambda:us-gov-west-1:{account_id}:function:{function_name}/invocations"
                )

        # Deploy API
        deployment = apigateway_client.create_deployment(  # type: ignore
            restApiId=api_id,
            stageName='prod'
        )

        # Add Lambda permission
        try:
            lambda_client.add_permission(  # type: ignore
                FunctionName=function_name,
                StatementId='api-gateway-invoke',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws-us-gov:execute-api:us-gov-west-1:{account_id}:{api_id}/*/*"
            )
        except lambda_client.exceptions.ResourceConflictException:  # type: ignore
            pass

        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"\n🎉 SIMPLE deployment complete!")
        print(f"   API URL: {api_url}")
        print(f"   Update your web UI to use this URL")

        return api_url

    except Exception as e:
        print(f"❌ Error in simple deployment: {str(e)}")
        return None

def deploy_full_mode(lambda_file: str = 'bulk_email_api_lambda.py', function_name: str = 'bulk-email-api-function', api_name: str = 'bulk-email-api') -> Optional[str]:
    """Deploy complete solution with IAM role creation and private API Gateway"""

    print("🚀 Starting FULL deployment mode...")
    print(f"   Lambda file: {lambda_file}")
    print(f"   Function name: {function_name}")
    print(f"   API name: {api_name}")

    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')  # type: ignore
    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')  # type: ignore
    iam_client = boto3.client('iam')  # type: ignore

    # Create IAM role
    role_name = 'bulk-email-api-lambda-role'

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
        iam_client.create_role(  # type: ignore
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for bulk email API Lambda function'
        )
        print(f"✅ Created IAM role: {role_name}")
        time.sleep(10)  # Wait for propagation
    except iam_client.exceptions.EntityAlreadyExistsException:  # type: ignore
        print(f"ℹ️  IAM role '{role_name}' already exists")

    # Attach policies
    policies = [
        'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSESFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonS3FullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSQSFullAccess',
        'arn:aws-us-gov:iam::aws:policy/SecretsManagerReadWrite'
    ]

    for policy in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy)  # type: ignore
            print(f"✅ Attached policy: {policy.split('/')[-1]}")
        except Exception as e:
            print(f"⚠️  Policy attachment issue: {e}")

    # Get role ARN
    role_response = iam_client.get_role(RoleName=role_name)  # type: ignore
    role_arn = role_response['Role']['Arn']
    account_id = role_arn.split(':')[4]

    # Create Lambda function
    zip_filename = f'{function_name.replace("-", "_")}_lambda.zip'
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
        # Include lib modules
        if os.path.exists('lib'):
            for root, _, files in os.walk('lib'):
                for file in files:
                    if file.endswith('.py'):
                        zip_file.write(os.path.join(root, file), os.path.join(root, file))

    with open(zip_filename, 'rb') as zip_file:
        try:
            lambda_client.create_function(  # type: ignore
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Description='Bulk email API',
                Timeout=900,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'ATTACHMENTS_BUCKET': 'jcdc-ses-contact-list'
                    }
                }
            )
            print(f"✅ Created Lambda function: {function_name}")
        except lambda_client.exceptions.ResourceConflictException:  # type: ignore
            zip_file.seek(0)
            lambda_client.update_function_code(  # type: ignore
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
            print(f"✅ Updated Lambda function: {function_name}")

    # Create private API Gateway
    try:
        # Check if API Gateway already exists
        apis = apigateway_client.get_rest_apis()['items']  # type: ignore
        existing_api = next((api for api in apis if api['name'] == api_name), None)

        if existing_api:
            api_id = existing_api['id']
            print(f"ℹ️  Using existing API Gateway: {api_id}")
        else:
            api_response = apigateway_client.create_rest_api(  # type: ignore
                name=api_name,
                description='Private Bulk Email API',
                endpointConfiguration={'types': ['PRIVATE']},
                policy=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "execute-api:Invoke",
                            "Resource": "*",
                            "Condition": {
                                "IpAddress": {
                                    "aws:sourceIp": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
                                }
                            }
                        }
                    ]
                })
            )
            api_id = api_response['id']
            print(f"✅ Created private API Gateway: {api_id}")

        if not existing_api:
            # Get root resource
            resources = apigateway_client.get_resources(restApiId=api_id)  # type: ignore
            root_id = resources['items'][0]['id']

            # Create resources and methods
            resources_to_create = [
                ('config', ['GET', 'POST']),
                ('contacts', ['GET', 'POST', 'PUT', 'DELETE']),
                ('campaign', ['POST']),
                ('groups', ['GET', 'POST']),
                ('search', ['GET']),
                ('upload-attachment', ['POST']),
            ]

            # Create sub-resources for contacts
            contacts_sub_resources = [
                ('distinct', ['GET']),
                ('filter', ['POST']),
                ('batch', ['POST']),
                ('search', ['POST']),
            ]

            # Create sub-resources for campaign
            campaign_sub_resources = [
                ('{campaign_id}', ['GET']),
            ]

            lambda_arn = f"arn:aws-us-gov:lambda:us-gov-west-1:{account_id}:function:{function_name}"

            for resource_name, methods in resources_to_create:
                resource_response = apigateway_client.create_resource(  # type: ignore
                    restApiId=api_id,
                    parentId=root_id,
                    pathPart=resource_name
                )
                resource_id = resource_response['id']

                for method in methods:
                    apigateway_client.put_method(  # type: ignore
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod=method,
                        authorizationType='NONE'
                    )

                    apigateway_client.put_integration(  # type: ignore
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod=method,
                        type='AWS_PROXY',
                        integrationHttpMethod='POST',
                        uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
                    )

            # Create contacts sub-resources
            contacts_resource_id = None
            for resource in apigateway_client.get_resources(restApiId=api_id)['items']:  # type: ignore
                if resource['path'] == '/contacts':
                    contacts_resource_id = resource['id']
                    break

            if contacts_resource_id:
                for sub_resource_name, methods in contacts_sub_resources:
                    sub_resource_response = apigateway_client.create_resource(  # type: ignore
                        restApiId=api_id,
                        parentId=contacts_resource_id,
                        pathPart=sub_resource_name
                    )
                    sub_resource_id = sub_resource_response['id']

                    for method in methods:
                        apigateway_client.put_method(  # type: ignore
                            restApiId=api_id,
                            resourceId=sub_resource_id,
                            httpMethod=method,
                            authorizationType='NONE'
                        )

                        apigateway_client.put_integration(  # type: ignore
                            restApiId=api_id,
                            resourceId=sub_resource_id,
                            httpMethod=method,
                            type='AWS_PROXY',
                            integrationHttpMethod='POST',
                            uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
                        )

            # Create campaign sub-resources
            campaign_resource_id = None
            for resource in apigateway_client.get_resources(restApiId=api_id)['items']:  # type: ignore
                if resource['path'] == '/campaign':
                    campaign_resource_id = resource['id']
                    break

            if campaign_resource_id:
                for sub_resource_name, methods in campaign_sub_resources:
                    sub_resource_response = apigateway_client.create_resource(  # type: ignore
                        restApiId=api_id,
                        parentId=campaign_resource_id,
                        pathPart=sub_resource_name
                    )
                    sub_resource_id = sub_resource_response['id']

                    for method in methods:
                        apigateway_client.put_method(  # type: ignore
                            restApiId=api_id,
                            resourceId=sub_resource_id,
                            httpMethod=method,
                            authorizationType='NONE'
                        )

                        apigateway_client.put_integration(  # type: ignore
                            restApiId=api_id,
                            resourceId=sub_resource_id,
                            httpMethod=method,
                            type='AWS_PROXY',
                            integrationHttpMethod='POST',
                            uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
                        )

            # Add GET method to root for web UI
            apigateway_client.put_method(  # type: ignore
                restApiId=api_id,
                resourceId=root_id,
                httpMethod='GET',
                authorizationType='NONE'
            )

            apigateway_client.put_integration(  # type: ignore
                restApiId=api_id,
                resourceId=root_id,
                httpMethod='GET',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
            )

        # Deploy API
        apigateway_client.create_deployment(  # type: ignore
            restApiId=api_id,
            stageName='prod'
        )

        # Enable logging
        try:
            apigateway_client.update_stage(  # type: ignore
                restApiId=api_id,
                stageName='prod',
                patchOperations=[
                    {
                        'op': 'replace',
                        'path': '/*/*/logging/loglevel',
                        'value': 'INFO'
                    },
                    {
                        'op': 'replace',
                        'path': '/*/*/logging/dataTrace',
                        'value': 'true'
                    }
                ]
            )
        except Exception as e:
            print(f"⚠️  Could not enable logging: {e}")

        # Add Lambda permissions
        try:
            lambda_client.add_permission(  # type: ignore
                FunctionName=function_name,
                StatementId='api-gateway-invoke',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws-us-gov:execute-api:us-gov-west-1:{account_id}:{api_id}/*/*"
            )
        except lambda_client.exceptions.ResourceConflictException:  # type: ignore
            print("ℹ️  Lambda permission already exists")

        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"

        print(f"\n🎉 FULL deployment complete!")
        print(f"   API Gateway ID: {api_id}")
        print(f"   Private API URL: {api_url}")
        print(f"   Web UI: {api_url} (served from Lambda)")
        print(f"\n⚠️  IMPORTANT: This is a PRIVATE API Gateway")
        print(f"   - Only accessible from private IP ranges (10.x, 172.16-31.x, 192.168.x)")
        print(f"   - Update IP ranges in resource policy as needed")
        print(f"   - Access via Load Balancer or VPC resources")

        return api_url

    except Exception as e:
        print(f"❌ Error in full deployment: {str(e)}")
        return None

def deploy_worker_mode(lambda_file: str = 'email_worker_lambda.py', function_name: str = 'email-worker-function', queue_name: str = 'bulk-email-queue') -> Optional[str]:
    """Deploy email worker Lambda with SQS trigger"""

    print("🚀 Starting WORKER deployment mode...")
    print(f"   Lambda file: {lambda_file}")
    print(f"   Function name: {function_name}")
    print(f"   SQS Queue: {queue_name}")

    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')  # type: ignore
    iam_client = boto3.client('iam')  # type: ignore
    sqs_client = boto3.client('sqs', region_name='us-gov-west-1')  # type: ignore

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
        iam_client.create_role(  # type: ignore
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for email worker Lambda function'
        )
        print(f"✅ Created IAM role: {role_name}")
        time.sleep(10)  # Wait for propagation
    except iam_client.exceptions.EntityAlreadyExistsException:  # type: ignore
        print(f"ℹ️  IAM role '{role_name}' already exists")

    # Attach policies
    policies = [
        'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSESFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSQSFullAccess'
    ]

    for policy in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy)  # type: ignore
            print(f"✅ Attached policy: {policy.split('/')[-1]}")
        except Exception as e:
            print(f"⚠️  Policy attachment issue: {e}")

    # Add Secrets Manager permissions (if policy file exists)
    try:
        if os.path.exists('secrets_manager_policy.json'):
            with open('secrets_manager_policy.json', 'r') as f:
                secrets_policy = f.read()

            iam_client.put_role_policy(  # type: ignore
                RoleName=role_name,
                PolicyName='SecretsManagerAccess',
                PolicyDocument=secrets_policy
            )
            print(f"✅ Added Secrets Manager permissions")
    except Exception as e:
        print(f"⚠️  Secrets Manager policy issue: {e}")

    # Get role ARN and account ID
    role_response = iam_client.get_role(RoleName=role_name)  # type: ignore
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
                "Resource": f"arn:aws-us-gov:sqs:us-gov-west-1:{account_id}:{queue_name}"
            },
            {
                "Effect": "Allow",
                "Action": ["sqs:GetQueueUrl"],
                "Resource": "*"
            }
        ]
    }

    try:
        iam_client.put_role_policy(  # type: ignore
            RoleName=role_name,
            PolicyName='SQSReceiveMessagePolicy',
            PolicyDocument=json.dumps(sqs_inline_policy)
        )
        print(f"✅ Added SQS receive permissions")
        time.sleep(5)  # Wait for policy to propagate
    except Exception as e:
        print(f"⚠️  SQS inline policy issue: {e}")

    # Create Lambda deployment package
    zip_filename = f'{function_name.replace("-", "_")}_lambda.zip'
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write(lambda_file, 'lambda_function.py')
        # Include lib modules if they exist
        if os.path.exists('lib'):
            for root, _, files in os.walk('lib'):
                for file in files:
                    if file.endswith('.py'):
                        zip_file.write(os.path.join(root, file), os.path.join(root, file))

    # Deploy Lambda function
    with open(zip_filename, 'rb') as zip_file:
        try:
            lambda_client.create_function(  # type: ignore
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Description='Email worker to process SQS messages and send emails',
                Timeout=300,  # 5 minutes
                MemorySize=512
            )
            print(f"✅ Created Lambda function: {function_name}")
        except lambda_client.exceptions.ResourceConflictException:  # type: ignore
            zip_file.seek(0)
            lambda_client.update_function_code(  # type: ignore
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
            print(f"✅ Updated Lambda function: {function_name}")

    # Configure SQS trigger
    try:
        queue_url_response = sqs_client.get_queue_url(QueueName=queue_name)  # type: ignore
        queue_url = queue_url_response['QueueUrl']

        queue_attrs = sqs_client.get_queue_attributes(  # type: ignore
            QueueUrl=queue_url,
            AttributeNames=['QueueArn']
        )
        queue_arn = queue_attrs['Attributes']['QueueArn']

        print(f"\n⚙️  Configuring SQS trigger...")

        # Create event source mapping (SQS trigger)
        try:
            lambda_client.create_event_source_mapping(  # type: ignore
                EventSourceArn=queue_arn,
                FunctionName=function_name,
                BatchSize=10,  # Process up to 10 messages at once
                MaximumBatchingWindowInSeconds=5,  # Wait up to 5 seconds to batch messages
                Enabled=True
            )
            print(f"✅ Created SQS trigger for Lambda function")
        except lambda_client.exceptions.ResourceConflictException:  # type: ignore
            print(f"ℹ️  SQS trigger already exists")

        print(f"\n🎉 WORKER deployment complete!")
        print(f"   Function: {function_name}")
        print(f"   SQS Queue: {queue_name}")
        print(f"   The worker will automatically process email jobs from the queue")

        return function_name

    except sqs_client.exceptions.QueueDoesNotExist:  # type: ignore
        print(f"⚠️  Warning: SQS queue '{queue_name}' not found")
        print(f"   Run 'python create_sqs_queue.py' to create the queue first")
        print(f"   Lambda function deployed but SQS trigger not configured")
        return function_name

    except Exception as e:
        print(f"❌ Error configuring SQS trigger: {str(e)}")
        return None

def deploy_monitoring_mode(lambda_file: str = 'email_worker_lambda.py', function_name: str = 'email-worker-function') -> Optional[str]:
    """Deploy monitoring system for existing Lambda functions - creates CloudWatch alarms only"""

    print("📊 Starting MONITORING deployment mode...")
    print(f"   Lambda file: {lambda_file}")
    print(f"   Function name: {function_name}")

    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')  # type: ignore
    cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')  # type: ignore

    try:
        # Find the email worker function
        functions = lambda_client.list_functions()
        worker_function_name = None

        patterns = [
            function_name,
            'email-worker-function',
            'email-worker',
            'EmailWorker',
            'email_worker'
        ]

        for pattern in patterns:
            matches = [f for f in functions['Functions'] if pattern.lower() in f['FunctionName'].lower()]
            if matches:
                worker_function_name = matches[0]['FunctionName']
                break

        if not worker_function_name:
            print("❌ Could not find email worker Lambda function")
            print("   Please deploy the worker Lambda first using: python deployment/deploy.py --mode worker")
            return None

        print(f"✅ Found worker function: {worker_function_name}")

        print(f"\n📊 Setting up monitoring for existing email worker...")
        print(f"   Note: The worker already has built-in adaptive rate control and error detection")
        print(f"   This monitoring mode only creates CloudWatch alarms to observe worker behavior")

        # Create CloudWatch alarms - the worker already sends these metrics
        print("\n🚨 Creating CloudWatch Alarms...")

        alarms = [
            {
                'name': 'EmailWorker-FunctionErrors',
                'description': 'Email Worker Lambda function errors',
                'metric': 'Errors',
                'namespace': 'AWS/Lambda',
                'statistic': 'Sum',
                'threshold': 1.0,
                'operator': 'GreaterThanOrEqualToThreshold',
                'period': 300,
                'evaluation_periods': 2,
                'dimensions': [{'Name': 'FunctionName', 'Value': worker_function_name}]
            },
            {
                'name': 'EmailWorker-HighDuration',
                'description': 'Email Worker Lambda function taking too long',
                'metric': 'Duration',
                'namespace': 'AWS/Lambda',
                'statistic': 'Average',
                'threshold': 600000.0,  # 10 minutes
                'operator': 'GreaterThanThreshold',
                'period': 300,
                'evaluation_periods': 3,
                'dimensions': [{'Name': 'FunctionName', 'Value': worker_function_name}]
            },
            {
                'name': 'EmailWorker-ThrottleExceptions',
                'description': 'Email Worker detected throttle exceptions (custom metric from worker)',
                'metric': 'ThrottleExceptions',
                'namespace': 'EmailWorker/Custom',
                'statistic': 'Sum',
                'threshold': 1.0,
                'operator': 'GreaterThanOrEqualToThreshold',
                'period': 300,
                'evaluation_periods': 2
            },
            {
                'name': 'EmailWorker-IncompleteCampaigns',
                'description': 'Email campaigns not completed within expected time (custom metric from worker)',
                'metric': 'IncompleteCampaigns',
                'namespace': 'EmailWorker/Custom',
                'statistic': 'Sum',
                'threshold': 1.0,
                'operator': 'GreaterThanOrEqualToThreshold',
                'period': 300,
                'evaluation_periods': 2
            },
            {
                'name': 'EmailWorker-EmailsFailed',
                'description': 'Email Worker failed to send emails (custom metric from worker)',
                'metric': 'EmailsFailed',
                'namespace': 'EmailWorker/Custom',
                'statistic': 'Sum',
                'threshold': 1.0,
                'operator': 'GreaterThanOrEqualToThreshold',
                'period': 300,
                'evaluation_periods': 2
            },
            {
                'name': 'EmailWorker-HighFailureRate',
                'description': 'Email Worker has high failure rate (custom metric from worker)',
                'metric': 'FailureRate',
                'namespace': 'EmailWorker/Custom',
                'statistic': 'Average',
                'threshold': 5.0,  # 5% failure rate
                'operator': 'GreaterThanThreshold',
                'period': 300,
                'evaluation_periods': 3
            }
        ]

        created_alarms = []
        for alarm_config in alarms:
            try:
                alarm_params = {
                    'AlarmName': alarm_config['name'],
                    'AlarmDescription': alarm_config['description'],
                    'MetricName': alarm_config['metric'],
                    'Namespace': alarm_config['namespace'],
                    'Statistic': alarm_config['statistic'],
                    'Period': alarm_config['period'],
                    'EvaluationPeriods': alarm_config['evaluation_periods'],
                    'Threshold': alarm_config['threshold'],
                    'ComparisonOperator': alarm_config['operator'],
                    'TreatMissingData': 'notBreaching'
                }

                if 'dimensions' in alarm_config:
                    alarm_params['Dimensions'] = alarm_config['dimensions']

                cloudwatch.put_metric_alarm(**alarm_params)  # type: ignore
                created_alarms.append(alarm_config['name'])
                print(f"  ✅ Created alarm: {alarm_config['name']}")

            except Exception as e:
                print(f"  ⚠️ Failed to create {alarm_config['name']}: {str(e)}")

        print(f"\n📊 Monitoring System Deployment Complete!")
        print(f"   Worker Function: {worker_function_name}")
        print(f"   CloudWatch Alarms: {len(created_alarms)}")
        print(f"\n🎯 Monitoring Features Active:")
        print(f"   📈 Adaptive rate control: Already implemented in worker Lambda")
        print(f"   🚨 Error detection: Already implemented in worker Lambda")
        print(f"   📊 Campaign completion monitoring: Custom metrics from worker")
        print(f"   ⏱️ Performance monitoring: Lambda duration and custom metrics")
        print(f"   📧 Email failure monitoring: Custom metrics from worker")
        print(f"\n📋 What the monitoring system does:")
        print(f"   ✅ Creates CloudWatch alarms to monitor worker behavior")
        print(f"   ✅ Observes metrics already sent by the worker Lambda")
        print(f"   ✅ Does NOT modify worker code or configuration")
        print(f"   ✅ Maintains separation between business logic and monitoring")
        print(f"\n📋 Next Steps:")
        print(f"   1. Monitor CloudWatch alarms in AWS console")
        print(f"   2. Test email campaigns to verify metrics are being sent")
        print(f"   3. Review CloudWatch metrics and logs")

        return worker_function_name

    except Exception as e:
        print(f"❌ Error in monitoring deployment: {str(e)}")
        return None

def redeploy_api(api_name: str = 'bulk-email-api') -> Optional[str]:
    """Redeploy existing API Gateway to prod stage"""

    print("🔄 Starting API REDEPLOYMENT mode...")
    print(f"   API name: {api_name}")

    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')  # type: ignore

    try:
        # Find the API Gateway
        print("🔍 Finding API Gateway...")
        apis = apigateway_client.get_rest_apis()['items']  # type: ignore

        api = None
        for api_item in apis:
            if api_name.lower() in api_item['name'].lower():
                api = api_item
                break

        if not api:
            print(f"❌ API Gateway '{api_name}' not found!")
            print("\nAvailable APIs:")
            for api_item in apis:
                print(f"  - {api_item['name']} (ID: {api_item['id']})")
            return None

        api_id = api['id']
        api_name_found = api['name']
        print(f"✅ Found API: {api_name_found} (ID: {api_id})")

        # Check for search endpoint (optional validation)
        print("\n🔍 Checking API resources...")
        resources = apigateway_client.get_resources(restApiId=api_id)  # type: ignore

        endpoints_found = []
        for resource in resources['items']:
            if resource['path'] and resource['path'] != '/':
                endpoints_found.append(resource['path'])

        if endpoints_found:
            print(f"✅ Found {len(endpoints_found)} endpoints:")
            for endpoint in sorted(endpoints_found):
                print(f"   - {endpoint}")
        else:
            print("⚠️  No endpoints found")

        # Deploy to prod stage
        print("\n🚀 Deploying API to 'prod' stage...")

        deployment = apigateway_client.create_deployment(  # type: ignore
            restApiId=api_id,
            stageName='prod',
            description='Redeployed via consolidated script'
        )

        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"\n🎉 API redeployed successfully!")
        print(f"   API URL: {api_url}")
        print(f"   Deployment ID: {deployment['id']}")

        return api_url

    except Exception as e:
        print(f"❌ Error in redeployment: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Deploy Bulk Email API')
    parser.add_argument('--mode', required=True, choices=['simple', 'full', 'redeploy', 'worker', 'monitoring'],
                       help='Deployment mode: simple (API-only), full (complete infrastructure), redeploy (redeploy existing API), worker (email worker Lambda), or monitoring (add monitoring to existing deployment)')
    parser.add_argument('--account-id', help='AWS account ID (required for simple mode)')
    parser.add_argument('--lambda-file', default=None,
                       help='Lambda source file (defaults based on mode)')
    parser.add_argument('--function-name', default=None,
                       help='Lambda function name (defaults based on mode)')
    parser.add_argument('--api-name', default=None,
                       help='API Gateway name (defaults based on mode)')
    parser.add_argument('--queue-name', default=None,
                       help='SQS queue name (defaults to bulk-email-queue for worker mode)')

    args = parser.parse_args()

    # Validate arguments
    if args.mode == 'simple' and not args.account_id:
        print("❌ Error: --account-id is required for simple mode")
        sys.exit(1)

    # Handle redeploy mode
    if args.mode == 'redeploy':
        api_name = args.api_name or 'bulk-email-api'
        result = redeploy_api(api_name)
        if result:
            print(f"\n✅ Redeployment successful!")
            print(f"   API URL: {result}")
        else:
            print(f"\n❌ Redeployment failed!")
            sys.exit(1)
        return

    # Handle worker mode
    if args.mode == 'worker':
        lambda_file = args.lambda_file or 'email_worker_lambda.py'
        function_name = args.function_name or 'email-worker-function'
        queue_name = args.queue_name or 'bulk-email-queue'

        # Validate Lambda file exists
        if not os.path.exists(lambda_file):
            print(f"❌ Error: Lambda file '{lambda_file}' not found")
            sys.exit(1)

        result = deploy_worker_mode(lambda_file, function_name, queue_name)
        if result:
            print(f"\n✅ Worker deployment successful!")
            print(f"   Function: {result}")
        else:
            print(f"\n❌ Worker deployment failed!")
            sys.exit(1)
        return

    # Handle monitoring mode
    if args.mode == 'monitoring':
        lambda_file = args.lambda_file or 'email_worker_lambda.py'
        function_name = args.function_name or 'email-worker-function'

        # Validate Lambda file exists
        if not os.path.exists(lambda_file):
            print(f"❌ Error: Lambda file '{lambda_file}' not found")
            sys.exit(1)

        result = deploy_monitoring_mode(lambda_file, function_name)
        if result:
            print(f"\n✅ Monitoring deployment successful!")
            print(f"   Enhanced Function: {result}")
        else:
            print(f"\n❌ Monitoring deployment failed!")
            sys.exit(1)
        return

    # Set defaults based on mode for simple/full
    if args.mode == 'simple':
        lambda_file = args.lambda_file or 'api_gateway_lambda.py'
        function_name = args.function_name or 'email-api-function'
        api_name = args.api_name or 'bulk-email-api'
    else:  # full mode
        lambda_file = args.lambda_file or 'bulk_email_api_lambda.py'
        function_name = args.function_name or 'bulk-email-api-function'
        api_name = args.api_name or 'bulk-email-api'

    # Validate Lambda file exists
    if not os.path.exists(lambda_file):
        print(f"❌ Error: Lambda file '{lambda_file}' not found")
        sys.exit(1)

    # Execute deployment
    if args.mode == 'simple':
        result = deploy_simple_mode(args.account_id, lambda_file, function_name, api_name)
    else:
        result = deploy_full_mode(lambda_file, function_name, api_name)

    if result:
        print(f"\n✅ Deployment successful!")
        print(f"   API URL: {result}")
    else:
        print(f"\n❌ Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()