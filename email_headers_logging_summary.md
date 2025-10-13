# Email Headers Logging Summary

## Added Logging to email_worker_lambda.py

The following logging has been added to help you debug and print the To, CC, and BCC lines:

### 1. Role-Based Processing Logging
**Location**: Around line 467
**What it shows**: How the worker processes different message roles (regular, cc, bcc, to)

```
[Message X] 🎭 ROLE-BASED PROCESSING:
[Message X]   Message Role: cc
[Message X]   Contact Email: user@example.com
[Message X]   Campaign CC: ['cc1@example.com', 'cc2@example.com']
[Message X]   Campaign BCC: ['bcc@example.com']
```

### 2. Simple Email Headers (No Attachments)
**Location**: Around line 1158
**What it shows**: To, CC, BCC for emails sent via send_email API

```
[Message X] 📧 EMAIL HEADERS (Simple Email):
[Message X]   To: ['user@example.com']
[Message X]   CC: ['cc1@example.com', 'cc2@example.com']
[Message X]   BCC: ['bcc@example.com']
```

### 3. Raw Email Headers (With Attachments)
**Location**: Around line 1186
**What it shows**: To, CC, BCC for emails with attachments sent via send_raw_email API

```
[Message X] 📧 EMAIL HEADERS (Raw Email with Attachments):
[Message X]   To: user@example.com
[Message X]   CC: ['cc1@example.com', 'cc2@example.com']
[Message X]   BCC: ['bcc@example.com']
[Message X]   MIME CC Header: cc1@example.com, cc2@example.com
```

### 4. SES Envelope Destinations
**Location**: Around line 1334
**What it shows**: All recipients that SES will deliver to (envelope recipients)

```
[Message X] 📬 SES ENVELOPE DESTINATIONS:
[Message X]   All Recipients: ['user@example.com', 'cc1@example.com', 'cc2@example.com', 'bcc@example.com']
[Message X]   Total Count: 4
```

## How to Use This Logging

1. **Deploy** the updated `email_worker_lambda.py` to AWS Lambda
2. **Send a test campaign** with CC and BCC recipients
3. **Check CloudWatch Logs** for your email worker Lambda function
4. **Look for the emoji indicators**:
   - 🎭 = Role-based processing
   - 📧 = Email headers
   - 📬 = SES envelope destinations

## What to Look For

- **CC Duplication**: If you see the same email address in multiple messages with different roles
- **Missing Recipients**: If CC/BCC lists are empty when they shouldn't be
- **Header Issues**: If MIME CC header doesn't match the CC list
- **Envelope Problems**: If SES destinations don't include all expected recipients

## Example Output for CC Recipient

For a CC recipient (role='cc'), you should see:
```
[Message 1] 🎭 ROLE-BASED PROCESSING:
[Message 1]   Message Role: cc
[Message 1]   Contact Email: cc-user@example.com
[Message 1]   Campaign CC: ['cc-user@example.com']
[Message 1]   Campaign BCC: []

[Message 1] 📧 EMAIL HEADERS (Simple Email):
[Message 1]   To: ['sender@example.com']  # CC recipients use sender as To
[Message 1]   CC: ['cc-user@example.com']  # CC recipient appears in CC field
[Message 1]   BCC: []
```

This logging will help you verify that the CC duplication fix is working correctly.