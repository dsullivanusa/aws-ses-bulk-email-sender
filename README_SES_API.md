# AWS SES API Gateway Email Sender

Serverless AWS SES email sending solution with API Gateway, Lambda, DynamoDB, and full attachment support with real-time progress tracking.

## Architecture

- **API Gateway**: RESTful endpoints for SES email operations
- **Lambda Function**: SES email processing with attachments via raw email
- **DynamoDB**: Contact storage and campaign tracking
- **AWS SES**: Reliable email delivery service
- **Web UI**: Real-time progress monitoring interface

## Features

### SES Email Capabilities
- AWS SES integration for reliable delivery
- File attachments via SES raw email API
- HTML email templates with personalization
- Bulk campaign sending with progress tracking
- Automatic bounce and complaint handling

### Campaign Tracking
- Real-time progress monitoring
- Campaign status persistence in DynamoDB
- Contact email history updates
- Detailed sending results and error reporting

### API Endpoints

**POST /ses-campaign**
- Send bulk SES email campaign with attachments
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

### 1. AWS SES Configuration
```bash
# Verify sender email in SES console
aws ses verify-email-identity --email-address sender@domain.com

# Check verification status
aws ses get-identity-verification-attributes --identities sender@domain.com

# Request production access (if needed)
# Submit case in AWS Support Center to move out of sandbox
```

### 2. Create DynamoDB Tables
```bash
python dynamodb_table_setup.py      # EmailContacts table
python dynamodb_campaigns_table.py  # EmailCampaigns table
```

### 3. Deploy API Gateway and Lambda
1. Update `YOUR_ACCOUNT_ID` in `deploy_ses_api_gateway.py`
2. Create IAM role with `ses_iam_policy.json`
3. Run: `python deploy_ses_api_gateway.py`

### 4. Configure Web UI
1. Update `API_BASE_URL` in `ses_web_ui_api.html`
2. Host web UI on S3 or web server

## SES Requirements

### Email Verification
- **Sender Email**: Must be verified in SES console
- **Sandbox Mode**: Recipient emails must also be verified
- **Production Mode**: Can send to any email address

### Sending Limits
- **Sandbox**: 200 emails/day, 1 email/second
- **Production**: Higher limits based on reputation
- **Rate Limiting**: Automatic throttling in Lambda

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

### SES Raw Email API
- Uses `send_raw_email` for attachment support
- MIME multipart message construction
- Base64 encoding for binary files
- Proper Content-Disposition headers

### File Processing
- Web UI converts files to base64
- Lambda decodes and creates MIME parts
- Attachments embedded in email message
- Supports any file type and size (within limits)

### Size Limits
- **API Gateway**: 10MB payload limit
- **SES**: 10MB per email (including attachments)
- **Lambda**: 6MB synchronous payload

## Real-Time Progress Tracking

### Campaign Status Flow
1. **Pending**: Campaign created, not started
2. **In Progress**: Emails being sent via SES
3. **Completed**: All emails processed
4. **Failed**: Campaign encountered errors

### Progress Updates
- DynamoDB updated after each SES send
- Web UI polls campaign status every 2 seconds
- Real-time progress bar and counters
- Contact records updated with send timestamps

## API Request Examples

### Send SES Campaign with Attachments
```json
POST /ses-campaign
{
  "subject": "Welcome {{first_name}}!",
  "body": "<h1>Hello {{first_name}}</h1>",
  "campaign_name": "SES Welcome Campaign",
  "from_email": "verified-sender@domain.com",
  "attachments": [
    {
      "filename": "welcome.pdf",
      "content": "base64-encoded-content",
      "content_type": "application/pdf"
    }
  ]
}
```

### Check Campaign Status
```json
GET /campaign-status/ses_campaign_1234567890
{
  "campaign_id": "ses_campaign_1234567890",
  "campaign_name": "SES Welcome Campaign",
  "status": "completed",
  "total_contacts": 100,
  "sent_count": 98,
  "failed_count": 2,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:10:00"
}
```

## SES Advantages

- **High Deliverability**: AWS reputation and infrastructure
- **Bounce Handling**: Automatic bounce and complaint processing
- **Analytics**: Built-in sending statistics and metrics
- **Scalability**: Handles large volume campaigns
- **Reliability**: 99.9% uptime SLA
- **Cost Effective**: $0.10 per 1,000 emails

## Monitoring and Compliance

### CloudWatch Metrics
- Email sending rates and volumes
- Bounce and complaint rates
- Lambda execution metrics
- API Gateway request metrics

### Compliance Features
- Automatic unsubscribe handling
- Bounce and complaint tracking
- DKIM signing support
- SPF and DMARC compatibility

## Security Considerations

- IAM roles with minimal SES permissions
- API Gateway throttling and rate limiting
- Email content validation and sanitization
- Attachment size and type restrictions
- Sender email verification requirements

## Troubleshooting

### Common Issues

**Email Not Delivered:**
- Check sender email verification
- Verify recipient email (sandbox mode)
- Check SES sending statistics for bounces

**Attachment Too Large:**
- SES limit: 10MB per email
- Compress files or split into multiple emails
- Use cloud storage links for large files

**Rate Limit Exceeded:**
- Check SES sending quotas
- Implement exponential backoff
- Request limit increase from AWS

**Lambda Timeout:**
- Increase timeout for large campaigns
- Implement batch processing
- Use Step Functions for very large campaigns