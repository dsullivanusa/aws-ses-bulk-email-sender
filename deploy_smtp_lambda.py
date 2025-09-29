import boto3
import zipfile
import json
import time

def deploy_smtp_lambda():
    """Deploy SMTP bulk email Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    iam_client = boto3.client('iam')
    
    # Create execution role
    role_name = 'smtp-bulk-email-lambda-role'
    
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
    
    role_created = False
    try:
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for SMTP bulk email Lambda function'
        )
        print(f"Created IAM role: {role_name}")
        role_created = True
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"IAM role {role_name} already exists")
    
    # Attach policies
    policies = [
        'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess'
    ]
    
    for policy in policies:
        try:
            iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy)
            print(f"Attached policy: {policy}")
        except Exception as e:
            print(f"Policy attachment error: {e}")
    
    # Wait for role propagation if newly created
    if role_created:
        print("Waiting for role propagation...")
        time.sleep(10)
    
    # Get role ARN
    role_response = iam_client.get_role(RoleName=role_name)
    role_arn = role_response['Role']['Arn']
    
    # Create deployment package
    with zipfile.ZipFile('smtp_bulk_email_lambda.zip', 'w') as zip_file:
        zip_file.write('smtp_bulk_email_lambda.py', 'lambda_function.py')
    
    # Create Lambda function
    function_name = 'smtp-bulk-email-function'
    
    with open('smtp_bulk_email_lambda.zip', 'rb') as zip_file:
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Description='SMTP bulk email sender with rate limiting',
                Timeout=900,  # 15 minutes
                MemorySize=512,
                Environment={
                    'Variables': {
                        'REGION': 'us-gov-west-1'
                    }
                }
            )
            print(f"Created Lambda function: {function_name}")
            
        except lambda_client.exceptions.ResourceConflictException:
            # Update existing function
            zip_file.seek(0)
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
            print(f"Updated Lambda function: {function_name}")
    
    print(f"\nDeployment complete!")
    print(f"Function Name: {function_name}")
    print(f"Lambda ARN: {role_arn.replace('role', 'function').replace(role_name, function_name)}")
    print(f"Create API Gateway manually and point to this Lambda function")
    print(f"Use API Gateway URL with your Load Balancer")

if __name__ == "__main__":
    deploy_smtp_lambda()