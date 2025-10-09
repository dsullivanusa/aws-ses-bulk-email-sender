# Email Failure Alarms Guide

## 🚨 Overview

This guide covers CloudWatch alarms that monitor **individual email sending failures** (custom metrics from `EmailWorker/Custom` namespace), which are different from Lambda function-level errors.

## 📊 Alarm Types Created

### 1. **EmailWorker-EmailsFailed** (High Severity)
- **Monitors:** Number of individual emails that failed to send
- **Threshold:** 5+ failed emails in 10 minutes
- **Triggers on:** SES errors, validation errors, send failures
- **Use case:** Detect when emails are failing to send

### 2. **EmailWorker-HighFailureRate** (High Severity)
- **Monitors:** Percentage of email send failures
- **Threshold:** >10% failure rate
- **Triggers on:** High proportion of failures
- **Use case:** Detect systemic sending issues

### 3. **EmailWorker-CriticalFailureRate** (Critical Severity)
- **Monitors:** Very high failure percentage
- **Threshold:** >50% failure rate
- **Triggers on:** Majority of emails failing
- **Use case:** Critical system issues requiring immediate attention

### 4. **EmailWorker-ThrottleExceptions** (Medium Severity)
- **Monitors:** AWS SES throttling events
- **Threshold:** Any throttle exceptions in 10 minutes
- **Triggers on:** Hitting SES rate limits
- **Use case:** Detect when you're being throttled by AWS

### 5. **EmailWorker-IncompleteCampaigns** (Medium Severity)
- **Monitors:** Campaigns not finishing
- **Threshold:** Any incomplete campaigns
- **Triggers on:** Campaigns <90% complete
- **Use case:** Detect stuck or failing campaigns

### 6. **EmailWorker-HighAttachmentDelays** (Low Severity)
- **Monitors:** Attachment processing delays
- **Threshold:** 10+ attachment delays in 10 minutes
- **Triggers on:** Large attachments causing slowdowns
- **Use case:** Performance monitoring for attachments

---

## 🚀 Quick Start

### Create All Alarms
```bash
# Method 1: Run Python script
python create_email_failure_alarms.py

# Method 2: Windows batch file (double-click)
setup_email_alarms.bat
```

### View Alarm Status
```bash
# View EmailWorker alarms
python view_alarm_status.py

# View all CloudWatch alarms
python view_alarm_status.py --all

# View alarm history (last 24 hours)
python view_alarm_status.py --history

# View alarm history (custom time range)
python view_alarm_status.py --history 48
```

### Test an Alarm
```bash
python view_alarm_status.py --test EmailWorker-EmailsFailed
```

---

## 📋 Available Commands

### create_email_failure_alarms.py

```bash
# Create alarms (default)
python create_email_failure_alarms.py

# View existing alarms
python create_email_failure_alarms.py view

# Delete all email failure alarms
python create_email_failure_alarms.py delete

# Show help
python create_email_failure_alarms.py help
```

### view_alarm_status.py

```bash
# View EmailWorker alarms status
python view_alarm_status.py

# View all alarms
python view_alarm_status.py --all

# View alarm history
python view_alarm_status.py --history [hours]

# Test an alarm
python view_alarm_status.py --test <alarm-name>

# Show help
python view_alarm_status.py --help
```

---

## 🔍 When Alarms Trigger

### EmailsFailed Alarm Triggers

**What it means:** Multiple emails failed to send in a short time

**Common causes:**
1. Invalid recipient email addresses
2. SES sandbox limitations (unverified recipients)
3. SES sending quota exceeded
4. Malformed email content
5. Missing required fields (from, to, subject)

**Actions to take:**
```bash
# 1. Search for error details in logs
python search_lambda_errors_with_code.py email-worker-function 1

# 2. Check recent campaign failures
aws dynamodb scan \
  --table-name EmailCampaigns \
  --filter-expression "failed_count > :zero" \
  --expression-attribute-values '{":zero":{"N":"0"}}' \
  --region us-gov-west-1

# 3. Check SES sending limits
aws ses get-send-quota --region us-gov-west-1
```

### HighFailureRate Alarm Triggers

**What it means:** High percentage of sends are failing

**Common causes:**
1. Invalid contact data in database
2. SES configuration issues
3. Network connectivity problems
4. AWS service outage

**Actions to take:**
```bash
# 1. Check failure patterns
python search_lambda_errors_with_code.py email-worker-function 6

# 2. Verify SES configuration
aws ses get-identity-verification-attributes \
  --identities your-sender@example.com \
  --region us-gov-west-1

# 3. Check AWS service health
# Visit: https://status.aws.amazon.com/
```

### ThrottleExceptions Alarm Triggers

**What it means:** AWS is throttling your sending rate

**Common causes:**
1. Sending too fast (exceeding send rate)
2. Account in SES sandbox (low limits)
3. Sudden spike in volume

**Actions to take:**
```bash
# 1. Check current SES quotas
aws ses get-send-quota --region us-gov-west-1

# 2. Request limit increase (if needed)
# Visit: AWS Console → SES → Account Dashboard → Request increase

# 3. Review adaptive rate control settings
# Edit email_worker_lambda.py:
#   BASE_DELAY_SECONDS environment variable
```

---

## 🔧 Alarm Configuration

### Modify Thresholds

Edit `create_email_failure_alarms.py` to adjust thresholds:

```python
# EmailsFailed alarm (line 34)
Threshold=5.0,  # Change to your desired threshold

# HighFailureRate alarm (line 60)
Threshold=10.0,  # Change to your desired percentage

# CriticalFailureRate alarm (line 83)
Threshold=50.0,  # Change to your desired percentage
```

### Change Evaluation Periods

```python
# Make alarm more sensitive (trigger faster)
EvaluationPeriods=1,  # Trigger after 1 period

# Make alarm less sensitive (trigger slower)
EvaluationPeriods=3,  # Require 3 consecutive periods
```

### Adjust Period Duration

```python
# Check more frequently
Period=60,  # 1 minute

# Check less frequently
Period=600,  # 10 minutes
```

---

## 📈 Viewing Metrics

### AWS Console
```
CloudWatch → Metrics → EmailWorker/Custom
```

### AWS CLI
```bash
# Get EmailsFailed metric
aws cloudwatch get-metric-statistics \
  --namespace EmailWorker/Custom \
  --metric-name EmailsFailed \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-gov-west-1

# Get FailureRate metric
aws cloudwatch get-metric-statistics \
  --namespace EmailWorker/Custom \
  --metric-name FailureRate \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-gov-west-1
```

---

## 🔔 Setting Up Notifications

### Create SNS Topic
```bash
# Create SNS topic for alarm notifications
aws sns create-topic \
  --name email-worker-alarms \
  --region us-gov-west-1

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-gov-west-1:ACCOUNT-ID:email-worker-alarms \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-gov-west-1

# Confirm subscription (check your email)
```

### Add SNS to Alarms
```python
# Edit create_email_failure_alarms.py
# Add SNS ARN to put_metric_alarm calls:

AlarmActions=[
    'arn:aws:sns:us-gov-west-1:ACCOUNT-ID:email-worker-alarms'
]
```

---

## 🎯 Comparison: Two Types of Error Monitoring

| Aspect | Lambda Function Errors | Email Send Failures |
|--------|----------------------|-------------------|
| **Alarm Name** | `EmailWorker-FunctionErrors` | `EmailWorker-EmailsFailed` |
| **Namespace** | `AWS/Lambda` | `EmailWorker/Custom` |
| **Metric** | `Errors` (built-in) | `EmailsFailed` (custom) |
| **What it tracks** | Lambda crashes, timeouts, OOM | Individual email send failures |
| **When it triggers** | Function fails to complete | Email fails to send (SES error) |
| **Severity** | Critical (system failure) | High (user impact) |
| **Source code** | Lambda runtime | Lines 565, 482-497 in email_worker_lambda.py |

**Both are important!** 
- Function errors = system is broken
- Email failures = emails not getting delivered

---

## 🚨 Troubleshooting

### "No data available for alarm"
**Problem:** Alarm shows INSUFFICIENT_DATA

**Solutions:**
1. Trigger the Lambda function to generate metrics
2. Send a test campaign
3. Wait 5-10 minutes for data to populate

### "Alarm state doesn't change"
**Problem:** Alarm stuck in same state

**Solutions:**
1. Check if Lambda is actually running
2. Verify custom metrics are being sent
3. Check metric namespace is correct (EmailWorker/Custom)

### "Can't create alarm - metric not found"
**Problem:** Metric doesn't exist in CloudWatch

**Solutions:**
1. Run email worker at least once to create metrics
2. Check email_worker_lambda.py has send_cloudwatch_metric calls
3. Verify Lambda has CloudWatch PutMetricData permission

---

## 📝 Best Practices

1. **Create alarms immediately** after deploying email worker
2. **Test alarms** regularly to ensure they work
3. **Review alarm history** weekly to identify patterns
4. **Adjust thresholds** based on your normal error rates
5. **Set up SNS notifications** for critical alarms
6. **Document response procedures** for each alarm type
7. **Monitor both** Lambda errors AND email failures

---

## 🔗 Related Tools

- `search_lambda_errors_with_code.py` - Find errors in logs with source code
- `tail_lambda_logs.py` - Real-time log viewing
- `cloudwatch_alarms_setup.py` - Lambda function-level alarms
- `view_lambda_errors.py` - Basic error viewer

---

## 💡 Pro Tips

1. **Set different thresholds for different times**
   - Higher thresholds during business hours (more volume)
   - Lower thresholds during off-hours (catch issues early)

2. **Create composite alarms**
   - Combine multiple alarms to reduce noise
   - Example: Trigger only if EmailsFailed AND HighFailureRate

3. **Use alarm actions**
   - Auto-scaling: Increase concurrency when throttled
   - Auto-remediation: Lambda to retry failed emails
   - Notifications: Different SNS topics for different severities

4. **Track trends over time**
   - Export alarm history to S3
   - Create dashboards with historical data
   - Identify patterns (e.g., failures every Monday morning)

---

## 📞 Quick Reference

```bash
# Setup (one-time)
python create_email_failure_alarms.py

# Daily monitoring
python view_alarm_status.py

# When alarm triggers
python search_lambda_errors_with_code.py email-worker-function 1
python view_alarm_status.py --history

# Weekly review
python view_alarm_status.py --history 168
```

---

**Questions?** Check the troubleshooting section or search CloudWatch Logs for details.

