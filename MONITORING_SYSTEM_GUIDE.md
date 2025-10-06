# 🚨 Email System Monitoring & Alerting Guide

## Overview

The email system now includes comprehensive monitoring and alerting capabilities that automatically detect and alert on:

1. **Throttle Exceptions** - When AWS SES or SMTP rate limits are hit
2. **Incomplete Campaigns** - When email campaigns stop processing before completion
3. **System Health Issues** - Lambda errors, queue backlogs, and performance problems

## 🎯 Monitoring Components

### 1. **Email Worker Lambda Function**
- **Enhanced with CloudWatch metrics**
- **Adaptive rate control** based on attachment sizes
- **Automatic throttle detection** and handling
- **Custom metrics** for monitoring

### 2. **Campaign Monitor Lambda Function**
- **Scheduled monitoring** (runs every 5 minutes)
- **Detects stuck campaigns** automatically
- **Queue health monitoring**
- **Summary metrics** for system overview

### 3. **CloudWatch Alarms**
- **Real-time alerting** on critical issues
- **Multiple alarm types** for different scenarios
- **Configurable thresholds** and evaluation periods

## 🚨 CloudWatch Alarms

### **Standard AWS Metrics Alarms**

| Alarm Name | Description | Trigger Condition |
|------------|-------------|-------------------|
| `EmailWorker-FunctionErrors` | Lambda function errors | ≥1 error in 10 minutes |
| `EmailWorker-HighDuration` | Lambda taking too long | >10 minutes average |
| `EmailWorker-NoActivity` | No Lambda invocations | <1 invocation in 30 minutes |

### **Custom Metrics Alarms**

| Alarm Name | Description | Trigger Condition |
|------------|-------------|-------------------|
| `EmailWorker-ThrottleExceptions` | Throttle exceptions detected | ≥1 throttle in 10 minutes |
| `EmailWorker-IncompleteCampaigns` | Campaigns not completing | ≥1 incomplete campaign |
| `CampaignMonitor-StuckCampaigns` | Campaigns stuck for >1 hour | ≥1 stuck campaign |

### **Queue Health Alarms**

| Alarm Name | Description | Trigger Condition |
|------------|-------------|-------------------|
| `EmailWorker-QueueBacklog` | Too many messages in queue | >100 messages visible |
| `EmailWorker-DLQMessages` | Failed messages in DLQ | ≥1 message in DLQ |

## 📊 Custom CloudWatch Metrics

### **Email Worker Metrics**

| Metric Name | Namespace | Description |
|-------------|-----------|-------------|
| `ThrottleExceptions` | `EmailWorker/Custom` | Number of throttle exceptions |
| `IncompleteCampaigns` | `EmailWorker/Custom` | Campaigns not completing |
| `AttachmentDelays` | `EmailWorker/Custom` | Emails with attachment delays |
| `BatchProcessing` | `EmailWorker/Custom` | Lambda batch processing events |
| `EmailsProcessed` | `EmailWorker/Custom` | Total emails processed |
| `ProcessingDuration` | `EmailWorker/Custom` | Batch processing duration |

### **Campaign Monitor Metrics**

| Metric Name | Namespace | Description |
|-------------|-----------|-------------|
| `StuckCampaigns` | `EmailWorker/CampaignMonitor` | Campaigns stuck >1 hour |
| `QueueDepth` | `EmailWorker/QueueHealth` | SQS queue message counts |
| `TotalCampaigns` | `EmailWorker/Summary` | Total campaigns in system |
| `ActiveCampaigns` | `EmailWorker/Summary` | Currently active campaigns |
| `CompletedCampaigns` | `EmailWorker/Summary` | Successfully completed campaigns |

## 🔧 Deployment Instructions

### **Option 1: Complete Deployment (Recommended)**
```bash
python deploy_monitoring_system.py
```

This script will:
- ✅ Update email worker Lambda with monitoring
- ✅ Deploy campaign monitor Lambda
- ✅ Create all CloudWatch alarms
- ✅ Setup EventBridge scheduling
- ✅ Verify deployment

### **Option 2: Individual Components**
```bash
# Deploy CloudWatch alarms only
python cloudwatch_alarms_setup.py

# Deploy adaptive rate control only
python deploy_adaptive_rate_control.py
```

## 📋 Monitoring Scenarios

### **Scenario 1: Throttle Exception Alert**
```
Trigger: AWS SES rate limit exceeded
Response: 
- CloudWatch alarm fires
- Email sending rate automatically reduced
- Alert sent to monitoring team
- System gradually recovers
```

### **Scenario 2: Campaign Stuck Alert**
```
Trigger: Campaign <90% complete after 1 hour
Response:
- Campaign Monitor detects stuck campaign
- CloudWatch alarm fires
- Investigation team notified
- Manual intervention may be required
```

### **Scenario 3: Queue Backlog Alert**
```
Trigger: >100 messages in SQS queue
Response:
- Queue health alarm fires
- Indicates processing bottleneck
- May need to scale Lambda concurrency
- Check for system issues
```

## 🔍 Troubleshooting Guide

### **High Throttle Exception Rate**
**Symptoms:**
- Frequent `EmailWorker-ThrottleExceptions` alarms
- Slow email processing
- High attachment delay metrics

**Solutions:**
1. Increase `MAX_DELAY_SECONDS` environment variable
2. Request AWS SES sending limit increase
3. Split large campaigns into smaller batches
4. Optimize attachment sizes

### **Campaigns Getting Stuck**
**Symptoms:**
- `CampaignMonitor-StuckCampaigns` alarms
- Low completion percentages
- Messages remaining in SQS queue

**Solutions:**
1. Check Lambda function logs for errors
2. Verify DynamoDB table permissions
3. Check SQS queue configuration
4. Review campaign data integrity

### **Queue Backlog Issues**
**Symptoms:**
- `EmailWorker-QueueBacklog` alarms
- Messages accumulating in queue
- Slow processing times

**Solutions:**
1. Increase Lambda concurrency limit
2. Increase Lambda memory allocation
3. Check for dead letter queue messages
4. Review batch size configuration

## 📊 Monitoring Dashboard

### **CloudWatch Dashboard Metrics to Monitor**

1. **Email Processing Rate**
   - `EmailsProcessed` metric
   - `ProcessingDuration` metric
   - Lambda invocation count

2. **Error Rates**
   - `ThrottleExceptions` metric
   - Lambda error count
   - Dead letter queue depth

3. **Campaign Health**
   - `StuckCampaigns` metric
   - `IncompleteCampaigns` metric
   - Campaign completion percentages

4. **System Performance**
   - Lambda duration
   - Memory utilization
   - Queue depth metrics

## 🔔 Alerting Configuration

### **SNS Notification Setup**
```bash
# Create SNS topic
aws sns create-topic --name email-worker-alarms --region us-gov-west-1

# Subscribe to email notifications
aws sns subscribe \
  --topic-arn arn:aws-us-gov:sns:us-gov-west-1:ACCOUNT:email-worker-alarms \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-gov-west-1
```

### **Alarm Action Configuration**
```bash
# Add SNS action to alarm
aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-ThrottleExceptions \
  --alarm-actions arn:aws-us-gov:sns:us-gov-west-1:ACCOUNT:email-worker-alarms \
  --region us-gov-west-1
```

## 📈 Performance Optimization

### **Environment Variables for Tuning**
```bash
# Conservative settings (slower, more reliable)
BASE_DELAY_SECONDS=0.5
MAX_DELAY_SECONDS=10.0
MIN_DELAY_SECONDS=0.1

# Aggressive settings (faster, higher risk)
BASE_DELAY_SECONDS=0.05
MAX_DELAY_SECONDS=2.0
MIN_DELAY_SECONDS=0.01

# High-volume settings
BASE_DELAY_SECONDS=0.2
MAX_DELAY_SECONDS=8.0
MIN_DELAY_SECONDS=0.05
```

### **Lambda Configuration Optimization**
```bash
# Increase memory for better performance
aws lambda update-function-configuration \
  --function-name email-worker-function \
  --memory-size 1024 \
  --timeout 900 \
  --region us-gov-west-1

# Increase concurrency limit
aws lambda put-provisioned-concurrency-config \
  --function-name email-worker-function \
  --provisioned-concurrency-config ProvisionedConcurrencyConfig='{ProvisionedConcurrencyCount=5}' \
  --region us-gov-west-1
```

## 🧪 Testing the Monitoring System

### **Test Throttle Detection**
```bash
# Simulate throttle by sending many emails quickly
# Monitor CloudWatch logs for throttle detection
aws logs tail /aws/lambda/email-worker-function --follow --region us-gov-west-1
```

### **Test Campaign Monitoring**
```bash
# Run campaign monitor manually
python campaign_monitor.py

# Check for stuck campaigns
aws dynamodb scan \
  --table-name EmailCampaigns \
  --filter-expression "#status IN (:processing, :sending)" \
  --expression-attribute-names '{"#status": "status"}' \
  --expression-attribute-values '{":processing": {"S": "processing"}, ":sending": {"S": "sending"}}' \
  --region us-gov-west-1
```

### **Test CloudWatch Alarms**
```bash
# View alarm states
aws cloudwatch describe-alarms --region us-gov-west-1

# View alarm history
aws cloudwatch describe-alarm-history --region us-gov-west-1
```

## 📞 Emergency Response Procedures

### **When Throttle Alarms Fire**
1. **Immediate**: Check AWS SES sending quotas
2. **Short-term**: Increase delay settings via environment variables
3. **Long-term**: Request quota increase from AWS support

### **When Campaign Alarms Fire**
1. **Immediate**: Check campaign status in DynamoDB
2. **Short-term**: Review Lambda logs for errors
3. **Long-term**: Investigate root cause and optimize

### **When Queue Alarms Fire**
1. **Immediate**: Check SQS queue depth
2. **Short-term**: Increase Lambda concurrency
3. **Long-term**: Optimize batch processing

## 📚 Additional Resources

- **CloudWatch Documentation**: https://docs.aws.amazon.com/cloudwatch/
- **AWS SES Limits**: https://docs.aws.amazon.com/ses/latest/dg/quotas.html
- **Lambda Monitoring**: https://docs.aws.amazon.com/lambda/latest/dg/monitoring-functions.html
- **SQS Monitoring**: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-monitoring-cloudwatch.html

## 🎉 Benefits Summary

### **Before Monitoring**
- ❌ Manual monitoring required
- ❌ No early warning for issues
- ❌ Difficult to diagnose problems
- ❌ No automatic rate adjustment

### **After Monitoring**
- ✅ **Automated monitoring** and alerting
- ✅ **Proactive issue detection**
- ✅ **Detailed metrics** for troubleshooting
- ✅ **Adaptive rate control**
- ✅ **Campaign completion tracking**
- ✅ **System health visibility**

The monitoring system ensures your email campaigns run reliably and efficiently, with automatic detection and response to common issues.
