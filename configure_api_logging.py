import boto3
import json

def configure_api_logging():
    """Configure API Gateway logging and X-Ray tracing"""
    
    apigateway = boto3.client('apigateway', region_name='us-gov-west-1')
    iam = boto3.client('iam', region_name='us-gov-west-1')
    logs = boto3.client('logs', region_name='us-gov-west-1')
    
    # Get API Gateway
    apis = apigateway.get_rest_apis()
    api_id = None
    for api in apis['items']:
        if api['name'] == 'vpc-smtp-bulk-email-api':
            api_id = api['id']
            break
    
    if not api_id:
        print("API Gateway not found")
        return
    
    # Create CloudWatch log group
    log_group_name = f'/aws/apigateway/{api_id}'
    try:
        logs.create_log_group(logGroupName=log_group_name)
        print(f"Created log group: {log_group_name}")
    except logs.exceptions.ResourceAlreadyExistsException:
        print(f"Log group already exists: {log_group_name}")
    
    # Create IAM role for API Gateway logging
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "apigateway.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    role_name = 'APIGatewayCloudWatchLogsRole'
    try:
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for API Gateway CloudWatch logging'
        )
        
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws-us-gov:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs'
        )
        print(f"Created IAM role: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM role already exists: {role_name}")
    
    # Get role ARN
    role = iam.get_role(RoleName=role_name)
    role_arn = role['Role']['Arn']
    
    # Set account-level CloudWatch role
    try:
        apigateway.update_account(
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/cloudwatchRoleArn',
                    'value': role_arn
                }
            ]
        )
        print("Updated account CloudWatch role")
    except Exception as e:
        print(f"Account role update: {e}")
    
    # Custom log format with all variables including source IP
    log_format = json.dumps({
        "requestId": "$context.requestId",
        "requestTime": "$context.requestTime",
        "requestTimeEpoch": "$context.requestTimeEpoch",
        "httpMethod": "$context.httpMethod",
        "resourcePath": "$context.resourcePath",
        "path": "$context.path",
        "protocol": "$context.protocol",
        "status": "$context.status",
        "responseLength": "$context.responseLength",
        "responseLatency": "$context.responseLatency",
        "integrationLatency": "$context.integrationLatency",
        "sourceIp": "$context.identity.sourceIp",
        "userAgent": "$context.identity.userAgent",
        "user": "$context.identity.user",
        "caller": "$context.identity.caller",
        "cognitoIdentityId": "$context.identity.cognitoIdentityId",
        "cognitoAuthenticationType": "$context.identity.cognitoAuthenticationType",
        "principalOrgId": "$context.identity.principalOrgId",
        "apiKey": "$context.identity.apiKey",
        "apiKeyId": "$context.identity.apiKeyId",
        "accessKey": "$context.identity.accessKey",
        "accountId": "$context.identity.accountId",
        "userArn": "$context.identity.userArn",
        "stage": "$context.stage",
        "domainName": "$context.domainName",
        "apiId": "$context.apiId",
        "error.message": "$context.error.message",
        "error.messageString": "$context.error.messageString",
        "integration.error": "$context.integration.error",
        "integration.integrationStatus": "$context.integration.integrationStatus",
        "integration.latency": "$context.integration.latency",
        "integration.requestId": "$context.integration.requestId",
        "integration.status": "$context.integration.status",
        "authorizer.claims": "$context.authorizer.claims",
        "authorizer.principalId": "$context.authorizer.principalId",
        "wafResponseCode": "$context.wafResponseCode",
        "webaclArn": "$context.webaclArn",
        "xrayTraceId": "$context.xrayTraceId"
    })
    
    # Update stage with logging and X-Ray tracing
    try:
        apigateway.update_stage(
            restApiId=api_id,
            stageName='prod',
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/accessLogSettings/destinationArn',
                    'value': f'arn:aws-us-gov:logs:us-gov-west-1:*:log-group:{log_group_name}'
                },
                {
                    'op': 'replace',
                    'path': '/accessLogSettings/format',
                    'value': log_format
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
                },
                {
                    'op': 'replace',
                    'path': '/*/*/metrics/enabled',
                    'value': 'true'
                },
                {
                    'op': 'replace',
                    'path': '/tracingConfig/mode',
                    'value': 'Active'
                }
            ]
        )
        print("Updated stage with logging and X-Ray tracing")
    except Exception as e:
        print(f"Stage update error: {e}")
    
    print(f"API Gateway logging configured for {api_id}")
    print(f"Log group: {log_group_name}")
    print("X-Ray tracing enabled")
    print("Custom log format includes source IP and all context variables")

if __name__ == "__main__":
    configure_api_logging()