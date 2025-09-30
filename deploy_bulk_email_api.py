import boto3
import zipfile
import json
import time

def deploy_bulk_email_api():
    """Deploy complete bulk email solution with API Gateway"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')
    iam_client = boto3.client('iam')
    
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
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for bulk email API Lambda function'
        )
        print(f"Created IAM role: {role_name}")
        time.sleep(10)  # Wait for propagation
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"IAM role {role_name} already exists")
    
    # Attach policies
    policies = [
        'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess',
        'arn:aws-us-gov:iam::aws:policy/AmazonSESFullAccess'
    ]
    
    for policy in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy)
            print(f"Attached policy: {policy}")
        except Exception as e:
            print(f"Policy error: {e}")
    
    # Get role ARN
    role_response = iam_client.get_role(RoleName=role_name)
    role_arn = role_response['Role']['Arn']
    
    # Create Lambda function
    function_name = 'bulk-email-api-function'
    
    with zipfile.ZipFile('bulk_email_api_lambda.zip', 'w') as zip_file:
        zip_file.write('bulk_email_api_lambda.py', 'lambda_function.py')
    
    with open('bulk_email_api_lambda.zip', 'rb') as zip_file:
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Description='Bulk email API with SES and SMTP support',
                Timeout=900,
                MemorySize=512
            )
            print(f"Created Lambda function: {function_name}")
        except lambda_client.exceptions.ResourceConflictException:
            zip_file.seek(0)
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
            print(f"Updated Lambda function: {function_name}")
    
    # Create API Gateway
    api_name = 'bulk-email-api'
    
    try:
        # Check if API Gateway already exists
        apis = apigateway_client.get_rest_apis()['items']
        existing_api = next((api for api in apis if api['name'] == api_name), None)
        
        if existing_api:
            api_id = existing_api['id']
            print(f"Using existing API Gateway: {api_id}")
        else:
            # Create private API Gateway
            api_response = apigateway_client.create_rest_api(
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
            print(f"Created API Gateway: {api_id}")
        
        if not existing_api:
            # Get root resource
            resources = apigateway_client.get_resources(restApiId=api_id)
            root_id = resources['items'][0]['id']
            
            # Create resources and methods
            resources_to_create = [
                ('config', ['GET', 'POST']),
                ('contacts', ['GET', 'POST', 'PUT', 'DELETE']),
                ('campaign', ['POST']),
            ]
            
            for resource_name, methods in resources_to_create:
                # Create resource
                resource_response = apigateway_client.create_resource(
                    restApiId=api_id,
                    parentId=root_id,
                    pathPart=resource_name
                )
                resource_id = resource_response['id']
                
                # Create methods
                for method in methods:
                    apigateway_client.put_method(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod=method,
                        authorizationType='NONE'
                    )
                    
                    # Set up integration
                    lambda_arn = f"arn:aws-us-gov:lambda:us-gov-west-1:{role_arn.split(':')[4]}:function:{function_name}"
                    
                    apigateway_client.put_integration(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod=method,
                        type='AWS_PROXY',
                        integrationHttpMethod='POST',
                        uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
                    )
            
            # Add GET method to root for web UI
            apigateway_client.put_method(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod='GET',
                authorizationType='NONE'
            )
            
            lambda_arn = f"arn:aws-us-gov:lambda:us-gov-west-1:{role_arn.split(':')[4]}:function:{function_name}"
            
            apigateway_client.put_integration(
                restApiId=api_id,
                resourceId=root_id,
                httpMethod='GET',
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
            )
        
        # Deploy API
        apigateway_client.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )
        
        # Enable logging
        apigateway_client.update_stage(
            restApiId=api_id,
            stageName='prod',
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/accessLogSettings/destinationArn',
                    'value': f'arn:aws-us-gov:logs:us-gov-west-1:{role_arn.split(":")[4]}:log-group:API-Gateway-Execution-Logs_{api_id}/prod'
                },
                {
                    'op': 'replace',
                    'path': '/accessLogSettings/format',
                    'value': '{"requestId":"$context.requestId","extendedRequestId":"$context.extendedRequestId","ip":"$context.identity.sourceIp","caller":"$context.identity.caller","user":"$context.identity.user","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","resourcePath":"$context.resourcePath","protocol":"$context.protocol","status":"$context.status","error":"$context.error.message","responseLength":"$context.responseLength","requestLength":"$context.requestLength","integrationStatus":"$context.integrationStatus","integrationLatency":"$context.integrationLatency","responseLatency":"$context.responseLatency","stage":"$context.stage","apiId":"$context.apiId"}'
                },
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
        
        # Add Lambda permissions (skip if already exists)
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId='api-gateway-invoke',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws-us-gov:execute-api:us-gov-west-1:{role_arn.split(':')[4]}:{api_id}/*/*"
            )
        except lambda_client.exceptions.ResourceConflictException:
            print("Lambda permission already exists")
        
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        
        print(f"\\nPrivate API Gateway Deployment Complete!")
        print(f"API Gateway ID: {api_id}")
        print(f"Private API URL: {api_url}")
        print(f"\\nIMPORTANT: This is a PRIVATE API Gateway")
        print(f"1. Only accessible from private IP ranges (10.x, 172.16-31.x, 192.168.x)")
        print(f"2. Update IP ranges in resource policy as needed")
        print(f"3. Access via Load Balancer or VPC resources")
        print(f"4. Modify sourceIp condition for your specific IP ranges")
        
    except Exception as e:
        print(f"API Gateway error: {e}")

if __name__ == "__main__":
    deploy_bulk_email_api()