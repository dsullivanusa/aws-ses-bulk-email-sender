# ⚡ SQS Integration - Quick Start

## 🎯 What Changed?

Your bulk email system now uses **AWS SQS** for asynchronous email processing!

**Before:** Emails sent directly (slow, limited by Lambda timeout)  
**After:** Emails queued to SQS and processed by worker Lambda (fast, unlimited scale)

## 🚀 Setup in 3 Steps

### **Step 1: Create SQS Queue**
```bash
python create_sqs_queue.py
```
Creates: `bulk-email-queue` and `bulk-email-dlq` (Dead Letter Queue)

### **Step 2: Deploy Worker Lambda**
```bash
python deploy_email_worker.py
```
Deploys: Lambda function that processes emails from SQS

### **Step 3: Update & Redeploy API**
```bash
python deploy_bulk_email_api.py
```
Updates: Main API to queue emails to SQS

## ✅ That's It!

Your system is now ready to handle campaigns of any size!

## 🔍 How It Works

1. User clicks **🚀 Send Campaign**
2. API queues all contact emails to SQS instantly
3. Worker Lambda automatically processes emails from queue
4. Emails sent via SES/SMTP asynchronously
5. Campaign stats updated in DynamoDB

## 📊 New Web UI Response

After clicking Send Campaign, users now see:
- **Queued to SQS**: Number of emails successfully queued
- **Failed to Queue**: Any emails that couldn't be queued
- **Total Contacts**: Total recipients
- **Campaign ID**: Track your campaign
- **Queue Name**: `bulk-email-queue`

## 🔧 Additional Files

| File | Purpose |
|------|---------|
| `create_sqs_queue.py` | ✅ Creates SQS queues |
| `email_worker_lambda.py` | ✅ Worker Lambda code |
| `deploy_email_worker.py` | ✅ Deploys worker |
| `sqs_policy.json` | ✅ IAM policy |
| `README_SQS.md` | 📚 Full documentation |

## 🎁 Benefits

✅ **No Timeout Limits** - Handle unlimited emails  
✅ **Instant Response** - User doesn't wait for completion  
✅ **Auto Scaling** - SQS and Lambda scale automatically  
✅ **Reliability** - Failed emails retry automatically  
✅ **Monitoring** - Track everything in CloudWatch  
✅ **Cost Effective** - Pay only for what you use

## 🐛 Troubleshooting

**Queue not found?**
```bash
python create_sqs_queue.py
```

**Emails not sending?**
```bash
# Check worker logs
aws logs tail /aws/lambda/email-worker-function --follow --region us-gov-west-1
```

**Add SQS permissions manually:**
```bash
aws iam attach-role-policy \
  --role-name bulk-email-api-lambda-role \
  --policy-arn arn:aws-us-gov:iam::aws:policy/AmazonSQSFullAccess \
  --region us-gov-west-1
```

## 📖 Full Documentation

See [README_SQS.md](README_SQS.md) for complete details on:
- Architecture diagrams
- Monitoring and metrics
- Cost estimation
- Advanced configuration
- Scaling considerations

---

**Ready?** Just run:
```bash
python create_sqs_queue.py
python deploy_email_worker.py
python deploy_bulk_email_api.py
```

🎉 Your asynchronous email system is ready!
