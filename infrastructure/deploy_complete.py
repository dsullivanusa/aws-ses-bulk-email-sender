#!/usr/bin/env python3
"""
Complete Deployment Script for Bulk Email API
Automates all deployment steps
"""

import boto3
import sys
import time
from datetime import datetime

def print_step(step_num, title):
    """Print formatted step header"""
    print(f"\n{'='*70}")
    print(f"  STEP {step_num}: {title}")
    print(f"{'='*70}\n")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")

def check_aws_credentials():
    """Verify AWS credentials are configured"""
    try:
        sts = boto3.client('sts', region_name='us-gov-west-1')
        identity = sts.get_caller_identity()
        print_success(f"AWS credentials valid for account: {identity['Account']}")
        return True
    except Exception as e:
        print_error(f"AWS credentials not configured: {e}")
        return False

def create_dynamodb_tables():
    """Create all required DynamoDB tables"""
    print_step(1, "Creating DynamoDB Tables")
    
    dynamodb = boto3.client('dynamodb', region_name='us-gov-west-1')
    
    tables = [
        {
            'name': 'EmailContacts',
            'key': 'email',
            'description': 'Stores email contacts'
        },
        {
            'name': 'EmailCampaigns',
            'key': 'campaign_id',
            'description': 'Tracks email campaigns'
        },
        {
            'name': 'EmailConfig',
            'key': 'config_id',
            'description': 'Stores email configuration'
        }
    ]
    
    for table_config in tables:
        table_name = table_config['name']
        key_name = table_config['key']
        
        try:
            # Check if table exists
            dynamodb.describe_table(TableName=table_name)
            print_success(f"{table_name} table already exists")
        except dynamodb.exceptions.ResourceNotFoundException:
            # Create table
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': key_name, 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': key_name, 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print_success(f"Created {table_name} table")
            
            # Wait for table to be active
            print(f"  Waiting for {table_name} to be active...")
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            print_success(f"{table_name} is now active")
        except Exception as e:
            print_error(f"Error with {table_name}: {e}")
            return False
    
    return True

def check_secrets_manager():
    """Check if AWS Secrets Manager secret exists"""
    print_step(2, "Checking AWS Secrets Manager")
    
    secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')
    
    secret_name = input("Enter your Secrets Manager secret name (default: email-api-credentials): ").strip()
    if not secret_name:
        secret_name = "email-api-credentials"
    
    try:
        secrets_client.describe_secret(SecretId=secret_name)
        print_success(f"Secret '{secret_name}' found")
        return secret_name
    except secrets_client.exceptions.ResourceNotFoundException:
        print_warning(f"Secret '{secret_name}' not found")
        print("\nYou need to create the secret first. Run:")
        print(f"  python setup_email_credentials_secret.py create")
        
        create_now = input("\nWould you like to create it now? (y/N): ").strip().lower()
        if create_now == 'y':
            print("\nPlease run: python setup_email_credentials_secret.py create")
            print("Then re-run this deployment script.")
            return None
        return None
    except Exception as e:
        print_error(f"Error checking secret: {e}")
        return None

def deploy_lambda_and_api():
    """Deploy Lambda function and API Gateway"""
    print_step(3, "Deploying Lambda Function and API Gateway")
    
    print("Running deployment script...")
    
    import deploy_bulk_email_api
    try:
        deploy_bulk_email_api.deploy_bulk_email_api()
        print_success("Lambda and API Gateway deployed successfully")
        return True
    except Exception as e:
        print_error(f"Deployment failed: {e}")
        return False

def update_lambda_permissions():
    """Update Lambda IAM role with Secrets Manager permissions"""
    print_step(4, "Updating Lambda IAM Permissions")
    
    iam_client = boto3.client('iam')
    role_name = 'bulk-email-api-lambda-role'
    
    # Read the policy from file
    try:
        with open('secrets_manager_policy.json', 'r') as f:
            policy_document = f.read()
        
        # Attach inline policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='SecretsManagerAccess',
            PolicyDocument=policy_document
        )
        print_success("Secrets Manager permissions added to Lambda role")
        return True
        
    except iam_client.exceptions.NoSuchEntityException:
        print_error(f"IAM role '{role_name}' not found")
        return False
    except FileNotFoundError:
        print_error("secrets_manager_policy.json not found")
        return False
    except Exception as e:
        if 'EntityAlreadyExists' in str(e):
            print_success("Secrets Manager permissions already exist")
            return True
        print_error(f"Error updating permissions: {e}")
        return False

def run_tests():
    """Run test suite"""
    print_step(5, "Running Tests")
    
    try:
        import test_email_config
        test_email_config.main()
        return True
    except Exception as e:
        print_error(f"Tests failed: {e}")
        return False

def get_api_url():
    """Get the API Gateway URL"""
    apigateway = boto3.client('apigateway', region_name='us-gov-west-1')
    
    try:
        apis = apigateway.get_rest_apis()['items']
        api = next((a for a in apis if a['name'] == 'bulk-email-api'), None)
        
        if api:
            api_id = api['id']
            api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
            return api_url
        return None
    except Exception as e:
        print_warning(f"Could not retrieve API URL: {e}")
        return None

def main():
    """Main deployment function"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║          Bulk Email API - Complete Deployment Script            ║
║                                                                  ║
║  This script will deploy the complete email campaign system     ║
║  with AWS Secrets Manager integration                           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    start_time = datetime.now()
    
    # Check AWS credentials
    if not check_aws_credentials():
        print("\n❌ Deployment aborted: AWS credentials not configured")
        sys.exit(1)
    
    # Create DynamoDB tables
    if not create_dynamodb_tables():
        print("\n❌ Deployment aborted: DynamoDB table creation failed")
        sys.exit(1)
    
    # Check Secrets Manager
    secret_name = check_secrets_manager()
    if not secret_name:
        print("\n❌ Deployment aborted: Secrets Manager setup required")
        sys.exit(1)
    
    # Deploy Lambda and API Gateway
    if not deploy_lambda_and_api():
        print("\n❌ Deployment aborted: Lambda/API Gateway deployment failed")
        sys.exit(1)
    
    # Update Lambda permissions
    if not update_lambda_permissions():
        print("\n⚠️  Warning: Could not update Lambda permissions")
        print("   You may need to manually add Secrets Manager permissions")
    
    # Run tests
    print("\n")
    run_tests()
    
    # Deployment summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print(f"  🎉 DEPLOYMENT COMPLETE!")
    print(f"{'='*70}\n")
    
    api_url = get_api_url()
    if api_url:
        print(f"🌐 Web UI URL: {api_url}")
    
    print(f"⏱️  Deployment time: {duration:.1f} seconds")
    print(f"📝 Secret name: {secret_name}")
    
    print(f"\n{'='*70}")
    print("  Next Steps:")
    print(f"{'='*70}\n")
    print("1. Open the Web UI in your browser")
    print("2. Configure email service (AWS SES or SMTP)")
    print(f"3. Enter your secret name: {secret_name}")
    print("4. Import contacts or add manually")
    print("5. Send your first campaign!")
    
    print("\n📚 For more information, see DEPLOYMENT_GUIDE.md")
    print("\n✅ Your bulk email system is ready to use!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
