# Lambda-Based Bulk Email Sender with DynamoDB

A serverless bulk email sending solution using AWS Lambda, DynamoDB, and SES.

## Architecture

- **Lambda Function**: Handles email sending and contact management
- **DynamoDB**: Stores contact information and tracks email history
- **SES**: Sends emails with personalization
- **GUI Client**: Desktop interface to manage campaigns

## Setup Instructions

### 1. Create DynamoDB Table
```bash
python dynamodb_table_setup.py
```

### 2. Create IAM Role
Create an IAM role with the policy in `lambda_deployment.json`:
- Role name: `lambda-email-sender-role`
- Attach the policy for SES, DynamoDB, and CloudWatch permissions

### 3. Deploy Lambda Function
1. Update the IAM role ARN in `deploy_lambda.py`
2. Run: `python deploy_lambda.py`

### 4. Configure GUI Client
1. Install dependencies: `pip install boto3`
2. Run: `python gui_lambda_client.py`
3. Configure AWS credentials and Lambda function name

## Features

### Lambda Function (`lambda_email_sender.py`)
- **send_campaign**: Sends bulk emails to all contacts in DynamoDB
- **add_contact**: Adds new contact to DynamoDB
- **get_contacts**: Retrieves all contacts from DynamoDB
- **update_contact**: Updates existing contact information

### DynamoDB Schema
```json
{
  "email": "primary_key",
  "first_name": "string",
  "last_name": "string", 
  "company": "string",
  "created_at": "timestamp",
  "last_email_sent": "timestamp",
  "last_campaign": "string",
  "email_count": "number"
}
```

### Email Tracking
- Updates `last_email_sent` timestamp when email is sent
- Tracks `email_count` for each contact
- Records `last_campaign` name

## Usage

1. **Setup**: Configure AWS credentials in GUI
2. **Import Contacts**: Upload CSV to DynamoDB via GUI
3. **Create Template**: Design HTML email with personalization
4. **Send Campaign**: Execute via Lambda function
5. **Track Results**: View sending results and contact history

## Personalization Placeholders
- `{{first_name}}` - Contact's first name
- `{{last_name}}` - Contact's last name  
- `{{email}}` - Contact's email address
- `{{company}}` - Contact's company

## Benefits of Lambda Architecture

- **Serverless**: No server management required
- **Scalable**: Automatically handles varying loads
- **Cost-effective**: Pay only for execution time
- **Reliable**: Built-in retry and error handling
- **Persistent Storage**: DynamoDB maintains contact history

## Security Notes

- Use IAM roles with minimal required permissions
- Store credentials securely
- Enable CloudWatch logging for monitoring
- Consider VPC configuration for enhanced security