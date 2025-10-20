# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A serverless bulk email campaign management system built on AWS GovCloud using SES, Lambda, API Gateway, SQS, and DynamoDB. Features a modern web UI with rich text editing, contact management, campaign tracking, and adaptive rate control for high-volume email sending.

## Architecture

### Core Components

**Frontend:**
- `preview_bulk_ui.html` - Single-page web application with tabbed interface
  - Rich text email editor using Quill.js
  - Contact management with CSV import/export
  - Campaign creation and monitoring
  - Email preview with personalization
  - Served directly from the API Lambda function

**Backend Lambda Functions:**
- `bulk_email_api_lambda.py` - Main API Lambda (API Gateway proxy)
  - Handles all HTTP endpoints (contacts, campaigns, config, attachments)
  - Serves the web UI HTML
  - Queues emails to SQS for processing
  - Manages campaign metadata

- `email_worker_lambda.py` - Background email processor (SQS-triggered)
  - Processes individual email messages from SQS queue
  - Sends emails via SES with personalization
  - Implements adaptive rate control based on attachment size
  - Updates campaign progress in DynamoDB
  - Handles CC/BCC addressing with role-based logic

**Data Layer (DynamoDB):**
- `EmailContacts` - Contact database (partition key: email)
- `EmailCampaigns` - Campaign tracking and templates
- `EmailConfig` - Email service configuration (SES/SMTP credentials)

**Queue:**
- `bulk-email-queue` (SQS) - Message queue for email processing
  - Each recipient gets a separate message
  - Messages include `role` field for CC/BCC handling ('cc', 'bcc', 'to', or none)
  - CC/BCC recipients are queued as individual messages with role identifiers

**Storage:**
- S3 bucket `jcdc-ses-contact-list` - Email attachments and config files

### Data Flow

1. **Campaign Creation:** User creates campaign in web UI → API Lambda stores in `EmailCampaigns` table
2. **Email Queuing:** API Lambda creates individual SQS messages for each recipient (including separate messages for CC/BCC with role identifiers)
3. **Email Processing:** SQS triggers Email Worker Lambda for each message → Worker retrieves campaign data → Sends via SES → Updates progress
4. **Progress Tracking:** Web UI polls API Lambda for campaign status from DynamoDB

### Key Design Patterns

**CC/BCC Handling:**
- Each CC/BCC recipient gets a separate SQS message with `role` field set to 'cc' or 'bcc'
- Email Worker detects role and adjusts headers accordingly
- CC recipients: appear in CC field, sender in To field
- BCC recipients: appear in BCC field (hidden), sender in To field
- Regular contacts: receive campaign CC/BCC in headers

**Adaptive Rate Control:**
- Base delay configurable via environment variables
- Automatically adjusts send rate based on attachment sizes
- Throttle detection and exponential backoff
- CloudWatch metrics for monitoring

**Personalization:**
- Template placeholders: `{{first_name}}`, `{{last_name}}`, `{{email}}`, `{{company}}`
- Applied by Email Worker before sending

**Error Handling:**
- Email Worker catches all exceptions to prevent SQS message redelivery
- CloudWatch alarms monitor error rates via log metric filters
- Custom CloudWatch metrics in `EmailWorker/Custom` namespace

## AWS Region

**CRITICAL:** This system is deployed to **AWS GovCloud US West (us-gov-west-1)**. All boto3 clients are hardcoded to this region. When modifying code, ensure region consistency across:
- DynamoDB clients
- SES clients
- S3 clients (with signature_version='s3v4' config)
- SQS clients
- Secrets Manager clients

## Development Commands

### Deployment

**One-command full deployment:**
```bash
python deploy_complete.py
```

**Deploy individual components:**
```bash
# Create DynamoDB tables
python dynamodb_table_setup.py           # EmailContacts table
python dynamodb_campaigns_table.py       # EmailCampaigns table
python create_email_config_table.py      # EmailConfig table

# Create SQS queue
python create_sqs_queue.py

# Deploy Lambda functions
python deploy_bulk_email_api.py          # API Lambda + API Gateway
python deploy_email_worker.py            # Email Worker Lambda

# Setup email credentials in AWS Secrets Manager
python setup_email_credentials_secret.py create
```

### Testing and Diagnostics

**Monitor campaigns:**
```bash
python campaign_monitor.py               # Real-time campaign progress
python tail_lambda_logs.py               # Stream Lambda logs
```

**Diagnose errors:**
```bash
python diagnose_emailworker_errors.py 24 <function-name>   # Check worker errors (last 24 hours)
python find_cloudwatch_error_metrics.py  # Locate error metric sources
python view_lambda_errors.py             # View recent Lambda errors
python check_sqs_status.py               # Check SQS queue status
```

**Test email functionality:**
```bash
python test_email_worker_cc_bcc.py       # Test CC/BCC handling
python test_cc_duplication_fix_final.py  # Verify CC duplication fix
```

**Local GUI (desktop mode):**
```bash
python bulk_email_sender.py              # Tkinter GUI for local campaigns
```

### CloudWatch Monitoring

**Setup alarms:**
```bash
python cloudwatch_alarms_setup.py        # Create monitoring alarms
python configure_alarm_notifications.py  # Setup SNS notifications
python view_alarm_status.py              # Check alarm states
```

**Common metrics to monitor:**
- `AWS/Lambda/Errors` - Lambda function failures
- `EmailWorker/Custom/ThrottleExceptions` - SES rate limiting
- `EmailWorker/Custom/EmailsFailed` - Failed sends
- `EmailWorker/Custom/FailureRate` - Failure percentage

## Common Development Tasks

### Adding a New Contact Field

1. Update DynamoDB schema if needed (tables are schemaless but consider defaults)
2. Update web UI form in `preview_bulk_ui.html`
3. Update API Lambda handlers in `bulk_email_api_lambda.py`
4. Update Email Worker if field is used in personalization (`email_worker_lambda.py`)
5. Update CSV import/export logic

### Modifying Email Templates

- Templates stored in `EmailCampaigns` DynamoDB table with campaign metadata
- HTML content should be inline-styled (no external CSS) for email client compatibility
- Quill editor in web UI generates HTML automatically
- Preview endpoint: `/preview` (POST with campaign_id)

### Adding New API Endpoints

1. Add handler in `bulk_email_api_lambda.py` in the main `lambda_handler()` function
2. Check `httpMethod` and `path` to route requests
3. Return responses with CORS headers (already configured)
4. Update web UI JavaScript to call new endpoint
5. Deploy with `python deploy_bulk_email_api.py`

### Adjusting Send Rate

**Environment variables for Email Worker Lambda:**
- `BASE_DELAY_SECONDS` - Base delay between emails (default: 0.1)
- `MAX_DELAY_SECONDS` - Maximum delay allowed (default: 5.0)
- `MIN_DELAY_SECONDS` - Minimum delay allowed (default: 0.01)

**Update via AWS Console or CLI:**
```bash
aws lambda update-function-configuration \
  --function-name email-worker-function \
  --environment "Variables={BASE_DELAY_SECONDS=0.5}" \
  --region us-gov-west-1
```

## Important Conventions

### JSON Serialization
- DynamoDB returns `Decimal` objects which aren't JSON-serializable
- Always use `convert_decimals()` helper function before returning JSON responses
- Helper function recursively converts Decimals to int/float

### Email Addressing
- SES requires verified sender identities (sandbox mode requires verified recipients too)
- Validate email addresses before queuing to avoid SES validation errors
- CC/BCC recipients must be queued as separate SQS messages with `role` field

### Error Handling in Email Worker
- **CRITICAL:** Email Worker catches ALL exceptions to prevent SQS message redelivery
- This means Lambda always returns success (200) even on errors
- Errors are logged to CloudWatch and tracked via custom metrics
- Alarms likely use log metric filters on ERROR patterns, not Lambda's built-in error metric

### API Gateway Integration
- Uses Lambda Proxy integration (event contains `httpMethod`, `path`, `body`, `pathParameters`)
- Always include CORS headers in responses
- HTML is served inline from Lambda, not from S3

### Configuration Management
- Credentials stored in AWS Secrets Manager (never hardcoded)
- Use `secrets_client.get_secret_value()` to retrieve
- Custom API URL can be set via `CUSTOM_API_URL` environment variable

## File Organization

**Deployment Scripts:**
- `deploy_*.py` - Various deployment utilities
- `create_*.py` - Resource creation scripts
- `setup_*.py` - Configuration scripts

**Lambda Functions:**
- `*_lambda.py` - Lambda function handlers
- Always package as `lambda_function.py` in deployment zip

**Diagnostics:**
- `diagnose_*.py` - Troubleshooting utilities
- `test_*.py` - Test scripts
- `check_*.py` - Status checking utilities
- `fix_*.py` - Automated fix scripts

**Documentation:**
- Extensive markdown docs for specific features and fixes
- See `deployment_readiness_report.md` for production status
- See `CLOUDWATCH_ERROR_METRICS_EXPLAINED.md` for error metric details

## Known Issues and Fixes

**CC Duplication:** Fixed - CC recipients are now excluded from regular contact processing to prevent duplicate emails

**Font Compatibility:** System uses Outlook-optimized fonts with 13 professional options (web fonts with fallbacks)

**403 Errors:** Usually DynamoDB permissions - run `python fix_403_permissions.py`

**SES Throttling:** Adaptive rate control automatically adjusts send rate

**CloudWatch Alarms Triggering:** Usually from log metric filters on ERROR patterns, not actual Lambda failures - use `diagnose_emailworker_errors.py` to investigate

## Testing

**No automated unit tests included.** Manual testing workflow:

1. **Test API endpoints:**
   - Open web UI in browser
   - Test contact CRUD operations
   - Upload CSV contacts
   - Create and preview campaign

2. **Test email sending:**
   - Send small test campaign (3-5 contacts)
   - Monitor CloudWatch logs with `tail_lambda_logs.py`
   - Verify emails received with correct headers
   - Check campaign progress updates

3. **Test CC/BCC:**
   - Use `test_email_worker_cc_bcc.py`
   - Verify CC recipients see correct headers
   - Verify BCC recipients remain hidden

4. **Load testing:**
   - Use `generate_test_contacts.py` to create test data
   - Monitor SQS queue depth
   - Watch for throttling metrics

## Security Considerations

- Never commit AWS credentials to git (`config.json` is gitignored)
- Use IAM roles with least privilege
- Verify all sender and recipient addresses in SES before production use
- Attachments stored in S3 with KMS encryption (requires signature v4)
- Consider enabling Cognito authentication (currently disabled but code present)

## Quick Reference

**API Endpoints (from bulk_email_api_lambda.py):**
- `GET /` - Serve web UI
- `GET /contacts` - List all contacts
- `POST /contacts` - Add contact
- `PUT /contacts/{email}` - Update contact
- `DELETE /contacts/{email}` - Delete contact
- `POST /campaign` - Create and send campaign
- `GET /campaigns` - List campaigns
- `GET /campaigns/{campaign_id}` - Get campaign details
- `POST /config` - Save email configuration
- `GET /config` - Get email configuration
- `POST /preview` - Preview email with personalization
- `POST /upload` - Upload attachment to S3
- `GET /attachments` - List attachments

**DynamoDB Tables:**
- EmailContacts (PK: email)
- EmailCampaigns (PK: campaign_id)
- EmailConfig (PK: config_id)

**Key Environment Variables:**
- `CUSTOM_API_URL` - Override default API Gateway URL
- `BASE_DELAY_SECONDS` - Email send rate control
- `MAX_DELAY_SECONDS` - Maximum send delay
- `MIN_DELAY_SECONDS` - Minimum send delay
