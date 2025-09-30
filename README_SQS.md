# 📨 AWS SQS Integration for Bulk Email System

This document explains the SQS-based architecture for processing bulk email campaigns asynchronously.

## 🏗️ Architecture Overview

```
User → Web UI → API Gateway → Lambda (Queue Handler)
                                    ↓
                              SQS Queue (bulk-email-queue)
                                    ↓
                         Lambda (Email Worker) ← Secrets Manager
                                    ↓
                              AWS SES / SMTP
```

### **How It Works:**

1. **User Clicks "Send Campaign"** → All contact emails are queued to SQS
2. **SQS Queue** → Holds all email jobs to be processed
3. **Worker Lambda** → Automatically triggered by SQS, processes emails in batches
4. **Email Delivery** → Worker sends emails via SES or SMTP
5. **Campaign Tracking** → DynamoDB tracks sent/failed counts

## ✨ Benefits of SQS Architecture

| Feature | Benefit |
|---------|---------|
| **Asynchronous Processing** | API responds immediately, no timeouts |
| **Scalability** | Handles thousands of emails efficiently |
| **Reliability** | Failed messages retry automatically |
| **Rate Limiting** | Natural throttling through batch processing |
| **Dead Letter Queue** | Captures permanently failed messages |
| **Monitoring** | Easy tracking via CloudWatch metrics |

## 🚀 Deployment Steps

### **Step 1: Create SQS Queue**

```bash
python create_sqs_queue.py
```

This creates:
- **bulk-email-queue** - Main queue for email processing
- **bulk-email-dlq** - Dead Letter Queue for failed messages

### **Step 2: Deploy Worker Lambda**

```bash
python deploy_email_worker.py
```

This will:
- Create IAM role with necessary permissions
- Deploy the email worker Lambda function
- Set up SQS trigger to invoke Lambda automatically
- Configure batch processing settings

### **Step 3: Update Main API Lambda**

```bash
python deploy_bulk_email_api.py
```

This updates your main API to queue messages to SQS instead of sending emails directly.

### **Step 4: Add SQS Permissions to API Lambda**

```bash
aws iam put-role-policy \
  --role-name bulk-email-api-lambda-role \
  --policy-name SQSAccess \
  --policy-document file://sqs_policy.json \
  --region us-gov-west-1
```

## 📋 Files Overview

| File | Purpose |
|------|---------|
| `create_sqs_queue.py` | Creates SQS queues |
| `email_worker_lambda.py` | Worker Lambda that sends emails |
| `deploy_email_worker.py` | Deploys worker Lambda |
| `sqs_policy.json` | IAM policy for SQS access |
| `bulk_email_api_lambda.py` | Updated to queue to SQS |

## 🔧 Configuration

### Queue Settings

**Main Queue (bulk-email-queue):**
- **Visibility Timeout**: 900 seconds (15 minutes)
- **Message Retention**: 4 days
- **Batch Size**: 10 messages per Lambda invocation
- **Max Receive Count**: 3 attempts before moving to DLQ

**Dead Letter Queue (bulk-email-dlq):**
- **Message Retention**: 14 days
- Stores messages that failed after 3 attempts

### Worker Lambda Settings

- **Memory**: 512 MB
- **Timeout**: 300 seconds (5 minutes)
- **Batch Size**: 10 emails per invocation
- **Batching Window**: 5 seconds

## 📊 Monitoring

### CloudWatch Metrics

**SQS Metrics:**
- `ApproximateNumberOfMessages` - Messages waiting in queue
- `NumberOfMessagesSent` - Total messages sent to queue
- `NumberOfMessagesDeleted` - Successfully processed messages
- `ApproximateNumberOfMessagesNotVisible` - Messages being processed

**Lambda Metrics:**
- `Invocations` - Number of times worker Lambda ran
- `Errors` - Failed Lambda executions
- `Duration` - Processing time per batch
- `ConcurrentExecutions` - Number of parallel workers

### CloudWatch Logs

**View Worker Lambda Logs:**
```bash
aws logs tail /aws/lambda/email-worker-function --follow --region us-gov-west-1
```

**View API Lambda Logs:**
```bash
aws logs tail /aws/lambda/bulk-email-api-function --follow --region us-gov-west-1
```

## 🔍 Message Format

Messages in the SQS queue contain:

```json
{
  "campaign_id": "campaign_1234567890",
  "campaign_name": "Monthly Newsletter",
  "subject": "Hello {{first_name}}!",
  "body": "Dear {{first_name}} {{last_name}}, ...",
  "contact": {
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme Corp"
  },
  "config": {
    "email_service": "ses",
    "from_email": "noreply@example.com",
    "aws_region": "us-gov-west-1",
    "aws_secret_name": "email-api-credentials"
  }
}
```

## 🐛 Troubleshooting

### Issue: Messages stuck in queue

**Check:**
1. Is worker Lambda enabled?
   ```bash
   aws lambda get-function --function-name email-worker-function --region us-gov-west-1
   ```

2. Check Lambda errors:
   ```bash
   aws logs tail /aws/lambda/email-worker-function --region us-gov-west-1
   ```

3. Check event source mapping:
   ```bash
   aws lambda list-event-source-mappings --function-name email-worker-function --region us-gov-west-1
   ```

### Issue: High failure rate

**Solutions:**
1. Check SES sending limits
2. Verify credentials in Secrets Manager
3. Check Dead Letter Queue for error patterns
4. Review CloudWatch logs for specific errors

### Issue: Slow processing

**Solutions:**
1. Increase Lambda concurrency limit
2. Increase batch size (up to 10)
3. Add more memory to Lambda (increases CPU)
4. Check for rate limiting from email provider

## 📈 Scaling Considerations

### Handling Large Campaigns

**For 10,000+ emails:**
1. SQS automatically scales
2. Lambda concurrency: Up to 1,000 concurrent executions
3. Processing rate: ~100-500 emails/minute (depending on batch size)
4. Cost: Pay only for what you use

### Rate Limiting

**Natural throttling:**
- Worker Lambda processes in batches
- Adjust batch size to control throughput
- SQS visibility timeout prevents duplicate sends
- Failed messages automatically retry

## 💰 Cost Estimation

**SQS Costs (us-gov-west-1):**
- First 1M requests/month: Free
- Additional requests: ~$0.40 per million

**Lambda Costs:**
- First 1M requests/month: Free
- Additional requests: $0.20 per million
- GB-seconds: Based on execution time

**Example: 10,000 email campaign**
- SQS requests: ~10,000 = $0.004
- Lambda invocations: ~1,000 = $0.0002
- **Total SQS+Lambda cost: < $0.01**

## ✅ Deployment Checklist

- [ ] SQS queues created (`create_sqs_queue.py`)
- [ ] Worker Lambda deployed (`deploy_email_worker.py`)
- [ ] API Lambda updated (`deploy_bulk_email_api.py`)
- [ ] SQS permissions added to API Lambda
- [ ] Secrets Manager configured
- [ ] Test campaign sent successfully
- [ ] CloudWatch logs reviewed
- [ ] Monitoring dashboards set up

## 🔄 Migration from Synchronous to SQS

**Before (Synchronous):**
- Lambda sends all emails directly
- 15-minute Lambda timeout limit
- Max ~900 emails per campaign
- User waits for completion

**After (SQS Architecture):**
- Lambda queues emails to SQS
- No timeout limits
- Unlimited campaign size
- Instant response to user
- Parallel processing

## 📝 Next Steps

1. **Deploy the SQS system** using the steps above
2. **Test with a small campaign** (5-10 contacts)
3. **Monitor CloudWatch** for successful processing
4. **Scale up gradually** to larger campaigns
5. **Set up alerts** for queue depth and errors

## 🆘 Support

- **CloudWatch Logs**: Primary debugging tool
- **SQS Console**: Monitor queue depth and messages
- **Lambda Console**: Check function metrics
- **DynamoDB**: Track campaign statistics

---

**Ready to deploy?** Start with:
```bash
python create_sqs_queue.py
python deploy_email_worker.py
```

🎉 Your asynchronous email system will be ready to handle campaigns of any size!
