# SES To Address Validation - Summary

## ✅ **VALIDATION ADDED**

I've added comprehensive validation to detect when there's no To email address and prevent sending emails to AWS SES. This includes print statements with campaign IDs for immediate visibility.

## 📍 **Validation Locations Added**

### **1. Simple Email Validation (send_email API)**
**Location**: `email_worker_lambda.py` - around line 1176
**Validates**: ToAddresses in destination object

```python
# 🚨 VALIDATION: Check for To address before sending to SES
to_addresses = destination.get('ToAddresses', [])
if not to_addresses or len(to_addresses) == 0:
    campaign_id = campaign.get('campaign_id', 'unknown') if campaign else 'unknown'
    error_msg = f"No To address specified for simple email. SES requires at least one To recipient."
    
    # Print statement for immediate visibility
    print(f"🚨 SES VALIDATION ERROR - Campaign {campaign_id}: {error_msg}")
    print(f"   Message {msg_idx}: Destination={destination}")
    print(f"   Message {msg_idx}: Contact={contact}")
    print(f"   Message {msg_idx}: Role={message.get('role', 'None')}")
    
    return False  # Don't send the email
```

### **2. Raw Email Destinations Validation (send_raw_email API)**
**Location**: `email_worker_lambda.py` - around line 1626
**Validates**: Destinations list for raw email

```python
# 🚨 VALIDATION: Check for destinations before sending raw email to SES
if not destinations or len(destinations) == 0:
    campaign_id = campaign.get('campaign_id', 'unknown') if campaign else 'unknown'
    error_msg = f"No destinations specified for raw email. SES requires at least one recipient."
    
    # Print statement for immediate visibility
    print(f"🚨 SES VALIDATION ERROR - Campaign {campaign_id}: {error_msg}")
    print(f"   Message {msg_idx}: Destinations={destinations}")
    print(f"   Message {msg_idx}: Contact={contact}")
    
    return False  # Don't send the email
```

### **3. MIME To Field Validation (Raw Email with Attachments)**
**Location**: `email_worker_lambda.py` - around line 1228
**Validates**: To field in MIME message

```python
# 🚨 VALIDATION: Check if To field is valid
to_email = contact.get("email", "").strip()
if not to_email or "@" not in to_email:
    campaign_id = campaign.get('campaign_id', 'unknown') if campaign else 'unknown'
    error_msg = f"Invalid or empty To email address in MIME message: '{to_email}'"
    
    # Print statement for immediate visibility
    print(f"🚨 SES VALIDATION ERROR - Campaign {campaign_id}: {error_msg}")
    print(f"   Message {msg_idx}: Contact={contact}")
    print(f"   Message {msg_idx}: To Email='{to_email}'")
    
    return False  # Don't send the email
```

### **4. MIME To Field Validation (Simple Raw Email)**
**Location**: `email_worker_lambda.py` - around line 1796
**Validates**: To field in simple MIME message

```python
# Same validation as above, but for simple raw email path
```

## 📊 **CloudWatch Metrics Sent**

Each validation error sends a CloudWatch metric:

```python
send_cloudwatch_metric(
    'SESValidationErrors',
    1,
    'Count',
    [
        {'Name': 'ErrorType', 'Value': 'NoToAddress|NoDestinations|InvalidToEmail'},
        {'Name': 'EmailType', 'Value': 'SimpleEmail|RawEmail|RawEmailMIME|SimpleRawEmail'},
        {'Name': 'CampaignId', 'Value': campaign_id}
    ]
)
```

## 🔍 **What You'll See in Logs**

### **Print Statements (Immediate Visibility)**:
```
🚨 SES VALIDATION ERROR - Campaign camp-123: No To address specified for simple email. SES requires at least one To recipient.
   Message 1: Destination={'CcAddresses': ['cc@example.com'], 'BccAddresses': ['bcc@example.com']}
   Message 1: Contact={'email': ''}
   Message 1: Role=cc
```

### **Logger Messages (CloudWatch Logs)**:
```
[Message 1] ❌ SES VALIDATION ERROR - Campaign camp-123: No To address specified for simple email. SES requires at least one To recipient.
[Message 1]   Destination: {'CcAddresses': ['cc@example.com'], 'BccAddresses': ['bcc@example.com']}
[Message 1]   Contact: {'email': ''}
[Message 1]   Role: cc
```

## 🚨 **Error Types Detected**

1. **NoToAddress**: No addresses in ToAddresses array for simple email
2. **NoDestinations**: No destinations specified for raw email
3. **InvalidToEmail**: Empty or invalid To email address in MIME message

## 📈 **CloudWatch Monitoring**

You can create alarms for:
- **Metric**: `SESValidationErrors`
- **Dimensions**: 
  - `ErrorType` (NoToAddress, NoDestinations, InvalidToEmail)
  - `EmailType` (SimpleEmail, RawEmail, etc.)
  - `CampaignId` (specific campaign)

## 🎯 **Benefits**

1. **Prevents SES Errors**: Stops invalid emails before they reach SES
2. **Clear Logging**: Print statements show immediate issues
3. **Campaign Tracking**: Includes campaign ID in all error messages
4. **Metrics**: CloudWatch metrics for monitoring and alerting
5. **Debugging**: Detailed context about what went wrong

## 🔧 **Common Scenarios This Catches**

1. **CC-only emails**: When someone tries to send email with only CC recipients
2. **BCC-only emails**: When someone tries to send email with only BCC recipients
3. **Empty contacts**: When contact email is empty or invalid
4. **Malformed destinations**: When SQS message has invalid recipient data

## 📋 **Next Steps**

1. **Deploy** the updated `email_worker_lambda.py`
2. **Test** with campaigns that might have missing To addresses
3. **Monitor** CloudWatch logs for validation error messages
4. **Set up alarms** for `SESValidationErrors` metric
5. **Check** print statements in Lambda logs for immediate visibility

This validation will prevent SES errors and provide clear debugging information when To addresses are missing or invalid!