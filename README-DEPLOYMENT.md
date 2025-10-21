# Bulk Email API - Deployment Guide

This guide explains how to deploy the Bulk Email API with the new `/log-csv-error` endpoint to AWS using SAM (Serverless Application Model).

## 📋 Prerequisites

1. **AWS Account** with GovCloud access (using `us-gov-west-1` region)
2. **AWS CLI** installed and configured:
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Key, and region (us-gov-west-1)
   ```
3. **AWS SAM CLI** installed:
   - [Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
   - Verify: `sam --version`

4. **Python 3.11+** (or adjust `Runtime` in `template.yaml`)

## 🚀 Quick Deployment

### Option 1: Using Deployment Scripts (Recommended)

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual Deployment

1. **Build the application:**
   ```bash
   sam build
   ```

2. **Deploy to AWS:**
   ```bash
   sam deploy --guided
   ```
   Follow the prompts:
   - Stack Name: `bulk-email-api`
   - AWS Region: `us-gov-west-1`
   - Confirm changes: `Y`
   - Allow SAM CLI IAM role creation: `Y`
   - Disable rollback: `n`
   - Save arguments to samconfig.toml: `Y`

3. **Subsequent deployments:**
   ```bash
   sam deploy
   ```

## 📦 What Gets Deployed

### AWS Resources Created:

1. **Lambda Functions:**
   - `BulkEmailApiFunction` - Main API handler (handles all endpoints including `/log-csv-error`)
   - `EmailWorkerFunction` - SQS consumer for sending emails

2. **API Gateway:**
   - REST API with all endpoints:
     - `POST /log-csv-error` - **NEW**: Log CSV parsing errors to CloudWatch
     - `POST /contacts/batch` - Batch upload contacts
     - `POST /campaign` - Send email campaigns
     - `GET /contacts` - List contacts
     - `GET /` - Web UI
     - *[15+ other endpoints defined in template.yaml]*

3. **DynamoDB Tables:**
   - `EmailContacts` - Stores contact information
   - `EmailCampaigns` - Stores campaign metadata

4. **S3 Bucket:**
   - Attachments storage with lifecycle policies

5. **SQS Queues:**
   - `email-queue` - Main processing queue
   - `email-dlq` - Dead letter queue

6. **CloudWatch:**
   - Log Groups for Lambda functions and API Gateway
   - Automatic logging enabled

## 🧪 Testing the New `/log-csv-error` Endpoint

After deployment, test the endpoint:

### Using curl:
```bash
# Get the endpoint URL from deployment output
API_URL="https://YOUR-API-ID.execute-api.us-gov-west-1.amazonaws.com/Prod"

curl -X POST $API_URL/log-csv-error \
  -H "Content-Type: application/json" \
  -d '{
    "row": 5,
    "error": "Column count mismatch (got 3, expected 4)",
    "rawLine": "john@example.com,John Doe,IT Director",
    "timestamp": "2025-10-21T12:00:00Z",
    "userAgent": "Mozilla/5.0..."
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "CSV error for row 5 logged to CloudWatch"
}
```

### Using PowerShell:
```powershell
$API_URL = "https://YOUR-API-ID.execute-api.us-gov-west-1.amazonaws.com/Prod"

Invoke-WebRequest -Method POST -Uri "$API_URL/log-csv-error" `
  -ContentType "application/json" `
  -Body '{"row": 5, "error": "Test error", "rawLine": "test,line,data"}'
```

## 📊 Viewing CloudWatch Logs

### View Lambda Logs:
```bash
# Real-time logs for the API function
aws logs tail /aws/lambda/bulk-email-api-BulkEmailApiFunction-* --follow --region us-gov-west-1

# Filter for CSV errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/bulk-email-api-BulkEmailApiFunction-* \
  --filter-pattern "CSV Parse Error" \
  --region us-gov-west-1
```

### In AWS Console:
1. Go to **CloudWatch** > **Log Groups**
2. Find `/aws/lambda/bulk-email-api-BulkEmailApiFunction-*`
3. Click on the latest log stream
4. Search for: `🚨 CSV Parse Error Logged`

You should see logs like:
```
🚨 CSV Parse Error Logged
   Row Number: 5
   Error: Column count mismatch (got 3, expected 4)
   Raw Line (first 500 chars): john@example.com,John Doe,IT Director
   User Agent: Mozilla/5.0...
   Timestamp: 2025-10-21T12:00:00Z
🔍 End CSV Error Log
```

## 🔧 Configuration

### Update Environment Variables:
Edit `template.yaml` under `BulkEmailApiFunction > Environment > Variables`:
```yaml
Environment:
  Variables:
    CONTACTS_TABLE: !Ref EmailContactsTable
    CUSTOM_DOMAIN: "yourdomain.com"  # Add custom settings
```

Then redeploy: `sam deploy`

### Update Lambda Timeout/Memory:
In `template.yaml` under `Globals > Function`:
```yaml
Timeout: 900  # Increase for large CSVs
MemorySize: 2048  # Increase for better performance
```

## 🌐 Frontend Integration

After deployment, update your frontend to use the new API URL:

1. **Get the API URL** from deployment output or:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name bulk-email-api \
     --region us-gov-west-1 \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
     --output text
   ```

2. **Update API_URL** in your frontend config (or it will auto-detect from `CUSTOM_API_URL` env var)

3. **The frontend code** (embedded in `bulk_email_api_lambda.py`) automatically POSTs CSV errors to `/log-csv-error` on parse failures

## 🗑️ Cleanup (Delete All Resources)

To remove all deployed resources:

```bash
sam delete --stack-name bulk-email-api --region us-gov-west-1
```

Or via AWS Console:
1. CloudFormation > Stacks > `bulk-email-api`
2. Click **Delete**

**Note:** The S3 bucket must be empty before deletion. Empty it manually if needed.

## 🔒 Security Considerations

1. **IAM Permissions**: The template creates minimal IAM roles. Review and restrict as needed.
2. **CORS**: Currently set to `*` (all origins). Update in `template.yaml` for production:
   ```yaml
   Cors:
     AllowOrigin: "'https://yourdomain.com'"
   ```
3. **API Keys**: Add API Gateway API keys for production:
   ```yaml
   Auth:
     ApiKeyRequired: true
   ```

## 📚 Additional Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [API Gateway Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## 🐛 Troubleshooting

### Issue: `sam: command not found`
**Solution:** Install AWS SAM CLI from the [official guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

### Issue: `Unable to locate credentials`
**Solution:** Run `aws configure` and enter your AWS credentials

### Issue: Deployment fails with "S3 bucket already exists"
**Solution:** The bucket name must be globally unique. Update `AttachmentsBucket` in `template.yaml`:
```yaml
BucketName: !Sub 'bulk-email-attachments-${AWS::AccountId}-${AWS::StackName}'
```

### Issue: 403 Forbidden on API calls
**Solution:** Check API Gateway CORS settings and Lambda IAM permissions

### Issue: CSV errors not appearing in CloudWatch
**Solution:** 
1. Check Lambda execution role has `logs:PutLogEvents` permission (auto-added by SAM)
2. Verify frontend is POSTing to the correct URL: `{API_URL}/log-csv-error`
3. Check Lambda function logs for execution errors

## 🎉 Success!

Once deployed, your CSV uploads will automatically log parsing errors to CloudWatch. You can:
- View detailed error messages with row numbers in CloudWatch Logs
- Track which rows failed and why
- Debug CSV format issues without crashing the upload process

The frontend will continue processing valid rows while logging problematic ones for investigation.

