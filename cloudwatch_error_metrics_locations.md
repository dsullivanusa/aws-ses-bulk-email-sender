# CloudWatch Error Metrics in email_worker_lambda.py

## Overview
The `email_worker_lambda.py` file sends several error metrics to CloudWatch that could trigger alarms. Here are all the locations where ERROR metrics are sent:

## 1. IncompleteCampaigns (Line ~278-284)
**Trigger**: When a campaign is less than 90% complete
**Location**: `check_campaign_completion_status()` function
```python
if completion_percentage < 90:
    print(f"📊 ERROR METRIC → CloudWatch: IncompleteCampaigns (Campaign: {campaign_id}, Completion: {completion_percentage:.1f}%)")
    send_cloudwatch_metric(
        'IncompleteCampaigns',
        1,
        'Count',
        [
            {'Name': 'CampaignId', 'Value': campaign_id},
            {'Name': 'CompletionPercentage', 'Value': f"{completion_percentage:.1f}"}
        ]
    )
```

## 2. ThrottleExceptions (Line ~605-613)
**Trigger**: When SES throttle/rate limit exceptions are detected
**Location**: Main lambda handler exception handling
```python
if rate_control.detect_throttle_exception(send_exception):
    print(f"📊 ERROR METRIC → CloudWatch: ThrottleExceptions (Campaign: {campaign_id}, Type: SES_Throttle)")
    send_cloudwatch_metric(
        'ThrottleExceptions',
        1,
        'Count',
        [
            {'Name': 'CampaignId', 'Value': campaign_id},
            {'Name': 'ErrorType', 'Value': 'SES_Throttle'}
        ]
    )
```

## 3. EmailsFailed (Line ~756-762)
**Trigger**: When any emails fail to send in a batch
**Location**: End of lambda handler
```python
if results['failed'] > 0:
    print(f"📊 ERROR METRIC → CloudWatch: EmailsFailed = {results['failed']} (out of {total_emails} total)")
    send_cloudwatch_metric('EmailsFailed', results['failed'], 'Count')
```

## 4. FailureRate (Line ~776-781)
**Trigger**: When failure rate is greater than 0%
**Location**: End of lambda handler
```python
if failure_rate > 0:
    print(f"📊 ERROR METRIC → CloudWatch: FailureRate = {failure_rate:.1f}%")
    send_cloudwatch_metric('FailureRate', failure_rate, 'Percent')
```

## 5. ThrottleExceptionsInBatch (Line ~784-792)
**Trigger**: When throttles are detected in the current batch
**Location**: End of lambda handler
```python
if results['rate_control_stats']['throttles_detected'] > 0:
    print(f"📊 ERROR METRIC → CloudWatch: ThrottleExceptionsInBatch = {results['rate_control_stats']['throttles_detected']}")
    send_cloudwatch_metric(
        'ThrottleExceptionsInBatch',
        results['rate_control_stats']['throttles_detected'],
        'Count'
    )
```

## Common Causes of CloudWatch Error Alarms

### 1. **CC Duplication Issue** (Most Likely)
- **Symptom**: `EmailsFailed` and `FailureRate` metrics
- **Cause**: CC recipients getting duplicate messages might cause processing errors
- **Solution**: Deploy the CC duplication fix we applied

### 2. **SES Rate Limiting**
- **Symptom**: `ThrottleExceptions` and `ThrottleExceptionsInBatch` metrics
- **Cause**: Sending emails too fast for SES limits
- **Solution**: Adjust rate control settings

### 3. **Campaign Processing Issues**
- **Symptom**: `IncompleteCampaigns` metric
- **Cause**: Campaigns not completing properly
- **Solution**: Check for stuck campaigns or processing errors

### 4. **General Email Failures**
- **Symptom**: `EmailsFailed` and `FailureRate` metrics
- **Cause**: Various email sending failures
- **Solution**: Check CloudWatch logs for specific error messages

## How to Diagnose Your Alarms

1. **Check CloudWatch Metrics Console**:
   - Look for which specific metric is triggering alarms
   - Check the time range when alarms occurred

2. **Check CloudWatch Logs**:
   - Look for the `📊 ERROR METRIC →` messages
   - Check for any exception stack traces

3. **Common Patterns**:
   - If you see `EmailsFailed` spikes after CC campaigns → CC duplication issue
   - If you see `ThrottleExceptions` → Rate limiting issue
   - If you see `IncompleteCampaigns` → Processing stuck

## Temporary Fix to Reduce Alarms

If you want to temporarily reduce error metrics while fixing the root cause, you can comment out specific metrics:

```python
# Temporarily disable specific error metrics
# send_cloudwatch_metric('EmailsFailed', results['failed'], 'Count')
```

**Note**: Only do this temporarily while debugging - these metrics are important for monitoring!