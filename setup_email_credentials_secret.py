#!/usr/bin/env python3
"""
Script to create and manage email API credentials in AWS Secrets Manager
"""

import boto3
import json
import sys
import getpass

def create_email_credentials_secret():
    """Create a new secret in AWS Secrets Manager for email API credentials"""
    
    secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')
    
    print("=== Email API Credentials Setup ===")
    print("This script will create a secret in AWS Secrets Manager to store your email API credentials.")
    print()
    
    # Get secret name
    secret_name = input("Enter secret name (default: email-api-credentials): ").strip()
    if not secret_name:
        secret_name = "email-api-credentials"
    
    # Check if secret already exists
    try:
        secrets_client.describe_secret(SecretId=secret_name)
        print(f"\nSecret '{secret_name}' already exists!")
        update = input("Do you want to update it? (y/N): ").strip().lower()
        if update != 'y':
            print("Exiting...")
            return
    except secrets_client.exceptions.ResourceNotFoundException:
        print(f"Creating new secret: {secret_name}")
    
    # Get credentials
    print("\nEnter your AWS SES credentials:")
    aws_access_key = input("AWS Access Key ID: ").strip()
    if not aws_access_key:
        print("Error: AWS Access Key ID is required")
        return
    
    aws_secret_key = getpass.getpass("AWS Secret Access Key: ").strip()
    if not aws_secret_key:
        print("Error: AWS Secret Access Key is required")
        return
    
    # Create the secret data
    secret_data = {
        "aws_access_key_id": aws_access_key,
        "aws_secret_access_key": aws_secret_key
    }
    
    try:
        # Try to update existing secret
        secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_data)
        )
        print(f"\n✓ Successfully updated secret '{secret_name}'")
        
    except secrets_client.exceptions.ResourceNotFoundException:
        # Create new secret
        secrets_client.create_secret(
            Name=secret_name,
            Description="Email API credentials for bulk email sending",
            SecretString=json.dumps(secret_data)
        )
        print(f"\n✓ Successfully created secret '{secret_name}'")
    
    print(f"\nSecret '{secret_name}' is ready to use in your email configuration!")
    print("Use this secret name in the web UI under 'AWS Secrets Manager Secret Name'")

def list_email_secrets():
    """List existing email-related secrets"""
    secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')
    
    try:
        response = secrets_client.list_secrets()
        email_secrets = [
            secret for secret in response.get('SecretList', [])
            if 'email' in secret['Name'].lower() or 'ses' in secret['Name'].lower()
        ]
        
        if email_secrets:
            print("Existing email-related secrets:")
            for secret in email_secrets:
                print(f"  - {secret['Name']} (created: {secret['CreatedDate']})")
        else:
            print("No email-related secrets found.")
            
    except Exception as e:
        print(f"Error listing secrets: {e}")

def test_secret(secret_name):
    """Test retrieving credentials from a secret"""
    secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        
        print(f"✓ Successfully retrieved secret '{secret_name}'")
        print(f"  Contains fields: {list(secret_data.keys())}")
        
        if 'aws_access_key_id' in secret_data and 'aws_secret_access_key' in secret_data:
            print("  ✓ Contains required AWS credentials")
        else:
            print("  ✗ Missing required AWS credentials")
            
    except Exception as e:
        print(f"✗ Error retrieving secret '{secret_name}': {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            create_email_credentials_secret()
        elif command == "list":
            list_email_secrets()
        elif command == "test":
            if len(sys.argv) > 2:
                test_secret(sys.argv[2])
            else:
                print("Usage: python setup_email_credentials_secret.py test <secret_name>")
        else:
            print("Unknown command. Use: create, list, or test")
    else:
        print("Email API Credentials Setup Script")
        print("Usage:")
        print("  python setup_email_credentials_secret.py create  - Create/update credentials secret")
        print("  python setup_email_credentials_secret.py list    - List existing email secrets")
        print("  python setup_email_credentials_secret.py test <secret_name> - Test secret retrieval")

if __name__ == "__main__":
    main()

