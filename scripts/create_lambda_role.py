import boto3
import json

def create_lambda_role():
    """Create IAM role for Lambda function"""
    
    iam = boto3.client('iam', region_name='us-gov-west-1')
    
    role_name = 'lambda-email-sender-role'
    
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
    
    # Create role
    try:
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for SMTP Lambda function'
        )
        print(f"Created role: {role_name}")
        
        # Create custom policy for EC2 network interfaces
        ec2_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        # Create and attach custom policy
        try:
            iam.create_policy(
                PolicyName='LambdaVPCNetworkPolicy',
                PolicyDocument=json.dumps(ec2_policy)
            )
        except iam.exceptions.EntityAlreadyExistsException:
            pass
        
        # Attach policies
        policies = [
            'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole',
            'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess'
        ]
        
        for policy in policies:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy
            )
            print(f"Attached policy: {policy}")
        
        # Get account ID for custom policy ARN
        account_id = boto3.client('sts').get_caller_identity()['Account']
        custom_policy_arn = f'arn:aws-us-gov:iam::{account_id}:policy/LambdaVPCNetworkPolicy'
        
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=custom_policy_arn
        )
        print(f"Attached custom policy: {custom_policy_arn}")
        
        return role_response['Role']['Arn']
        
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        print(f"Role already exists: {role_name}")
        role_arn = role['Role']['Arn']
    
    # Create custom policy for EC2 network interfaces
    ec2_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DeleteNetworkInterface",
                    "ec2:AttachNetworkInterface",
                    "ec2:DetachNetworkInterface"
                ],
                "Resource": "*"
            }
        ]
    }
    
    # Create and attach custom policy
    try:
        iam.create_policy(
            PolicyName='LambdaVPCNetworkPolicy',
            PolicyDocument=json.dumps(ec2_policy)
        )
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    
    # Attach policies
    policies = [
        'arn:aws-us-gov:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole',
        'arn:aws-us-gov:iam::aws:policy/AmazonDynamoDBFullAccess'
    ]
    
    for policy in policies:
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy
            )
            print(f"Attached policy: {policy}")
        except iam.exceptions.LimitExceededException:
            print(f"Policy already attached: {policy}")
    
    # Get account ID for custom policy ARN
    account_id = boto3.client('sts').get_caller_identity()['Account']
    custom_policy_arn = f'arn:aws-us-gov:iam::{account_id}:policy/LambdaVPCNetworkPolicy'
    
    try:
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=custom_policy_arn
        )
        print(f"Attached custom policy: {custom_policy_arn}")
    except iam.exceptions.LimitExceededException:
        print(f"Custom policy already attached: {custom_policy_arn}")
    
    return role_arn if 'role_arn' in locals() else role_response['Role']['Arn']

if __name__ == "__main__":
    role_arn = create_lambda_role()
    print(f"Role ARN: {role_arn}")