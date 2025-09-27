# SMTP API Gateway Email Sender

Serverless SMTP email sending solution with API Gateway, Lambda, DynamoDB, and full attachment support with real-time progress tracking.

## Architecture

- **API Gateway**: RESTful endpoints for email operations
- **Lambda Function**: SMTP email processing with attachments
- **DynamoDB**: Contact storage and campaign tracking
- **Web UI**: Real-time progress monitoring interface

## Features

### Email Capabilities
- SMTP relay support (Gmail, Outlook, custom servers)
- File attachments (any type, base64 encoded)
- HTML email templates with personalization
- Bulk campaign sending with progress tracking

### Campaign Tracking
- Real-time progress monitoring
- Campaign status persistence in DynamoDB
- Contact email history updates
- Detailed sending results and error reporting

### API Endpoints

**POST /smtp-campaign**
- Send bulk email campaign with attachments
- Updates contact records in DynamoDB
- Returns campaign ID for tracking

**GET /campaign-status/{campaign_id}**
- Get real-time campaign progress
- Returns sent/failed counts and status

**GET /contacts**
- Retrieve all contacts from DynamoDB

**POST /contacts**
- Add new contact to DynamoDB

## Setup Instructions

### 1. Create DynamoDB Tables
```bash
python dynamodb_table_setup.py      # EmailContacts table
python dynamodb_campaigns_table.py  # EmailCampaigns table
```

### 2. Deploy API Gateway and Lambda
1. Update `YOUR_ACCOUNT_ID` in `deploy_smtp_api_gateway.py`
2. Create IAM role: `lambda-email-sender-role`
3. Run: `python deploy_smtp_api_gateway.py`

### 3. Configure Web UI
1. Update `API_BASE_URL` in `smtp_web_ui_api.html`
2. Host web UI on S3 or web server

### 4. SMTP Configuration
Set environment variables in Lambda or pass in request:
- `SMTP_SERVER`: SMTP server hostname
- `SMTP_PORT`: SMTP port (587 for TLS)
- `SMTP_USERNAME`: SMTP username
- `SMTP_PASSWORD`: SMTP password

## DynamoDB Schema

### EmailContacts Table
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

### EmailCampaigns Table
```json
{
  "campaign_id": "primary_key",
  "campaign_name": "string",
  "status": "pending|in_progress|completed|failed",
  "total_contacts": "number",
  "sent_count": "number",
  "failed_count": "number",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

## Attachment Handling

**Web UI Upload:**
- Files converted to base64 encoding
- Sent in JSON payload to Lambda
- Decoded and attached to emails

**Supported Formats:**
- Documents: PDF, DOC, DOCX, TXT
- Images: JPG, PNG, GIF, BMP
- Archives: ZIP, RAR, 7Z
- Any file type supported

**Size Limits:**
- API Gateway: 10MB payload limit
- SMTP servers: Usually 25MB per email
- Lambda: 6MB synchronous payload

## Real-Time Progress Tracking

### Campaign Status Flow
1. **Pending**: Campaign created, not started
2. **In Progress**: Emails being sent
3. **Completed**: All emails processed
4. **Failed**: Campaign encountered errors

### Progress Updates
- DynamoDB updated after each email sent
- Web UI polls campaign status every 2 seconds
- Real-time progress bar and counters
- Contact records updated with send timestamps

## API Request Examples

### Send Campaign with Attachments
```json
POST /smtp-campaign
{
  "subject": "Welcome {{first_name}}!",
  "body": "<h1>Hello {{first_name}}</h1>",
  "campaign_name": "Welcome Campaign",
  "from_email": "sender@domain.com",
  "smtp_server": "smtp.gmail.com",
  "smtp_username": "user@gmail.com",
  "smtp_password": "app-password",
  "attachments": [
    {
      "filename": "document.pdf",
      "content": "base64-encoded-content",
      "content_type": "application/pdf"
    }
  ]
}
```

### Check Campaign Status
```json
GET /campaign-status/campaign_1234567890
{
  "campaign_id": "campaign_1234567890",
  "campaign_name": "Welcome Campaign",
  "status": "in_progress",
  "total_contacts": 100,
  "sent_count": 75,
  "failed_count": 5,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:05:00"
}
```

## Security Considerations

- Store SMTP credentials as Lambda environment variables
- Use IAM roles with minimal required permissions
- Enable API Gateway throttling and rate limiting
- Validate file uploads and size limits
- Implement authentication for production use

## Monitoring and Logging

- CloudWatch logs for Lambda execution
- DynamoDB metrics for table performance
- API Gateway access logs and metrics
- Campaign status tracking in DynamoDB

## Advantages

- **Serverless**: No server management required
- **Scalable**: Handles varying campaign sizes
- **Real-time**: Live progress tracking
- **Persistent**: Campaign history in DynamoDB
- **Flexible**: Works with any SMTP provider
- **Attachment Support**: Full file attachment capability