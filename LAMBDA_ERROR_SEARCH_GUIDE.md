# Lambda Error Search with Source Code Mapping

## 🎯 Purpose
This tool searches CloudWatch Logs for Lambda errors and maps them back to the exact lines in your source code, making debugging much faster and easier.

## 🚀 Quick Start

### Basic Usage
```bash
# Interactive mode - will prompt you to select a function
python search_lambda_errors_with_code.py

# Search specific function (last 1 hour)
python search_lambda_errors_with_code.py email-worker-function

# Search specific function (last 24 hours)
python search_lambda_errors_with_code.py email-worker-function 24

# Search with custom region
python search_lambda_errors_with_code.py email-worker-function 24 us-gov-west-1
```

## 📊 What It Finds

### 1. **Stack Trace Errors**
- Python exceptions with full stack traces
- Shows the exact file and line number
- Displays source code context (5 lines before/after)
- Groups similar errors together
- Shows all timestamps when the error occurred

### 2. **Timeout Errors**
- Lambda function timeouts
- "Task timed out after X seconds"
- Suggests increasing timeout or optimizing code

### 3. **Memory Errors**
- Out of memory errors
- "Runtime exited" errors
- Suggests increasing memory allocation

## 📋 Output Example

```
================================================================================
ERROR GROUP #1: KeyError: | email_worker_lambda.py:345
Occurrences: 5
================================================================================

🕐 Most Recent: 2025-01-08 14:23:45
🏷️  Error Type: KeyError:
💬 Message: 'campaign_id'

📅 All Occurrences:
    - 2025-01-08 14:20:12
    - 2025-01-08 14:21:33
    - 2025-01-08 14:22:45
    - 2025-01-08 14:23:12
    - 2025-01-08 14:23:45

📍 Stack Trace (from top to bottom):

  📄 File: email_worker_lambda.py, Line: 345

  Source Code Context:
  ----------------------------------------------------------------------------
      340 | def lambda_handler(event, context):
      341 |     """Process SQS messages and send emails"""
      342 |     
      343 |     for record in event['Records']:
      344 |         message = json.loads(record['body'])
  >>> 345 |         campaign_id = message['campaign_id']  # ← ERROR HERE
      346 |         contact_email = message['contact_email']
      347 |         
      348 |         # Process message
      349 |         send_email(campaign_id, contact_email)
      350 |
  ----------------------------------------------------------------------------
```

## 🔍 Error Types That Trigger CloudWatch Alarms

The `EmailWorker-FunctionErrors` alarm triggers on:

| Error Type | Description | How to Find |
|------------|-------------|------------|
| **Unhandled Exceptions** | Python exceptions not caught | Shows in stack traces |
| **Lambda Timeout** | Execution exceeds timeout | "Task timed out" message |
| **Out of Memory** | Memory limit exceeded | "Runtime exited" message |
| **Import Errors** | Module import failures | Runtime.ImportModuleError |

## 💡 Common Errors and Solutions

### KeyError / IndexError
**Problem:** Accessing dictionary key or list index that doesn't exist  
**Solution:** Add error handling or validate data structure first
```python
# Bad
campaign_id = message['campaign_id']

# Good
campaign_id = message.get('campaign_id')
if not campaign_id:
    logger.error("Missing campaign_id in message")
    return
```

### Timeout Errors
**Problem:** Lambda execution exceeds configured timeout  
**Solution:** 
- Increase Lambda timeout (max 15 minutes)
- Optimize slow operations (database queries, API calls)
- Process in smaller batches

### Memory Errors
**Problem:** Lambda runs out of allocated memory  
**Solution:**
- Increase Lambda memory allocation
- Optimize memory usage (clear large variables)
- Process data in chunks instead of loading all at once

### AttributeError
**Problem:** Trying to access attribute that doesn't exist  
**Solution:** Check object type and add defensive coding
```python
# Bad
email = contact.email

# Good
email = getattr(contact, 'email', None)
if not email:
    logger.warning(f"Contact missing email attribute")
    return
```

## 📂 Source Code Mapping

The script searches for source files in these locations:
1. Current directory
2. Relative path from current directory
3. Working directory path

Make sure to run the script from your project root directory (where `email_worker_lambda.py` is located).

## 💾 Save Reports

The script offers to save detailed reports to a file:
- File name format: `lambda_errors_<function-name>_<timestamp>.txt`
- Contains all error details, stack traces, and source code
- Easy to share with team or attach to tickets

## 🔧 Advanced Usage

### Search for Specific Error Patterns

You can modify the script to search for specific patterns. Edit line 62 in the script:

```python
# Search for all errors
events = self.get_log_events()

# Search for specific pattern (e.g., only timeout errors)
events = self.get_log_events(filter_pattern='Task timed out')

# Search for specific exception type
events = self.get_log_events(filter_pattern='KeyError')
```

### Adjust Source Code Context

Edit line 204 to change how many lines of context to show:

```python
# Show 10 lines before and after error
code_context = self.get_source_code_context(file_info['file'], file_info['line'], context_lines=10)
```

## 🚨 Troubleshooting

### "Log group not found"
**Problem:** Lambda function hasn't been invoked yet  
**Solution:** Trigger the Lambda at least once to create logs

### "Source file not found locally"
**Problem:** Script can't find the source file  
**Solution:** 
- Run script from project root directory
- Check that file names match between Lambda and local
- File might be in Lambda layer (not available locally)

### "No log events found"
**Problem:** No logs in specified time range  
**Solution:**
- Increase time range (e.g., 24 hours instead of 1)
- Check if Lambda is actually being invoked
- Verify you're looking at the correct function

## 📱 Integration with Existing Tools

This script complements other tools:

```bash
# 1. Find errors with source code mapping
python search_lambda_errors_with_code.py email-worker-function 24

# 2. View live logs
python tail_lambda_logs.py email-worker-function

# 3. Check CloudWatch alarms status
python cloudwatch_alarms_setup.py
```

## 🎓 Best Practices

1. **Run regularly:** Check for errors daily or after deployments
2. **Set time range appropriately:** Use 24-48 hours for comprehensive search
3. **Group similar errors:** Script automatically groups - focus on unique error patterns
4. **Fix root causes:** Don't just fix symptoms - understand why errors occur
5. **Save reports:** Keep history of errors for pattern analysis

## 📈 Understanding Error Frequency

The script shows occurrence count for each error type:

- **1-2 occurrences:** Likely edge case or one-off issue
- **5-10 occurrences:** Intermittent issue - investigate conditions
- **50+ occurrences:** Systemic problem - high priority fix needed
- **Thousands:** Critical issue affecting many users - urgent fix required

## 🔗 Related Files

- `tail_lambda_logs.py` - Real-time log viewing
- `view_lambda_errors.py` - Basic error viewer (no source mapping)
- `check_lambda_logs.py` - Simple log checker
- `cloudwatch_alarms_setup.py` - Alarm configuration

## ⚡ Quick Commands

```bash
# Common functions to search
python search_lambda_errors_with_code.py email-worker-function
python search_lambda_errors_with_code.py BulkEmailAPI
python search_lambda_errors_with_code.py campaign-monitor-function

# Recent errors (last hour)
python search_lambda_errors_with_code.py email-worker-function 1

# Full day search
python search_lambda_errors_with_code.py email-worker-function 24

# Weekly search
python search_lambda_errors_with_code.py email-worker-function 168
```

## 🎯 Pro Tips

1. **Run before deployments:** Establish baseline of current errors
2. **Run after deployments:** Verify no new errors introduced
3. **Compare reports:** Save reports before/after to compare
4. **Focus on new errors:** Recurring errors might already be known
5. **Check error times:** Correlate with deployment times or events
6. **Look for patterns:** Do errors happen at specific times?
7. **Check all functions:** Errors in one function might affect others

---

**Need help?** Check the error summary at the end of each search for suggestions and next steps.

