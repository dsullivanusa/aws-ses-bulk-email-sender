# CloudWatch Alarm Notifications Setup Guide

## 🔔 Overview

Configure CloudWatch alarms to send email notifications when email sending failures occur.

## 🚀 Quick Start

### Option 1: Use Existing SNS Topic

If you already have an SNS topic:

```bash
python configure_alarm_notifications.py add arn:aws-us-gov:sns:us-gov-west-1:123456789012:MyTopic
```

### Option 2: Create New SNS Topic and Configure

Create a new SNS topic and subscribe email addresses:

```bash
python configure_alarm_notifications.py create EmailAlerts admin@agency.gov ops@agency.gov
```

**⚠️ Important:** After running this, check your email inbox(es) and **click the confirmation link** in the AWS SNS subscription email!

## 📋 Commands

### Add Notifications to Alarms

```bash
python configure_alarm_notifications.py add <sns-topic-arn>
```

**What it does:**
- Finds all EmailWorker alarms
- Adds your SNS topic to each alarm's actions
- Enables notifications for email failures

**Example:**
```bash
python configure_alarm_notifications.py add arn:aws-us-gov:sns:us-gov-west-1:987654321098:EmailNotifications
```

### Create SNS Topic and Configure

```bash
python configure_alarm_notifications.py create <topic-name> <email1> [email2] [email3] ...
```

**What it does:**
- Creates new SNS topic
- Subscribes all provided email addresses
- Adds topic to all EmailWorker alarms

**Example:**
```bash
python configure_alarm_notifications.py create CISAEmailAlerts admin@cisa.gov ops@cisa.gov manager@cisa.gov
```

**Output:**
```
============================================================
📧 Creating SNS Topic for Alarm Notifications
============================================================
Topic Name: CISAEmailAlerts
Email Addresses: admin@cisa.gov, ops@cisa.gov, manager@cisa.gov

📋 Creating SNS topic...
   ✅ Created topic: arn:aws-us-gov:sns:us-gov-west-1:123:CISAEmailAlerts

📧 Subscribing email addresses...
   ✅ Subscribed: admin@cisa.gov
      ⚠️  Check admin@cisa.gov inbox and confirm subscription!
   ✅ Subscribed: ops@cisa.gov
      ⚠️  Check ops@cisa.gov inbox and confirm subscription!
   ✅ Subscribed: manager@cisa.gov
      ⚠️  Check manager@cisa.gov inbox and confirm subscription!

✅ Subscribed 3 email address(es)

⚠️  IMPORTANT: Each email address must confirm their subscription!

🔧 Updating alarms with SNS topic...
   ✅ EmailWorker-EmailsFailed: SNS topic added
   ✅ EmailWorker-HighFailureRate: SNS topic added
   ✅ EmailWorker-CriticalFailureRate: SNS topic added
   ✅ EmailWorker-ThrottleExceptions: SNS topic added
   ✅ EmailWorker-IncompleteCampaigns: SNS topic added
   ✅ EmailWorker-HighAttachmentDelays: SNS topic added

✅ All alarms configured successfully!
```

### List Current Configuration

```bash
python configure_alarm_notifications.py list
```

**Shows:**
- All EmailWorker alarms
- Current notification configuration
- SNS topics attached to each alarm

### Remove Notifications

```bash
# Remove all notifications
python configure_alarm_notifications.py remove

# Remove specific SNS topic
python configure_alarm_notifications.py remove arn:aws-us-gov:sns:us-gov-west-1:123:MyTopic
```

## 📧 SNS Subscription Confirmation

After subscribing emails to SNS, each recipient must confirm:

1. **Check email inbox** (including spam/junk folder)
2. **Look for email from:** AWS Notifications <no-reply@sns.amazonaws.com>
3. **Subject:** AWS Notification - Subscription Confirmation
4. **Click the confirmation link** in the email
5. **See confirmation page:** "Subscription confirmed!"

**Until confirmed, that email will NOT receive notifications!**

## 🔍 Verify Configuration

### Check Alarm Status

```bash
python view_alarm_status.py
```

### Check SNS Subscriptions

```bash
# List subscriptions for your topic
aws sns list-subscriptions-by-topic --topic-arn arn:aws-us-gov:sns:us-gov-west-1:123:EmailAlerts
```

### Test Notifications

Manually trigger an alarm to test:

```bash
aws cloudwatch set-alarm-state \
  --alarm-name EmailWorker-EmailsFailed \
  --state-value ALARM \
  --state-reason "Test notification" \
  --region us-gov-west-1
```

**You should receive an email notification within 1-2 minutes!**

## 📊 Which Alarms Send Notifications

After configuration, these alarms will send email notifications:

| Alarm | Triggers When | Severity |
|-------|---------------|----------|
| EmailWorker-EmailsFailed | 5+ emails fail in 10 min | 🔴 HIGH |
| EmailWorker-HighFailureRate | >10% failure rate | 🔴 HIGH |
| EmailWorker-CriticalFailureRate | >50% failure rate | ⚫ CRITICAL |
| EmailWorker-ThrottleExceptions | AWS SES throttling detected | 🟡 MEDIUM |
| EmailWorker-IncompleteCampaigns | Campaign doesn't complete | 🟡 MEDIUM |
| EmailWorker-HighAttachmentDelays | 10+ attachment delays | 🟠 LOW |

## 📝 Example Notification Email

When an alarm triggers, you'll receive an email like:

```
Subject: ALARM: "EmailWorker-EmailsFailed" in US-GOV-WEST-1

You are receiving this email because your Amazon CloudWatch Alarm 
"EmailWorker-EmailsFailed" in the US-GOV-WEST-1 region has entered 
the ALARM state, because "Threshold Crossed: 1 datapoint [7.0 (09/10/25 
15:30:00)] was greater than the threshold (5.0)." at "Sunday 09 October, 
2025 15:35:12 UTC".

View this alarm in the AWS Management Console:
https://console.aws.amazon.com/cloudwatch/...

Alarm Details:
- Name: EmailWorker-EmailsFailed
- Description: Email Worker - Individual emails failed to send
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-10-09 15:35:12 UTC

Monitored Metric:
- MetricNamespace: EmailWorker/Custom
- MetricName: EmailsFailed
- Dimensions: []
- Period: 300 seconds
- Statistic: Sum
- Unit: not specified

Threshold:
- ComparisonOperator: GreaterThanThreshold
- Threshold: 5.0
- TreatMissingData: notBreaching

Old State:
- StateValue: OK

New State:
- StateValue: ALARM
- StateReason: Threshold Crossed: 1 datapoint [7.0 (09/10/25 15:30:00)] 
  was greater than the threshold (5.0).
```

## 🛠️ Troubleshooting

### Issue: Not receiving emails

**Check:**
1. SNS subscription confirmed?
   ```bash
   aws sns list-subscriptions-by-topic --topic-arn <your-topic-arn>
   ```
   Look for `"ConfirmationWasAuthenticated": "true"`

2. Email in spam/junk folder?

3. Alarm actually triggered?
   ```bash
   python view_alarm_status.py
   ```

### Issue: "Topic does not exist"

**Solution:**
- Verify topic ARN is correct
- Ensure topic exists in same region (us-gov-west-1)
- Check IAM permissions

### Issue: "Access Denied"

**Solution:**
Lambda needs these permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "sns:Publish",
    "cloudwatch:PutMetricAlarm"
  ],
  "Resource": "*"
}
```

## 📚 Related Scripts

- `create_email_failure_alarms.py` - Create the alarms first
- `view_alarm_status.py` - View current alarm states
- `configure_alarm_notifications.py` - This script

## 🎯 Complete Setup Example

```bash
# Step 1: Create alarms (if not already done)
python create_email_failure_alarms.py

# Step 2: Create SNS topic and configure notifications
python configure_alarm_notifications.py create EmailFailureAlerts admin@agency.gov ops@agency.gov

# Step 3: Confirm email subscriptions (check inbox)
# Click confirmation links in emails from AWS

# Step 4: Verify configuration
python configure_alarm_notifications.py list

# Step 5: Test (optional)
aws cloudwatch set-alarm-state \
  --alarm-name EmailWorker-EmailsFailed \
  --state-value ALARM \
  --state-reason "Test notification" \
  --region us-gov-west-1

# Step 6: Check email - you should receive notification!
```

## ✅ Benefits

- 🔔 **Immediate alerts** when emails fail
- 📧 **Email notifications** to multiple recipients
- 🎯 **Severity levels** (Critical, High, Medium, Low)
- 📊 **Detailed metrics** in notification emails
- 🔗 **Direct links** to AWS Console
- ⚙️ **Customizable thresholds**

---

**Last Updated:** October 12, 2025

**Status:** Ready to use

**Support:** Check CloudWatch console for alarm details

