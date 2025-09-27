import boto3
import json

def create_lambda_execution_role():
    """Create IAM role for Lambda execution"""
    
    iam = boto3.client('iam')
    
    # Trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Lambda execution policy
    execution_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                    "dynamodb:BatchWriteItem"
                ],
                "Resource": "arn:aws-us-gov:dynamodb:*:*:table/EmailContacts"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws-us-gov:logs:*:*:*"
            }
        ]
    }
    
    try:
        # Create role
        role_response = iam.create_role(
            RoleName='lambda-email-sender-role',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Lambda execution role for email sender'
        )
        
        # Create policy
        policy_response = iam.create_policy(
            PolicyName='lambda-email-sender-policy',
            PolicyDocument=json.dumps(execution_policy),
            Description='Policy for Lambda email sender function'
        )
        
        # Attach policy to role
        iam.attach_role_policy(
            RoleName='lambda-email-sender-role',
            PolicyArn=policy_response['Policy']['Arn']
        )
        
        print(f"Created role: {role_response['Role']['Arn']}")
        print(f"Created policy: {policy_response['Policy']['Arn']}")
        
        return role_response['Role']['Arn']
        
    except Exception as e:
        print(f"Error creating IAM resources: {str(e)}")
        return None

def create_deployment_user():
    """Create IAM user for deployment"""
    
    iam = boto3.client('iam')
    
    deployment_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:CreateFunction",
                    "lambda:UpdateFunctionCode",
                    "lambda:UpdateFunctionConfiguration",
                    "lambda:AddPermission",
                    "lambda:GetFunction"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "apigateway:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:CreateTable",
                    "dynamodb:DescribeTable"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:PassRole"
                ],
                "Resource": "arn:aws-us-gov:iam::*:role/lambda-email-sender-role"
            }
        ]
    }
    
    try:
        # Create user
        user_response = iam.create_user(
            UserName='email-sender-deployer'
        )
        
        # Create policy
        policy_response = iam.create_policy(
            PolicyName='email-sender-deployment-policy',
            PolicyDocument=json.dumps(deployment_policy),
            Description='Policy for deploying email sender resources'
        )
        
        # Attach policy to user
        iam.attach_user_policy(
            UserName='email-sender-deployer',
            PolicyArn=policy_response['Policy']['Arn']
        )
        
        # Create access keys
        keys_response = iam.create_access_key(
            UserName='email-sender-deployer'
        )
        
        print(f"Created user: {user_response['User']['UserName']}")
        print(f"Access Key ID: {keys_response['AccessKey']['AccessKeyId']}")
        print(f"Secret Access Key: {keys_response['AccessKey']['SecretAccessKey']}")
        print("Save these credentials securely!")
        
        return keys_response['AccessKey']
        
    except Exception as e:
        print(f"Error creating deployment user: {str(e)}")
        return None

if __name__ == "__main__":
    print("Creating IAM resources for email sender...")
    
    # Create Lambda execution role
    role_arn = create_lambda_execution_role()
    
    # Create deployment user
    access_key = create_deployment_user()
    
    if role_arn and access_key:
        print("\nIAM resources created successfully!")
        print(f"Lambda Role ARN: {role_arn}")
        print("Use the deployment credentials to run the deployment scripts.")