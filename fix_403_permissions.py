#!/usr/bin/env python3
"""
Fix 403 Permission Issues for Lambda Function
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def get_lambda_role():
    """Get the Lambda function's IAM role name"""
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        function_config = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        role_arn = function_config['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        return role_name
    except Exception as e:
        print(f"❌ Error getting Lambda role: {str(e)}")
        return None

def add_dynamodb_permissions(role_name):
    """Add comprehensive DynamoDB permissions"""
    print(f"📝 Adding DynamoDB permissions to role: {role_name}")
    
    dynamodb_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:BatchGetItem",
                    "dynamodb:DescribeTable"
                ],
                "Resource": [
                    f"arn:aws-us-gov:dynamodb:{REGION}:*:table/EmailContacts",
                    f"arn:aws-us-gov:dynamodb:{REGION}:*:table/EmailCampaigns", 
                    f"arn:aws-us-gov:dynamodb:{REGION}:*:table/EmailConfig",
                    f"arn:aws-us-gov:dynamodb:{REGION}:*:table/EmailContacts/index/*",
                    f"arn:aws-us-gov:dynamodb:{REGION}:*:table/EmailCampaigns/index/*",
                    f"arn:aws-us-gov:dynamodb:{REGION}:*:table/EmailConfig/index/*"
                ]
            }
        ]
    }
    
    try:
        iam_client = boto3.client('iam', region_name=REGION)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='DynamoDBEmailAccess',
            PolicyDocument=json.dumps(dynamodb_policy)
        )
        print("✅ DynamoDB permissions added successfully")
        return True
    except Exception as e:
        print(f"❌ Error adding DynamoDB permissions: {str(e)}")
        return False

def add_s3_permissions(role_name):
    """Add S3 permissions for attachments bucket"""
    print(f"📝 Adding S3 permissions to role: {role_name}")
    
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws-us-gov:s3:::jcdc-ses-contact-list",
                    "arn:aws-us-gov:s3:::jcdc-ses-contact-list/*"
                ]
            }
        ]
    }
    
    try:
        iam_client = boto3.client('iam', region_name=REGION)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='S3AttachmentAccess',
            PolicyDocument=json.dumps(s3_policy)
        )
        print("✅ S3 permissions added successfully")
        return True
    except Exception as e:
        print(f"❌ Error adding S3 permissions: {str(e)}")
        return False

def add_secrets_manager_permissions(role_name):
    """Add Secrets Manager permissions"""
    print(f"📝 Adding Secrets Manager permissions to role: {role_name}")
    
    secrets_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                "Resource": f"arn:aws-us-gov:secretsmanager:{REGION}:*:secret:email-config-*"
            }
        ]
    }
    
    try:
        iam_client = boto3.client('iam', region_name=REGION)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='SecretsManagerAccess',
            PolicyDocument=json.dumps(secrets_policy)
        )
        print("✅ Secrets Manager permissions added successfully")
        return True
    except Exception as e:
        print(f"❌ Error adding Secrets Manager permissions: {str(e)}")
        return False

def add_sqs_permissions(role_name):
    """Add SQS permissions"""
    print(f"📝 Adding SQS permissions to role: {role_name}")
    
    sqs_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl"
                ],
                "Resource": f"arn:aws-us-gov:sqs:{REGION}:*:email-queue*"
            }
        ]
    }
    
    try:
        iam_client = boto3.client('iam', region_name=REGION)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='SQSEmailAccess',
            PolicyDocument=json.dumps(sqs_policy)
        )
        print("✅ SQS permissions added successfully")
        return True
    except Exception as e:
        print(f"❌ Error adding SQS permissions: {str(e)}")
        return False

def verify_tables_exist():
    """Verify all required DynamoDB tables exist"""
    print("🔍 Verifying DynamoDB tables exist...")
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    tables_to_check = ['EmailContacts', 'EmailCampaigns', 'EmailConfig']
    missing_tables = []
    
    for table_name in tables_to_check:
        try:
            table = dynamodb.Table(table_name)
            table.load()
            print(f"✅ {table_name} exists")
        except Exception as e:
            print(f"❌ {table_name} missing: {str(e)}")
            missing_tables.append(table_name)
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {missing_tables}")
        print("Run: python setup_all_tables.py")
        return False
    
    return True

def test_permissions():
    """Test if permissions are working"""
    print("🧪 Testing permissions...")
    
    try:
        # Test DynamoDB access
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table('EmailContacts')
        response = table.scan(Limit=1)
        print("✅ DynamoDB access test passed")
        
        # Test S3 access
        s3_client = boto3.client('s3', region_name=REGION)
        s3_client.head_bucket(Bucket='jcdc-ses-contact-list')
        print("✅ S3 access test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Permission test failed: {str(e)}")
        if '403' in str(e) or 'AccessDenied' in str(e):
            print("🔴 Still getting 403 errors - permissions may need time to propagate")
        return False

def main():
    """Fix all permission issues"""
    print("🔧 Fixing Lambda 403 Permission Issues")
    print("="*60)
    
    # Get Lambda role
    role_name = get_lambda_role()
    if not role_name:
        print("❌ Cannot proceed without Lambda role name")
        return
    
    print(f"🔐 Working with IAM role: {role_name}")
    print("="*60)
    
    # Verify tables exist first
    if not verify_tables_exist():
        print("\n❌ Please create missing DynamoDB tables first")
        return
    
    # Add all required permissions
    success_count = 0
    
    if add_dynamodb_permissions(role_name):
        success_count += 1
    
    if add_s3_permissions(role_name):
        success_count += 1
        
    if add_secrets_manager_permissions(role_name):
        success_count += 1
        
    if add_sqs_permissions(role_name):
        success_count += 1
    
    print(f"\n📊 Added {success_count}/4 permission sets successfully")
    
    if success_count > 0:
        print("\n⏳ Waiting 10 seconds for permissions to propagate...")
        import time
        time.sleep(10)
        
        print("\n🧪 Testing permissions...")
        if test_permissions():
            print("\n✅ SUCCESS! 403 errors should be resolved")
            print("\n🎯 Next steps:")
            print("1. Test your Lambda function again")
            print("2. Check the web UI for contact loading")
            print("3. Run: python diagnose_403_errors.py to verify")
        else:
            print("\n⚠️  Permissions added but still getting errors")
            print("This might be due to:")
            print("1. Permission propagation delay (wait 1-2 minutes)")
            print("2. Resource-based policies blocking access")
            print("3. Different account/region configuration")
    else:
        print("\n❌ Failed to add permissions - check IAM access")

if __name__ == '__main__':
    main()