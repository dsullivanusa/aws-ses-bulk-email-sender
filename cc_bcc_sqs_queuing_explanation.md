# CC and BCC SQS Queuing Explanation

## ✅ **YES - CC and BCC Recipients are Queued as Separate SQS Messages**

Each email address in the CC and BCC lines is queued as a **separate SQS message** with a specific role identifier.

## 📍 **How It Works**

### **1. Regular Contacts (No Role)**
```json
{
  "campaign_id": "camp-123",
  "contact_email": "user@example.com"
  // No "role" field = regular contact
}
```

### **2. CC Recipients (Role: 'cc')**
```json
{
  "campaign_id": "camp-123", 
  "contact_email": "cc@example.com",
  "role": "cc"
}
```

### **3. BCC Recipients (Role: 'bcc')**
```json
{
  "campaign_id": "camp-123",
  "contact_email": "bcc@example.com", 
  "role": "bcc"
}
```

### **4. To Recipients (Role: 'to')**
```json
{
  "campaign_id": "camp-123",
  "contact_email": "to@example.com",
  "role": "to"
}
```

## 🔄 **Queuing Process**

### **Location**: `bulk_email_api_lambda.py` - `send_campaign()` function

```python
# 1. Queue regular contacts (no role)
for contact in contacts:
    message_body = {
        'campaign_id': campaign_id,
        'contact_email': contact.get('email')
        # No role = regular contact
    }
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

# 2. Queue CC addresses (single-send each)
for cc in cc_list:
    enqueue_special(cc, 'cc')  # Creates message with role='cc'

# 3. Queue BCC addresses (single-send each)  
for bcc in bcc_list:
    enqueue_special(bcc, 'bcc')  # Creates message with role='bcc'

# 4. Queue To addresses (single-send each)
for to_addr in to_list:
    enqueue_special(to_addr, 'to')  # Creates message with role='to'
```

### **The `enqueue_special()` Function**:
```python
def enqueue_special(recipient_email, role):
    special_message = {
        'campaign_id': campaign_id,
        'contact_email': recipient_email,
        'role': role  # 'cc', 'bcc', or 'to'
    }
    
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(special_message),
        MessageAttributes={
            'campaign_id': {'StringValue': campaign_id, 'DataType': 'String'},
            'contact_email': {'StringValue': recipient_email, 'DataType': 'String'},
            'role': {'StringValue': role, 'DataType': 'String'}
        }
    )
```

## 📊 **Example Scenario**

**Campaign Setup:**
- Target Contacts: `['user1@example.com', 'user2@example.com']`
- CC: `['cc1@example.com', 'cc2@example.com']`
- BCC: `['bcc@example.com']`

**SQS Messages Created:**
```
Message 1: {"campaign_id": "camp-123", "contact_email": "user1@example.com"}
Message 2: {"campaign_id": "camp-123", "contact_email": "user2@example.com"}
Message 3: {"campaign_id": "camp-123", "contact_email": "cc1@example.com", "role": "cc"}
Message 4: {"campaign_id": "camp-123", "contact_email": "cc2@example.com", "role": "cc"}
Message 5: {"campaign_id": "camp-123", "contact_email": "bcc@example.com", "role": "bcc"}
```

**Total SQS Messages: 5**

## 🎯 **How Email Worker Processes These Messages**

### **Location**: `email_worker_lambda.py` - `lambda_handler()` function

```python
# Each SQS message is processed individually
message = json.loads(record['body'])
campaign_id = message.get('campaign_id')
contact_email = message.get('contact_email')
role = message.get('role')  # None, 'cc', 'bcc', or 'to'

if role == 'cc':
    # CC recipient: they appear in CC field, sender in To field
    cc_list = [contact_email]
    contact_email_for_sending = from_email
    
elif role == 'bcc':
    # BCC recipient: they appear in BCC field, sender in To field
    bcc_list = [contact_email]
    contact_email_for_sending = from_email
    
else:
    # Regular contact: they're in To field, campaign CC/BCC in headers
    cc_list = campaign.get('cc', [])
    bcc_list = campaign.get('bcc', [])
    contact_email_for_sending = contact_email
```

## ✅ **Benefits of This Approach**

1. **Individual Processing**: Each recipient gets personalized handling
2. **Role-Based Headers**: CC recipients get proper CC headers
3. **Scalability**: SQS can process messages in parallel
4. **Reliability**: Failed messages can be retried individually
5. **Monitoring**: Each message can be tracked separately

## 🚨 **The CC Duplication Problem (Now Fixed)**

**Before Fix:**
- CC recipients were queued TWICE:
  1. As regular contacts (if in target list)
  2. As CC recipients (with role='cc')

**After Fix:**
- CC recipients are **excluded** from regular contact processing
- They only get queued once with role='cc'

## 🔍 **How to Verify**

### **Check SQS Queue:**
1. Go to AWS SQS Console
2. Find your `bulk-email-queue`
3. Look for messages with different `role` attributes

### **Check CloudWatch Logs:**
```
Queued CC email for cc@example.com
Queued BCC email for bcc@example.com
```

### **Check Email Worker Logs:**
```
[Message 1] CC recipient: cc@example.com will receive email with their address in CC field
[Message 2] BCC recipient: bcc@example.com will receive email with their address in BCC field
```

## 📋 **Summary**

**YES** - Each CC and BCC email address is queued as a separate SQS message with:
- ✅ **Unique message per recipient**
- ✅ **Role identifier** ('cc', 'bcc', 'to', or none)
- ✅ **Individual processing** by email worker
- ✅ **Proper email headers** based on role

This design ensures that CC recipients appear in CC fields and BCC recipients remain hidden, while allowing for scalable, parallel processing of all email recipients.