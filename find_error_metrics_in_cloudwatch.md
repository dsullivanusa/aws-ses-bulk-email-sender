# How to Find Error Metric Messages in CloudWatch Logs

## Step-by-Step Guide

### 1. Navigate to CloudWatch Logs
1. Go to **AWS Console** → **CloudWatch**
2. Click **Logs** → **Log groups** in the left sidebar
3. Find your Lambda function log group: `/aws/lambda/your-email-worker-function-name`

### 2. Search for Error Metrics
Use these specific search terms to find error metric messages:

#### **Search Terms to Use:**

```
📊 ERROR METRIC
```
This will find all error metrics being sent.

**Or search for specific metrics:**

```
EmailsFailed
```

```
FailureRate
```

```
ThrottleExceptions
```

```
IncompleteCampaigns
```

```
ThrottleExceptionsInBatch
```

### 3. Using CloudWatch Logs Insights (Recommended)

1. Go to **CloudWatch** → **Logs** → **Insights**
2. Select your Lambda log group
3. Use these queries:

#### **Find All Error Metrics:**
```sql
fields @timestamp, @message
| filter @message like /📊 ERROR METRIC/
| sort @timestamp desc
| limit 100
```

#### **Find Failed Emails:**
```sql
fields @timestamp, @message
| filter @message like /EmailsFailed/
| sort @timestamp desc
| limit 50
```

#### **Find Throttle Issues:**
```sql
fields @timestamp, @message
| filter @message like /ThrottleExceptions/
| sort @timestamp desc
| limit 50
```

#### **Find Campaign Issues:**
```sql
fields @timestamp, @message
| filter @message like /IncompleteCampaigns/
| sort @timestamp desc
| limit 50
```

### 4. What to Look For

#### **Example Error Metric Messages:**

**EmailsFailed:**
```
📊 ERROR METRIC → CloudWatch: EmailsFailed = 5 (out of 20 total)
📊 Sending ERROR metric to CloudWatch: EmailsFailed = 5 emails failed to send
```

**FailureRate:**
```
📊 ERROR METRIC → CloudWatch: FailureRate = 25.0%
📊 Sending ERROR metric to CloudWatch: FailureRate = 25.0% (5/20)
```

**ThrottleExceptions:**
```
📊 ERROR METRIC → CloudWatch: ThrottleExceptions (Campaign: camp-123, Type: SES_Throttle)
📊 Sending ERROR metric to CloudWatch: ThrottleExceptions - Campaign camp-123 hit SES throttle limit
```

**IncompleteCampaigns:**
```
📊 ERROR METRIC → CloudWatch: IncompleteCampaigns (Campaign: camp-123, Completion: 75.0%)
📊 Sending ERROR metric to CloudWatch: IncompleteCampaigns - Campaign camp-123 is 75.0% complete
```

### 5. Time-Based Search

To find errors around a specific time:

1. **Set time range** in CloudWatch Logs
2. **Use relative time** (e.g., "Last 1 hour", "Last 24 hours")
3. **Use absolute time** for specific incidents

### 6. Advanced Search Patterns

#### **Find Errors with Context:**
```sql
fields @timestamp, @message
| filter @message like /📊 ERROR METRIC/ or @message like /EXCEPTION/ or @message like /ERROR/
| sort @timestamp desc
| limit 100
```

#### **Find CC-Related Issues:**
```sql
fields @timestamp, @message
| filter @message like /CC/ or @message like /duplicate/ or @message like /EXCLUDING/
| sort @timestamp desc
| limit 100
```

#### **Find Campaign-Specific Errors:**
```sql
fields @timestamp, @message
| filter @message like /Campaign.*camp-YOUR-CAMPAIGN-ID/
| sort @timestamp desc
| limit 100
```

### 7. Export Results

1. **Download results** as CSV for analysis
2. **Create custom dashboard** for ongoing monitoring
3. **Set up log filters** for real-time alerts

## Quick Troubleshooting Guide

### If You See:

**📊 ERROR METRIC → CloudWatch: EmailsFailed**
- **Cause**: Emails are failing to send
- **Check**: Look for exception messages before this metric
- **Solution**: Deploy CC duplication fix

**📊 ERROR METRIC → CloudWatch: FailureRate**
- **Cause**: High percentage of failed emails
- **Check**: Look at the percentage and total counts
- **Solution**: Fix underlying email sending issues

**📊 ERROR METRIC → CloudWatch: ThrottleExceptions**
- **Cause**: SES rate limits exceeded
- **Check**: Look for "throttle" or "rate limit" messages
- **Solution**: Reduce sending rate or increase SES limits

**📊 ERROR METRIC → CloudWatch: IncompleteCampaigns**
- **Cause**: Campaigns not completing properly
- **Check**: Look at completion percentage
- **Solution**: Check for stuck processing or errors

## Pro Tips

1. **Use the emoji** 📊 to quickly find error metrics
2. **Look at timestamps** to correlate with alarm times
3. **Check surrounding log messages** for context
4. **Filter by Request ID** to trace specific executions
5. **Use multiple search terms** with OR operators

## Example Search Session

1. Start with: `📊 ERROR METRIC`
2. If you find EmailsFailed, search for: `EmailsFailed` 
3. Look at timestamps and find related errors
4. Search for the campaign ID mentioned in errors
5. Check for any exception stack traces around that time

This will help you identify exactly what's causing your CloudWatch alarms!