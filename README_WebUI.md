# Web UI Bulk Email Sender with API Gateway

A serverless web-based bulk email sending solution using AWS API Gateway, Lambda, DynamoDB, and SES.

## Architecture

- **Web UI**: Modern HTML/CSS/JavaScript interface
- **API Gateway**: RESTful API endpoints with CORS support
- **Lambda Function**: Serverless backend processing
- **DynamoDB**: Contact storage with email tracking
- **SES**: Email delivery service

## Setup Instructions

### 1. Create DynamoDB Table
```bash
python dynamodb_table_setup.py
```

### 2. Deploy API Gateway and Lambda
1. Update `YOUR_ACCOUNT_ID` in `deploy_api_gateway.py`
2. Create IAM role: `lambda-email-sender-role`
3. Run: `python deploy_api_gateway.py`

### 3. Configure Web UI
1. Update `API_BASE_URL` in `web_ui.html` with your API Gateway URL
2. Host `web_ui.html` on any web server or S3 bucket

### 4. Verify SES Email
- Verify your sender email address in AWS SES console
- If in sandbox mode, verify recipient emails

## API Endpoints

### GET /contacts
Returns all contacts from DynamoDB
```json
{
  "contacts": [
    {
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "company": "Tech Corp",
      "last_email_sent": "2024-01-01T12:00:00",
      "email_count": 5
    }
  ],
  "count": 1
}
```

### POST /contacts
Add new contact to DynamoDB
```json
{
  "contact": {
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Tech Corp"
  }
}
```

### POST /campaign
Send email campaign to all contacts
```json
{
  "subject": "Welcome!",
  "body": "<h1>Hello {{first_name}}!</h1>",
  "from_email": "sender@example.com",
  "campaign_name": "Welcome Campaign"
}
```

## Web UI Features

### Contact Management
- Load contacts from DynamoDB
- Add individual contacts
- Import CSV files
- View email history and counts

### Email Templates
- HTML email editor
- Personalization placeholders
- Template preview
- Sample template loader

### Campaign Management
- Real-time progress tracking
- Campaign results display
- Email delivery status
- Error handling and reporting

## Personalization

Use these placeholders in your email templates:
- `{{first_name}}` - Contact's first name
- `{{last_name}}` - Contact's last name
- `{{email}}` - Contact's email address
- `{{company}}` - Contact's company

## Email Tracking

Each email sent automatically updates the contact record:
- `last_email_sent` - Timestamp of last email
- `last_campaign` - Name of last campaign
- `email_count` - Total emails sent to contact

## CORS Configuration

The API includes proper CORS headers for web browser access:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET,POST,OPTIONS`
- `Access-Control-Allow-Headers: Content-Type`

## Security Notes

- Use HTTPS for production deployment
- Consider API authentication for production use
- Implement rate limiting if needed
- Store AWS credentials securely
- Use least privilege IAM policies

## Hosting Options

### S3 Static Website
1. Upload `web_ui.html` to S3 bucket
2. Enable static website hosting
3. Configure bucket policy for public access

### CloudFront Distribution
1. Create CloudFront distribution
2. Point to S3 bucket or custom origin
3. Enable HTTPS with SSL certificate

### Local Development
Simply open `web_ui.html` in any modern web browser after updating the API URL.