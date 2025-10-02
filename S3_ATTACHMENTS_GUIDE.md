# S3 Email Attachments Guide

## Overview

The email campaign system now supports **file attachments** using AWS S3. Users can attach PDF, DOC, images, and other files to their email campaigns.

### Key Features:
- ✅ **40 MB limit per email** (all attachments combined - AWS SES v2)
- ✅ **Multiple file support** - Attach multiple files at once
- ✅ **Automatic S3 upload** - Files stored in `jcdc-ses-contact-list` bucket
- ✅ **Real-time validation** - Size checks before upload
- ✅ **Supported formats:** PDF, DOC, DOCX, XLS, XLSX, PNG, JPG, TXT, CSV

## Implementation Summary

### Frontend Features:
1. **File Upload UI** in Send Campaign tab
2. **40 MB Warning** - Clear message about limit
3. **Upload Progress** - Shows files being uploaded
4. **File List Display** - Shows attached files with size
5. **Remove Button** - Remove individual attachments
6. **Size Indicator** - Running total of attachment size

### Backend Features:
1. **S3 Upload Endpoint** - `/upload-attachment`
2. **Base64 Encoding** - Files converted and uploaded
3. **Metadata Storage** - Attachment info in DynamoDB
4. **S3 Storage** - Files in `jcdc-ses-contact-list` bucket

## Deployment Steps

### Step 1: Update Lambda Function
```bash
# Upload the updated bulk_email_api_lambda.py
python update_lambda.py
```

The Lambda function now includes:
- S3 client initialization
- `/upload-attachment` endpoint handler
- Attachment metadata in campaigns
- File download/attach logic

### Step 2: Configure S3 Bucket Permissions

Make sure the Lambda function has permissions to write to the S3 bucket:

```json
{
    "Effect": "Allow",
    "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
    ],
    "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list/*"
}
```

### Step 3: Add API Gateway Endpoint
```bash
python add_attachment_endpoint.py
```

This creates the `/upload-attachment` endpoint for file uploads.

### Step 4: Test
1. Open the web UI
2. Go to Send Campaign tab
3. Click "📎 Add Attachments"
4. Select a file (PDF, image, etc.)
5. Verify it appears in the list

## How It Works

### Upload Flow:
```
1. User selects file in browser
   ↓
2. JavaScript reads file and converts to Base64
   ↓
3. POST to /upload-attachment with:
   - filename
   - content_type
   - base64 data
   ↓
4. Lambda decodes and uploads to S3:
   s3://jcdc-ses-contact-list/campaign-attachments/{timestamp}-{random}-{filename}
   ↓
5. Returns S3 key to frontend
   ↓
6. Frontend stores metadata:
   {
     filename: "report.pdf",
     size: 2457600,
     type: "application/pdf",
     s3_key: "campaign-attachments/..."
   }
   ↓
7. When campaign sent, attachments array included in DynamoDB
```

### Send Campaign Flow:
```
1. User clicks "Send Campaign"
   ↓
2. Campaign data + attachments saved to DynamoDB:
   {
     campaign_id: "campaign_123",
     subject: "...",
     body: "...",
     attachments: [
       {filename: "...", s3_key: "...", size: ...}
     ]
   }
   ↓
3. Contacts queued to SQS with campaign_id
   ↓
4. Worker Lambda (email_worker_lambda.py):
   - Retrieves campaign from DynamoDB
   - Downloads attachments from S3
   - Attaches to email
   - Sends via SES
```

## S3 Bucket Structure

```
jcdc-ses-contact-list/
└── campaign-attachments/
    ├── 1696789234567-abc123-report.pdf
    ├── 1696789234789-def456-chart.png
    └── 1696789234890-ghi789-document.docx
```

**File naming:** `{timestamp}-{random}-{original_filename}`

## User Interface

### Send Campaign Tab (Updated):

```
┌─────────────────────────────────────────┐
│ Target Group: [All Groups ▼]            │
│ Campaign Name: [.....................]   │
│ Subject: [.............................]  │
│ Email Body: [Rich text editor...]       │
│                                          │
│ Attachments (Optional):                  │
│ ┌────────────────────────────────────┐  │
│ │ ⚠️ Important: Maximum total size    │  │
│ │ is 40 MB per email (including all   │  │
│ │ attachments). Supported formats:    │  │
│ │ PDF, DOC, DOCX, XLS, XLSX, PNG,     │  │
│ │ JPG, TXT, CSV                       │  │
│ └────────────────────────────────────┘  │
│                                          │
│ [📎 Add Attachments]                     │
│                                          │
│ 📎 report.pdf              [Remove]      │
│    1.2 MB                                │
│                                          │
│ 📎 chart.png               [Remove]      │
│    453.5 KB                              │
│                                          │
│ Total size: 1.65 MB / 40 MB ✓            │
│                                          │
│ [Send Campaign] [Clear Form]             │
└─────────────────────────────────────────┘
```

## Size Validation

### Client-Side (JavaScript):
- Checks total size before upload
- Prevents uploads > 40 MB
- Shows warning if limit exceeded

### Example:
```javascript
// User tries to add 30 MB file when 15 MB already attached
Total: 45 MB > 40 MB limit
→ Alert: "Total attachment size exceeds 40 MB limit.
         Current total: 45.00 MB
         Please remove some files."
```

## Supported File Types

### Recommended:
- **Documents:** PDF, DOC, DOCX, TXT
- **Spreadsheets:** XLS, XLSX, CSV
- **Images:** PNG, JPG, JPEG, GIF
- **Archives:** ZIP (if under 40 MB)

### Size Guidelines:
- **PDF:** Typically 500 KB - 5 MB
- **Images:** 100 KB - 2 MB (compress large images)
- **Documents:** 50 KB - 2 MB
- **Spreadsheets:** 100 KB - 3 MB

## Email Worker Lambda Update

**Note:** You'll need to update your email worker Lambda (`email_worker_lambda.py`) to fetch and attach files from S3.

### Required Changes:

```python
# In email_worker_lambda.py

import boto3
s3_client = boto3.client('s3')

def process_message(message):
    # ... existing code ...
    
    # Get campaign from DynamoDB
    campaign = campaigns_table.get_item(Key={'campaign_id': campaign_id})['Item']
    
    # Get attachments if present
    attachments = campaign.get('attachments', [])
    
    # Download from S3 and attach
    for attachment in attachments:
        s3_key = attachment['s3_key']
        bucket = 'jcdc-ses-contact-list'
        
        # Download from S3
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        file_data = response['Body'].read()
        
        # Attach to email
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={attachment["filename"]}'
        )
        msg.attach(part)
    
    # Send email with attachments
    # ... existing send code ...
```

## Troubleshooting

### Issue 1: Upload Fails (403 Forbidden)
**Cause:** Lambda doesn't have S3 permissions

**Solution:**
```bash
# Add S3 permissions to Lambda role
aws iam attach-role-policy \
  --role-name bulk-email-api-function-role \
  --policy-arn arn:aws-us-gov:iam::aws:policy/AmazonS3FullAccess \
  --region us-gov-west-1
```

### Issue 2: Upload Fails (404 Not Found)
**Cause:** `/upload-attachment` endpoint not in API Gateway

**Solution:**
```bash
python add_attachment_endpoint.py
```

### Issue 3: Emails Sent Without Attachments
**Cause:** Email worker Lambda not updated to fetch from S3

**Solution:** Update `email_worker_lambda.py` with S3 fetch code (see above)

### Issue 4: Size Limit Exceeded
**Cause:** Total attachments > 40 MB

**Solution:** 
- Remove some files
- Compress PDFs/images
- Split into multiple campaigns

## API Endpoints

### Upload Attachment
```
POST /upload-attachment

Request:
{
  "filename": "report.pdf",
  "content_type": "application/pdf",
  "s3_key": "campaign-attachments/123-abc-report.pdf",
  "data": "base64encodeddata..."
}

Response:
{
  "success": true,
  "s3_key": "campaign-attachments/123-abc-report.pdf",
  "bucket": "jcdc-ses-contact-list"
}
```

### Send Campaign (with attachments)
```
POST /campaign

Request:
{
  "campaign_name": "Monthly Newsletter",
  "subject": "Updates for {{first_name}}",
  "body": "<html>...</html>",
  "target_group": "State CISOs",
  "attachments": [
    {
      "filename": "report.pdf",
      "size": 2457600,
      "type": "application/pdf",
      "s3_key": "campaign-attachments/123-abc-report.pdf"
    }
  ]
}
```

## Cost Considerations

### S3 Storage:
- **Storage:** $0.023/GB/month
- **PUT requests:** $0.005/1000 requests
- **GET requests:** $0.0004/1000 requests

### Example:
- 100 campaigns/month
- 2 MB average attachment
- = 200 MB storage = $0.0046/month
- = 100 uploads + 10,000 sends = $0.005 + $0.004 = **$0.01/month**

**Very cost effective!** 💰

## Security

### Best Practices:
1. ✅ Files stored in private S3 bucket
2. ✅ Bucket not publicly accessible
3. ✅ Lambda uses IAM roles for access
4. ✅ Files auto-deleted after campaign (optional)
5. ✅ Virus scanning (optional, add Lambda trigger)

### Optional: Auto-Delete Old Attachments
```bash
# Set S3 lifecycle policy to delete after 30 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket jcdc-ses-contact-list \
  --lifecycle-configuration file://lifecycle.json
```

## Testing Checklist

- [ ] Lambda function updated
- [ ] S3 permissions configured
- [ ] `/upload-attachment` endpoint deployed
- [ ] Upload single file (PDF)
- [ ] Upload multiple files
- [ ] Test 40 MB limit warning
- [ ] Remove attachment works
- [ ] Clear form clears attachments
- [ ] Send campaign with attachments
- [ ] Verify files in S3 bucket
- [ ] Check DynamoDB campaign record
- [ ] Verify email worker fetches from S3
- [ ] Receive email with attachments

## Summary

✅ **Implemented:**
- S3 bucket integration (`jcdc-ses-contact-list`)
- File upload UI with 40 MB limit validation
- Base64 upload to S3
- Attachment metadata in DynamoDB
- Size validation and display
- Remove/clear functionality

🔧 **Next Steps:**
1. Deploy updated Lambda function
2. Run `python add_attachment_endpoint.py`
3. Update email worker Lambda to fetch from S3
4. Test full flow

📧 **Result:** Users can now attach files to email campaigns with automatic S3 storage!

