#!/usr/bin/env python3
"""
Update Email Worker Lambda Function with S3 Attachment Support
"""

import boto3
import zipfile
import json
import os

REGION = 'us-gov-west-1'
FUNCTION_NAME = 'email-worker-function'  # Change if your function has a different name

def update_email_worker():
    """Update the email worker Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    iam_client = boto3.client('iam')
    
    print("="*60)
    print("Updating Email Worker Lambda with Attachment Support")
    print("="*60)
    print()
    
    # Create deployment package
    print("📦 Creating deployment package...")
    
    # Delete old zip file if exists
    if os.path.exists('email_worker_lambda.zip'):
        os.remove('email_worker_lambda.zip')
        print("Deleted old email_worker_lambda.zip")
    
    with zipfile.ZipFile('email_worker_lambda.zip', 'w') as zip_file:
        zip_file.write('email_worker_lambda.py', 'lambda_function.py')
    print("✓ Package created")
    
    # Update Lambda function code
    print(f"\n📤 Uploading updated code to Lambda function: {FUNCTION_NAME}...")
    with open('email_worker_lambda.zip', 'rb') as zip_file:
        zip_data = zip_file.read()
        
        try:
            lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME,
                ZipFile=zip_data
            )
            print(f"✓ Lambda function code updated successfully")
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"❌ ERROR: Lambda function '{FUNCTION_NAME}' not found!")
            print(f"   Please run: python deploy_email_worker.py")
            return
    
    # Get Lambda role name
    try:
        function_config = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        role_arn = function_config['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        print(f"\n🔐 Lambda role: {role_name}")
    except Exception as e:
        print(f"⚠️  Could not get role: {str(e)}")
        role_name = None
    
    # Add S3 permissions to Lambda role
    if role_name:
        print(f"\n📝 Adding S3 permissions to Lambda role...")
        
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject"
                    ],
                    "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket"
                    ],
                    "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list"
                }
            ]
        }
        
        try:
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName='S3AttachmentAccess',
                PolicyDocument=json.dumps(s3_policy)
            )
            print(f"✓ Added S3 permissions for bucket: jcdc-ses-contact-list")
        except Exception as e:
            print(f"⚠️  Could not add S3 permissions: {str(e)}")
            print(f"   You may need to add this manually in IAM console")
    
    print("\n" + "="*60)
    print("✓ Email Worker Lambda Updated Successfully!")
    print("="*60)
    print("\nWhat's New:")
    print("  ✅ S3 attachment download support")
    print("  ✅ MIME email building with attachments")
    print("  ✅ Uses send_raw_email for attachments")
    print("  ✅ Falls back to send_email if no attachments")
    print("\nNext Steps:")
    print("  1. ✓ Email worker updated")
    print("  2. Test by sending a campaign with an attachment")
    print("  3. Check CloudWatch logs to verify attachment processing")
    print("\nAttachments will now be:")
    print("  • Downloaded from S3 bucket: jcdc-ses-contact-list")
    print("  • Attached to emails automatically")
    print("  • Sent via AWS SES v2 (40 MB limit)")
    
    return True

if __name__ == '__main__':
    try:
        update_email_worker()
    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        import traceback
        traceback.print_exc()

