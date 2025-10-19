# EmailWorker CloudWatch Alarm Diagnostics

## Problem
You're receiving many CloudWatch alarms for **EmailWorker-FunctionErrors** and need to identify what events are triggering these alarms.

## Solution

Use the `diagnose_emailworker_errors.py` script to automatically:
- Find the EmailWorker alarms in CloudWatch
- Identify the Lambda function being monitored
- Fetch error logs from CloudWatch Logs
- Analyze and categorize the errors
- Show you what's actually failing

## Usage

### Basic Usage (Last 24 hours)
```bash
python diagnose_emailworker_errors.py
```

### Specify Time Range (e.g., last 48 hours)
```bash
python diagnose_emailworker_errors.py 48
```

### Manually Specify Function Name
If the script can't automatically find the function name:
```bash
python diagnose_emailworker_errors.py 24 email-worker-function
```

## Requirements

1. **Python 3.7+** installed
2. **boto3** library installed:
   ```bash
   pip install boto3
   ```
3. **AWS credentials** configured (one of):
   - AWS CLI configured (`aws configure`)
   - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
   - IAM role attached (if running on EC2)

4. **AWS Permissions** needed:
   - `cloudwatch:DescribeAlarms`
   - `logs:FilterLogEvents`
   - `logs:DescribeLogStreams`
   - `cloudwatch:GetMetricStatistics`
   - `lambda:ListFunctions`

## What This Script Does

### Step 1: Find Alarms
Searches CloudWatch for alarms with "EmailWorker" in the name and shows their current state.

### Step 2: Extract Function Name
Gets the Lambda function name from the alarm's dimensions.

### Step 3: Fetch Error Logs
Queries CloudWatch Logs for error messages, exceptions, and failures in the Lambda function logs.

### Step 4: Analyze Errors
Categorizes errors by type:
- **KeyError** - Missing dictionary keys
- **AttributeError** - Missing object attributes
- **TypeError** - Type mismatches
- **ValueError** - Invalid values
- **Timeout** - Function timeouts
- **Memory Error** - Out of memory issues
- **General Exception** - Other exceptions
- **General Error** - Other errors

### Step 5: Show Summary
Displays:
- Total error count
- Breakdown by error type with percentages
- Sample error messages with timestamps
- Lambda function metrics (invocations, errors, throttles, etc.)

### Step 6: Save Report
Creates a detailed report file: `emailworker_errors_YYYYMMDD_HHMMSS.txt`

## Sample Output

```
================================================================================
EmailWorker CloudWatch Alarm Diagnostics
================================================================================

Finding EmailWorker CloudWatch Alarms...
================================================================================

Found 1 EmailWorker alarm(s):

  [ALARM] EmailWorker-FunctionErrors
      Metric: Errors
      State: ALARM
      Reason: Threshold Crossed: 5 datapoints [10.0, 8.0, ...] were greater than threshold (5.0)
      Lambda Function: email-worker-function

================================================================================
Fetching CloudWatch Logs for: email-worker-function
Time Range: Last 24 hours
================================================================================
From: 2025-10-18 15:30:00
To:   2025-10-19 15:30:00

Found 45 error-related log events

================================================================================
ERROR SUMMARY
================================================================================

Total Errors: 45

  KeyError                 :   28 ( 62.2%)
  AttributeError           :   12 ( 26.7%)
  General Exception        :    5 ( 11.1%)

================================================================================
DETAILED ERROR SAMPLES (Most Recent)
================================================================================

--- KeyError ---

  Example 1 - 2025-10-19 14:22:15
    [ERROR] KeyError: 'recipient_email'
    File "/var/task/email_worker_lambda.py", line 456, in process_message
    recipient = message['recipient_email']
    ...

  Example 2 - 2025-10-19 13:45:33
    [ERROR] KeyError: 'campaign_id'
    ...
```

## Common Issues and Solutions

### 1. No Alarms Found
**Problem:** Script says "No EmailWorker alarms found"

**Solutions:**
- Check you're connected to the correct AWS region
- Verify the alarm name contains "EmailWorker"
- List all alarms: `aws cloudwatch describe-alarms`

### 2. Log Group Not Found
**Problem:** "Log group not found: /aws/lambda/..."

**Solutions:**
- Lambda function hasn't been invoked yet
- Function name is incorrect
- Function was deleted/renamed

### 3. No Error Events Found
**Problem:** "No error events found"

**Possible Reasons:**
- Errors occurred outside the time range (try increasing hours)
- Alarms are based on metrics, not logs
- Error logging is not configured in the Lambda function

### 4. Access Denied
**Problem:** "AccessDeniedException" or "UnauthorizedOperation"

**Solution:** Add these IAM permissions to your AWS user/role:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:DescribeAlarms",
                "cloudwatch:GetMetricStatistics",
                "logs:FilterLogEvents",
                "logs:DescribeLogStreams",
                "lambda:ListFunctions"
            ],
            "Resource": "*"
        }
    ]
}
```

## Next Steps After Diagnosis

1. **Review the most common error types** - Focus on fixing the errors that occur most frequently

2. **Check recent deployments** - If errors started recently, review recent code changes

3. **Examine the source code** - Look at the line numbers mentioned in stack traces

4. **Check input data** - Many errors (KeyError, TypeError) are caused by unexpected input

5. **Monitor in real-time** - Use the tail script to watch logs live:
   ```bash
   python tail_lambda_logs.py email-worker-function
   ```

6. **Review the Lambda configuration**:
   - Memory allocation (if seeing memory errors)
   - Timeout settings (if seeing timeout errors)
   - Environment variables (if seeing KeyError for configs)
   - SQS/SNS triggers (check message formats)

7. **Fix the code** - Update the Lambda function based on findings

8. **Redeploy and monitor** - Deploy fixes and monitor if alarms clear

## Alternative Tools

This repository includes other diagnostic tools you can use:

- **view_lambda_errors.py** - Interactive error viewer
- **search_lambda_errors_with_code.py** - Shows errors with source code context
- **tail_lambda_logs.py** - Real-time log tailing
- **check_lambda_logs.py** - Check specific Lambda logs

## Troubleshooting the Script

If the script fails, try:

1. **Check Python version:**
   ```bash
   python --version  # Should be 3.7+
   ```

2. **Verify boto3 installation:**
   ```bash
   python -c "import boto3; print(boto3.__version__)"
   ```

3. **Test AWS credentials:**
   ```bash
   aws sts get-caller-identity
   ```

4. **Check region:**
   ```bash
   aws configure get region
   ```

5. **Set UTF-8 encoding (Windows):**
   ```powershell
   $env:PYTHONIOENCODING = 'utf-8'
   python diagnose_emailworker_errors.py
   ```

## Support

If you need help:
1. Check the generated report file for detailed error logs
2. Review the CloudWatch Logs console directly
3. Check Lambda function configuration in AWS Console
4. Review recent code changes in the Lambda function

