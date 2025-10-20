# Where Are Errors Sent to CloudWatch Error Metrics?

## Understanding CloudWatch Error Metrics for Lambda

There are **two types** of error metrics in CloudWatch for Lambda functions:

### 1. **AWS Lambda Built-in Error Metrics** (What triggers your alarm)
### 2. **Custom CloudWatch Metrics** (What your code sends manually)

---

## 1. AWS Lambda Built-in Error Metrics ⚡

### How Lambda Automatically Reports Errors

AWS Lambda **automatically** sends error metrics to CloudWatch when:
- An **unhandled exception** is raised from the lambda_handler
- The function **times out** 
- The function runs **out of memory**
- The function **crashes** or exits with an error

### In Your `email_worker_lambda.py`

The problem is your code is **catching ALL exceptions** and returning success:

```python
# Line 328-906 in email_worker_lambda.py
def lambda_handler(event, context):
    # ... processing code ...
    
    try:
        # Process all messages
        for record in event["Records"]:
            # ... send emails ...
            
    except Exception as fatal_error:
        # 🔴 THIS CATCHES ALL ERRORS!
        logger.error(f"❌ FATAL ERROR IN LAMBDA HANDLER")
        logger.error(f"Exception Type: {type(fatal_error).__name__}")
        logger.error(f"Exception Message: {str(fatal_error)}")
        logger.exception(f"Full Stack Trace:")
        logger.error(f"⚠️  RETURNING SUCCESS TO PREVENT MESSAGE RE-DELIVERY")
    
    # 🟢 ALWAYS RETURNS SUCCESS (200) - Even on errors!
    return {"statusCode": 200, "body": json.dumps(results)}
```

**The Issue:** Because you're catching all exceptions and returning success (200), Lambda thinks the function succeeded, so it **shouldn't** be triggering the built-in `Errors` metric.

---

## Where Lambda Function Errors CAN Come From

### Scenario 1: Errors in Inner Exception Handlers

Your code has nested try-catch blocks. If an error happens that's NOT caught properly, it will bubble up:

```python
# Lines 336-731 - Inside the message loop
for idx, record in enumerate(event["Records"], 1):
    try:
        # Parse message
        message = json.loads(record["body"])
        campaign_id = message.get("campaign_id")
        contact_email = message.get("contact_email")
        
        if not campaign_id or not contact_email:
            raise ValueError("Missing campaign_id or contact_email in message")  # 🔴 This is caught
        
        # Get campaign from DynamoDB
        campaign_response = campaigns_table.get_item(
            Key={"campaign_id": campaign_id}
        )
        
        if "Item" not in campaign_response:
            raise ValueError(f"Campaign {campaign_id} not found in DynamoDB")  # 🔴 This is caught
        
        # ... more processing ...
        
    except Exception as e:
        # These are caught and logged, NOT re-raised
        logger.error(f"Error processing message {idx}: {str(e)}")
        results["failed"] += 1
        results["errors"].append(error_msg)
        continue  # Move to next message
```

**These errors are caught and DON'T trigger Lambda function errors.**

### Scenario 2: Errors Outside Try-Catch Blocks

If there's an error BEFORE the main try block or in the cleanup code:

```python
def lambda_handler(event, context):
    start_time = datetime.now()
    
    # 🔴 IF ERROR HAPPENS HERE (before line 329), it's NOT caught!
    # Example: If event["Records"] doesn't exist
    logger.info(f"Processing {len(event['Records'])} messages")  # Line 310
    
    results = {...}
    
    try:
        # Main processing...
```

**Line 310** accesses `event["Records"]` BEFORE the try-catch! If the event is malformed, this will raise an unhandled exception.

### Scenario 3: CloudWatch Metric Filter

Your alarm might be using a **Log Metric Filter** instead of the built-in Lambda errors. This would trigger on log patterns like:

- `[ERROR]`
- `Exception`
- `Traceback`
- `FATAL ERROR`

---

## 2. Custom CloudWatch Metrics 📊

Your code DOES send custom error metrics manually:

### Location: `send_cloudwatch_metric()` function (Lines 230-251)

```python
def send_cloudwatch_metric(metric_name, value, unit="Count", dimensions=None):
    """Send custom metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace="EmailWorker/Custom",  # ⚠️ Different namespace!
            MetricData=[metric_data],
        )
    except Exception as e:
        logger.warning(f"Failed to send CloudWatch metric {metric_name}: {str(e)}")
```

### Custom Metrics Sent by Your Code:

| Metric Name | When Sent | Line Numbers |
|------------|-----------|--------------|
| `IncompleteCampaigns` | Campaign not fully sent | 283-288 |
| `ThrottleExceptions` | SES rate limit hit | 606-611 |
| `EmailsFailed` | Failed email sends | 816 |
| `FailureRate` | High failure percentage | 835 |
| `ThrottleExceptionsInBatch` | Multiple throttles in batch | 844-849 |
| `SESValidationErrors` | Email validation failures | 1243, 1299, 1724, 1745, 1776, 1898 |

**NOTE:** These are in the `EmailWorker/Custom` namespace, NOT `AWS/Lambda` namespace!

---

## How to Find What's Triggering Your Alarm 🔍

### Step 1: Check the Alarm Configuration

Run this to see what metric the alarm is monitoring:

```bash
aws cloudwatch describe-alarms --alarm-names EmailWorker-FunctionErrors
```

Look for:
- **Namespace**: Is it `AWS/Lambda` or `EmailWorker/Custom`?
- **MetricName**: Is it `Errors` or a custom metric?
- **Dimensions**: What Lambda function is it monitoring?

### Step 2: Check for Log Metric Filters

```bash
aws logs describe-metric-filters --log-group-name /aws/lambda/YOUR-FUNCTION-NAME
```

This will show if there's a metric filter converting log patterns into metrics.

### Step 3: Run the Diagnostic Script

```bash
python diagnose_emailworker_errors.py 24 your-function-name
```

This will show you:
- All error logs from the Lambda function
- When errors occurred
- What types of errors (KeyError, ValueError, etc.)

---

## Most Likely Causes of Your Alarms

Based on the code analysis, here are the most likely sources:

### 1. **Log Metric Filter on Error Patterns** (Most Likely)
- Your alarm is probably configured with a metric filter
- It triggers when it sees `[ERROR]` or `Exception` in logs
- Lines 890-895 log fatal errors that would trigger this

### 2. **Unhandled Exceptions in Event Parsing** (Second Most Likely)
- Line 310: `len(event['Records'])` - if event is malformed
- Line 338: `json.loads(record["body"])` - if body is invalid JSON
- These happen BEFORE the main try-catch block

### 3. **Function Timeout**
- If emails take too long to send, Lambda times out
- This is automatically recorded as a function error

### 4. **Out of Memory**
- Large attachments or many emails could cause OOM
- Automatically recorded as a function error

### 5. **Custom Metrics Misnamed**
- If someone created an alarm on `EmailWorker/Custom` metrics
- These are explicitly sent from lines 283-849

---

## Specific Code Locations That Log Errors

### Fatal Errors (Lines 887-898)
```python
except Exception as fatal_error:
    logger.error(f"❌ FATAL ERROR IN LAMBDA HANDLER")  # 🔴 Triggers log metric filter
    logger.error(f"Exception Type: {type(fatal_error).__name__}")
    logger.error(f"Exception Message: {str(fatal_error)}")
    logger.exception(f"Full Stack Trace:")  # 🔴 Triggers log metric filter
```

### Message Processing Errors (Lines 673-731)
```python
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "Unknown")
    error_msg = f"AWS error ({error_code}): {str(e)}"
    logger.error(f"[Message {idx}] {error_msg}")  # 🔴 Triggers log metric filter
    results["failed"] += 1
    results["errors"].append(error_msg)
```

### Campaign Not Found (Lines 362-366)
```python
if "Item" not in campaign_response:
    logger.error(f"[Message {idx}] Campaign {campaign_id} not found in DynamoDB")  # 🔴
    raise ValueError(f"Campaign {campaign_id} not found in DynamoDB")  # 🔴 Logged as exception
```

### Missing Required Fields (Lines 347-348)
```python
if not campaign_id or not contact_email:
    raise ValueError("Missing campaign_id or contact_email in message")  # 🔴
```

---

## How to Fix/Reduce the Alarms

### Option 1: Fix the Actual Errors
Run the diagnostic script to find what's failing, then fix:
- Missing campaign_id or contact_email in SQS messages
- Campaigns not found in DynamoDB
- Invalid email addresses
- SES throttling issues

### Option 2: Adjust Alarm Threshold
If errors are expected/acceptable:
```bash
# Increase threshold from current value
aws cloudwatch put-metric-alarm \
    --alarm-name EmailWorker-FunctionErrors \
    --threshold 10 \  # Instead of 5
    --evaluation-periods 2
```

### Option 3: Add Better Error Handling
Prevent certain errors from being logged as ERROR:
```python
# Change from ERROR to WARNING for expected issues
if "Item" not in campaign_response:
    logger.warning(f"Campaign {campaign_id} not found (possibly deleted)")  # ⚠️ WARNING not ERROR
    results["failed"] += 1
    continue
```

### Option 4: Remove the Outer Try-Catch
Let Lambda naturally fail on fatal errors:
```python
def lambda_handler(event, context):
    # Remove the outer try-catch on line 328
    # Let unhandled exceptions fail naturally
    # This prevents silent failures
```

---

## Summary

**Your errors are being sent to CloudWatch through:**

1. ✅ **Logger calls**: `logger.error()`, `logger.exception()` → Creates log entries
2. ✅ **Custom metrics**: `send_cloudwatch_metric()` → Sends to `EmailWorker/Custom` namespace
3. ⚠️ **Potential unhandled exceptions**: Outside the try-catch (lines 308-327)
4. ⚠️ **Log metric filters**: Converting ERROR logs → CloudWatch metrics

**To find the root cause, run:**
```bash
python diagnose_emailworker_errors.py 24 your-function-name
```

This will show you exactly what errors are occurring and when.


