# 🔍 Lambda Error Monitoring Scripts

Two Python scripts to help monitor and debug your Lambda functions.

## 📋 Scripts

### 1. `view_lambda_errors.py` - Error Analysis Tool
Analyzes CloudWatch logs and categorizes errors, exceptions, warnings, timeouts, and memory issues.

### 2. `tail_lambda_logs.py` - Real-Time Log Viewer
Tails Lambda logs in real-time (like `tail -f` for Linux).

---

## 🚀 Quick Start

### View Errors (Interactive)
```bash
python view_lambda_errors.py
```
- Lists all Lambda functions
- Select by number or name
- Shows errors from last 1 hour

### View Errors (Direct)
```bash
python view_lambda_errors.py BulkEmailAPI
```

### View Errors (Custom Time Range)
```bash
python view_lambda_errors.py BulkEmailAPI 24
```
Shows errors from last 24 hours

### View All Errors (No Limit)
```bash
python view_lambda_errors.py BulkEmailAPI 24 --all
```

### Tail Logs in Real-Time
```bash
python tail_lambda_logs.py BulkEmailAPI
```
Press Ctrl+C to stop

### Tail Without Following
```bash
python tail_lambda_logs.py BulkEmailAPI --no-follow
```
Shows recent logs and exits

---

## 📊 Features

### view_lambda_errors.py

**Categorizes Issues:**
- 🔴 **Exceptions** - Python exceptions and tracebacks
- 🟠 **Errors** - General errors
- 🟡 **Warnings** - Warning messages
- ⏱️ **Timeouts** - Lambda timeout errors
- 💾 **Memory Errors** - Out of memory issues

**Summary Report:**
```
📊 ERROR SUMMARY
=====================================
🔴 Exceptions: 5
🟠 Errors: 12
🟡 Warnings: 3
⏱️  Timeouts: 0
💾 Memory Errors: 0

📈 Total Issues Found: 20
```

**Save to File:**
- Option to save detailed logs to a timestamped file
- Format: `lambda_errors_<function>_<timestamp>.log`

### tail_lambda_logs.py

**Real-Time Features:**
- 🚀 Start events (green)
- ✅ End events (green)
- 📊 Report events (blue)
- 🔴 Errors/Exceptions (red)
- 🟡 Warnings (yellow)
- 📝 Info messages

---

## 🎯 Common Use Cases

### 1. Debug After Deployment
```bash
# Deploy your Lambda
python update_bulk_email_lambda.py

# Watch logs in real-time
python tail_lambda_logs.py BulkEmailAPI
```

### 2. Investigate Production Issues
```bash
# Check last 24 hours for errors
python view_lambda_errors.py BulkEmailAPI 24
```

### 3. Monitor Campaign Processing
```bash
# Tail the email worker Lambda
python tail_lambda_logs.py EmailWorkerLambda
```

### 4. Troubleshoot API Errors
```bash
# View all errors from API Lambda
python view_lambda_errors.py BulkEmailAPI 1 --all
```

---

## 🔧 Requirements

```bash
pip install boto3
```

### AWS Credentials
Make sure you have AWS credentials configured:
```bash
aws configure
```

Or use environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

---

## 📝 Example Output

### view_lambda_errors.py
```
🔍 Lambda Function Error Viewer
=====================================

🎯 Selected Lambda: BulkEmailAPI
⏰ Time range: Last 1 hour(s)
🔍 Fetching logs from 2025-10-06 10:00:00 to 2025-10-06 11:00:00
📊 Found 3 log streams
📦 Total log events: 245

📊 ERROR SUMMARY
=====================================
🔴 Exceptions: 2
🟠 Errors: 5
🟡 Warnings: 1
⏱️  Timeouts: 0
💾 Memory Errors: 0

📈 Total Issues Found: 8

=====================================
🔴 EXCEPTIONS
=====================================

[1] 2025-10-06 10:15:23
--------------------------------------------------------------------------------
Traceback (most recent call last):
  File "/var/task/lambda_function.py", line 123, in handler
    result = process_email(event)
  File "/var/task/lambda_function.py", line 456, in process_email
    contact = contacts_table.get_item(Key={'email': email})
KeyError: 'email'
```

### tail_lambda_logs.py
```
🔍 Tailing logs for: BulkEmailAPI
📋 Log group: /aws/lambda/BulkEmailAPI
=====================================
🚀 [10:15:20] START RequestId: abc-123 Version: $LATEST
📝 [10:15:21] Received campaign request with 50 email addresses
📝 [10:15:22] Campaign targeting 50 contacts (All Contacts)
📝 [10:15:23] Queuing 50 contacts to SQS for campaign campaign_1728219323
✅ [10:15:24] END RequestId: abc-123
📊 [10:15:24] REPORT RequestId: abc-123 Duration: 1234.56 ms Billed Duration: 1300 ms Memory Size: 512 MB Max Memory Used: 128 MB
```

---

## 💡 Tips

1. **Find Your Lambda Name:**
   ```bash
   python view_lambda_errors.py
   # Lists all functions
   ```

2. **Check Specific Error Types:**
   ```bash
   # Search for specific patterns in logs
   grep -i "timeout" lambda_errors_*.log
   ```

3. **Monitor During Testing:**
   ```bash
   # In one terminal: tail logs
   python tail_lambda_logs.py BulkEmailAPI
   
   # In another terminal: test your app
   ```

4. **Compare Before/After Deployment:**
   ```bash
   # Before
   python view_lambda_errors.py BulkEmailAPI 24 > before.log
   
   # Deploy changes
   python update_bulk_email_lambda.py
   
   # After
   python view_lambda_errors.py BulkEmailAPI 1 > after.log
   ```

---

## 🆘 Troubleshooting

**"No log events found"**
- Lambda hasn't been invoked recently
- Increase time range: `python view_lambda_errors.py FunctionName 24`

**"Log group not found"**
- Lambda function hasn't been invoked at least once
- Check function name spelling

**"Access Denied"**
- Your AWS credentials need CloudWatch Logs read permissions
- Add `logs:DescribeLogGroups`, `logs:DescribeLogStreams`, `logs:FilterLogEvents` permissions

---

## 📚 Related Scripts

- `check_lambda_logs.py` - Check logs for specific Lambda
- `list_lambda_functions.py` - List all Lambda functions
- `update_bulk_email_lambda.py` - Deploy Lambda updates

---

**Happy Debugging! 🐛🔍**

