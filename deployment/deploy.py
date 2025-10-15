#!/usr/bin/env python3
"""
Consolidated Bulk Email API Deployment Script

This script provides two deployment modes:
- simple: Deploys API-only Lambda with basic API Gateway (assumes IAM role exists)
- full: Deploys complete solution with IAM role creation, private API Gateway, and web UI

Usage:
    python deployment/deploy.py --mode simple --account-id YOUR_ACCOUNT_ID
    python deployment/deploy.py --mode full

Options:
    --mode: 'simple' or 'full' deployment mode
    --account-id: AWS account ID (required for simple mode)
    --lambda-file: Lambda source file ('api_gateway_lambda.py' or 'bulk_email_api_lambda.py')
    --function-name: Lambda function name (optional, defaults based on mode)
    --api-name: API Gateway name (optional, defaults based on mode)
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
                Description='Bulk email API with web UI support',
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
                description='Private Bulk Email API with Web UI',
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
        print(f"❌ Error in full deployment: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Deploy Bulk Email API')
    parser.add_argument('--mode', required=True, choices=['simple', 'full'],
                       help='Deployment mode: simple (API-only) or full (complete infrastructure)')
    parser.add_argument('--account-id', help='AWS account ID (required for simple mode)')
    parser.add_argument('--lambda-file', default=None,
                       help='Lambda source file (defaults based on mode)')
    parser.add_argument('--function-name', default=None,
                       help='Lambda function name (defaults based on mode)')
    parser.add_argument('--api-name', default=None,
                       help='API Gateway name (defaults based on mode)')

    args = parser.parse_args()

    # Validate arguments
    if args.mode == 'simple' and not args.account_id:
        print("❌ Error: --account-id is required for simple mode")
        sys.exit(1)

    # Set defaults based on mode
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