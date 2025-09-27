# IAM Setup Instructions

## Quick Setup (Automated)

Run the IAM setup script:
```bash
python create_iam_resources.py
```

This creates:
- **Lambda execution role**: `lambda-email-sender-role`
- **Deployment user**: `email-sender-deployer` 
- **Required policies**: Attached automatically

## Manual Setup

### 1. Lambda Execution Role

Create role `lambda-email-sender-role` with trust policy:
```json
{
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
```

Attach policy from `iam_policies.json` → `lambda_execution_policy`

### 2. Deployment User

Create user `email-sender-deployer` and attach policy from `iam_policies.json` → `deployment_policy`

### 3. SES Setup

Attach `ses_setup_policy.json` to verify email addresses.

## Required Permissions Summary

**Lambda Function Needs:**
- SES: Send emails
- DynamoDB: Read/write contacts table
- CloudWatch: Create logs

**Deployment User Needs:**
- Lambda: Create/update functions
- API Gateway: Create/manage APIs
- DynamoDB: Create tables
- IAM: Pass role to Lambda

**SES Setup Needs:**
- Verify email identities
- Check sending quotas

## Security Notes

- Use least privilege principle
- Store credentials securely
- Rotate access keys regularly
- Enable MFA on IAM users