# 📊 Updated Email Campaign Architecture

## Overview

The email campaign system has been updated to separate campaign data from queue messages, reducing SQS payload size and improving maintainability.

## 🔄 New Data Flow

```
User Clicks "Send Campaign"
         ↓
API Lambda saves campaign data to DynamoDB (EmailCampaigns table)
         ↓
API Lambda queues contact references to SQS (minimal payload)
         ↓
Worker Lambda triggered by SQS
         ↓
Worker retrieves campaign data from DynamoDB
         ↓
Worker retrieves contact data from DynamoDB
         ↓
Worker sends email via AWS SES
         ↓
Worker updates campaign statistics in DynamoDB
```

## 📦 Data Storage

### **DynamoDB - EmailCampaigns Table**
Stores complete campaign information:
```json
{
  "campaign_id": "campaign_1234567890",
  "campaign_name": "Monthly Newsletter",
  "subject": "Hello {{first_name}}!",
  "body": "Dear {{first_name}} {{last_name}}, ...",
  "from_email": "noreply@example.com",
  "email_service": "ses",
  "aws_region": "us-gov-west-1",
  "aws_secret_name": "email-api-credentials",
  "smtp_server": "",
  "smtp_port": 25,
  "status": "processing",
  "total_contacts": 100,
  "queued_count": 100,
  "sent_count": 0,
  "failed_count": 0,
  "created_at": "2024-01-01T00:00:00"
}
```

### **DynamoDB - EmailContacts Table**
Stores contact information:
```json
{
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company": "Acme Corp",
  "created_at": "2024-01-01T00:00:00"
}
```

### **SQS - bulk-email-queue**
Minimal message payload (only references):
```json
{
  "campaign_id": "campaign_1234567890",
  "contact_email": "john.doe@example.com"
}
```

## ✨ Benefits of New Architecture

| Feature | Before | After |
|---------|--------|-------|
| **SQS Message Size** | ~2-3 KB per message | ~100 bytes per message |
| **Campaign Updates** | Must requeue all messages | Update once in DynamoDB |
| **Data Consistency** | Multiple copies in SQS | Single source of truth |
| **Personalization** | Pre-processed | Real-time from DynamoDB |
| **Cost** | Higher SQS costs | Lower SQS costs |
| **Flexibility** | Fixed at queue time | Dynamic at send time |

## 🔍 How Worker Lambda Works

1. **Receives SQS Message**
   - Gets minimal payload: `campaign_id` and `contact_email`

2. **Retrieves Campaign Data**
   ```python
   campaign = campaigns_table.get_item(Key={'campaign_id': campaign_id})
   ```
   - Gets subject, body, sender email, configuration

3. **Retrieves Contact Data**
   ```python
   contact = contacts_table.get_item(Key={'email': contact_email})
   ```
   - Gets first name, last name, company

4. **Personalizes Content**
   ```python
   subject = subject.replace('{{first_name}}', contact['first_name'])
   body = body.replace('{{first_name}}', contact['first_name'])
   ```

5. **Sends Email**
   - Uses AWS SES with credentials from Secrets Manager
   - Credentials retrieved once per campaign

6. **Updates Statistics**
   ```python
   campaigns_table.update_item(
       Key={'campaign_id': campaign_id},
       UpdateExpression="SET sent_count = sent_count + :inc"
   )
   ```

## 📝 Key Changes Made

### **1. bulk_email_api_lambda.py**
- `send_campaign()` now saves complete campaign data to DynamoDB
- SQS messages only contain `campaign_id` and `contact_email`
- Reduced message size by ~95%

### **2. email_worker_lambda.py**
- Retrieves campaign data from DynamoDB on each invocation
- Retrieves contact data from DynamoDB for personalization
- Single source of truth for all data

### **3. DynamoDB Schema**
- `EmailCampaigns` table now stores all campaign fields
- Includes subject, body, sender email, configuration
- Status tracking: queued → processing → completed

## 🚀 Deployment Steps

1. **Deploy updated API Lambda:**
   ```bash
   python deploy_bulk_email_api.py
   ```

2. **Deploy updated Worker Lambda:**
   ```bash
   python deploy_email_worker.py
   ```

3. **Create SQS Queue (if not exists):**
   ```bash
   python create_sqs_queue.py
   ```

## 💡 Example Workflow

### **User Action:**
```
Campaign Name: "Monthly Newsletter"
Subject: "Hello {{first_name}}!"
Body: "Dear {{first_name}} {{last_name}}, welcome to {{company}}"
```

### **What Happens:**

1. **API Lambda saves to DynamoDB:**
   ```json
   {
     "campaign_id": "campaign_1704067200",
     "campaign_name": "Monthly Newsletter",
     "subject": "Hello {{first_name}}!",
     "body": "Dear {{first_name}} {{last_name}}, welcome to {{company}}",
     "from_email": "noreply@example.com",
     ...
   }
   ```

2. **API Lambda queues to SQS:**
   ```json
   {"campaign_id": "campaign_1704067200", "contact_email": "john@example.com"}
   {"campaign_id": "campaign_1704067200", "contact_email": "jane@example.com"}
   ...
   ```

3. **Worker Lambda processes each message:**
   - Retrieves campaign from DynamoDB
   - Retrieves contact from DynamoDB
   - Personalizes: "Hello John!" for john@example.com
   - Personalizes: "Hello Jane!" for jane@example.com
   - Sends via AWS SES
   - Updates sent_count in DynamoDB

## 📊 Performance Improvements

### **SQS Cost Reduction:**
- **Before**: 2 KB × 10,000 contacts = 20 MB
- **After**: 100 bytes × 10,000 contacts = 1 MB
- **Savings**: 95% reduction in SQS data transfer

### **Campaign Updates:**
- **Before**: Cannot update campaign after queueing
- **After**: Update campaign in DynamoDB, affects all pending sends

### **Data Consistency:**
- **Before**: Multiple copies of campaign data in SQS
- **After**: Single copy in DynamoDB, guaranteed consistency

## 🔐 Security

- ✅ AWS credentials stored in Secrets Manager (never in queue)
- ✅ Campaign data protected in DynamoDB
- ✅ Contact data protected in DynamoDB
- ✅ Minimal data exposure in SQS messages
- ✅ CloudWatch logging for audit trail

## 🐛 Troubleshooting

### **Campaign not found:**
```
Error: Campaign campaign_1234567890 not found in DynamoDB
```
**Solution:** Campaign data not saved properly. Check API Lambda logs.

### **Contact not found:**
```
Error: Contact john@example.com not found in DynamoDB
```
**Solution:** Contact was deleted after queueing. This is expected behavior.

### **SES credentials error:**
```
Error: No AWS secret name configured in campaign
```
**Solution:** Email configuration not saved properly. Check config in web UI.

## 📚 Related Files

- `bulk_email_api_lambda.py` - Main API with updated send_campaign()
- `email_worker_lambda.py` - Worker Lambda (completely rewritten)
- `deploy_email_worker.py` - Worker deployment script
- `README_SQS.md` - SQS architecture documentation

---

**Ready to deploy?** Run:
```bash
python deploy_bulk_email_api.py
python deploy_email_worker.py
```

🎉 Your optimized email campaign system is ready!
