# Email API with AWS Secrets Manager Integration

This document describes the updated email API that uses AWS Secrets Manager to securely store AWS SES credentials instead of storing them directly in the web UI or DynamoDB.

## Changes Made

### 1. Web UI Updates
- Removed AWS Access Key and Secret Key input fields
- Added "AWS Secrets Manager Secret Name" field
- Updated JavaScript to handle the new field

### 2. Backend Updates
- Modified `save_email_config()` to store secret name instead of credentials
- Updated `get_email_config()` to hide secret name for security
- Added `get_aws_credentials_from_secrets_manager()` function
- Updated `send_ses_email()` to retrieve credentials from Secrets Manager

### 3. Security Improvements
- AWS credentials are no longer stored in DynamoDB
- Credentials are retrieved securely from AWS Secrets Manager at runtime
- Secret name is masked in API responses

## Setup Instructions

### 1. Create Secret in AWS Secrets Manager

Run the setup script to create your credentials secret:

```bash
python setup_email_credentials_secret.py create
```

Or manually create a secret with the following JSON structure:
```json
{
    "aws_access_key_id": "YOUR_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_SECRET_KEY"
}
```

### 2. Update Lambda IAM Role

Add the following permissions to your Lambda function's IAM role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": [
                "arn:aws-us-gov:secretsmanager:us-gov-west-1:*:secret:email-api-credentials*"
            ]
        }
    ]
}
```

Or use the provided policy file:
```bash
aws iam put-role-policy --role-name YOUR_LAMBDA_ROLE --policy-name SecretsManagerAccess --policy-document file://secrets_manager_policy.json
```

### 3. Configure Email Service

1. Deploy the updated Lambda function
2. Open the web UI
3. Go to "Email Config" tab
4. Select "AWS SES" as email service
5. Enter your AWS region (default: us-gov-west-1)
6. Enter the secret name you created (e.g., "email-api-credentials")
7. Configure other settings and save

## Testing

Run the test suite to verify everything is working:

```bash
python test_email_config.py
```

This will test:
- DynamoDB connectivity
- Secrets Manager integration
- Configuration functions

## Available Scripts

### Setup Credentials Secret
```bash
python setup_email_credentials_secret.py create
```

### List Existing Secrets
```bash
python setup_email_credentials_secret.py list
```

### Test Secret Retrieval
```bash
python setup_email_credentials_secret.py test email-api-credentials
```

## Secret Structure

The secret in AWS Secrets Manager should contain:

```json
{
    "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

## Security Benefits

1. **No Credential Storage**: AWS credentials are never stored in DynamoDB or exposed in the web UI
2. **Runtime Retrieval**: Credentials are only retrieved when needed for sending emails
3. **AWS Managed Security**: Leverages AWS Secrets Manager's encryption and access controls
4. **Audit Trail**: All secret access is logged in CloudTrail
5. **Rotation Support**: Secrets can be rotated without code changes

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your Lambda role has `secretsmanager:GetSecretValue` permission
2. **Secret Not Found**: Verify the secret name is correct and exists in the same region
3. **Invalid Secret Format**: Ensure the secret contains the required JSON structure

### Debugging

Check CloudWatch logs for detailed error messages. The function logs all secret retrieval attempts and any errors encountered.

## Migration from Previous Version

If you were previously storing credentials directly in DynamoDB:

1. Create the secret in AWS Secrets Manager
2. Deploy the updated Lambda function
3. Update your email configuration with the secret name
4. The old credential fields will be ignored

No data migration is required as the new system doesn't use the old credential fields.

