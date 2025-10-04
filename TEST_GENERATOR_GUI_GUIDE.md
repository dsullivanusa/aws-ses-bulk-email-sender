# 🧪 Test Contact Generator GUI - User Guide

## Overview
A modern GUI application to generate thousands of test contacts with the same email address but unique IDs for load testing your email campaign system.

## Features

### ✨ Key Capabilities
- **Visual Interface**: Easy-to-use GUI with all configuration options
- **Real-time Progress**: Live progress bar, statistics, and ETA
- **Flexible Configuration**: Customize all contact fields and AWS settings
- **Thread-safe**: Runs generation in background thread (UI stays responsive)
- **Cancellable**: Stop generation at any time
- **Detailed Logging**: Real-time log with timestamps
- **Error Handling**: Graceful error handling and reporting

### 📊 Statistics Display
- **Imported Count**: Number of contacts successfully created
- **Rate**: Contacts created per second
- **ETA**: Estimated time remaining
- **Errors**: Count of failed insertions

## How to Use

### Method 1: Direct Launch
```bash
python generate_test_contacts_gui.py
```

### Method 2: Via Launcher (Windows)
Double-click: `launch_test_generator.bat`

### Method 3: From Original Script
```bash
python generate_test_contacts.py
# Then select option 2 or type 'gui'
```

## GUI Sections

### 1. Configuration Panel
- **AWS Region**: Your AWS region (default: us-gov-west-1)
- **DynamoDB Table**: Target table name (default: EmailContactsNew)
- **Test Email**: Email address for all test contacts
- **Number of Contacts**: How many contacts to generate (1-100000+)

### 2. Contact Template
Customize the contact data used for all test contacts:
- Personal info (first name, last name, title)
- Organization (entity type, agency, sector)
- Location (state, region)
- Contact details (phone)

### 3. Contact Flags
Boolean checkboxes for:
- MS-ISAC Member
- SOC Call
- Fusion Center
- K-12
- Water/Wastewater
- Weekly Rollup

### 4. Progress Section
Real-time display of:
- Progress bar (0-100%)
- Statistics (imported, rate, ETA, errors)
- Current status message

### 5. Log Panel
Scrollable log with:
- Timestamped messages
- Progress milestones (every 1000 contacts)
- Error messages (first 5 shown)
- Final summary

## Workflow

### Step 1: Configure Settings
1. Set AWS region and table name
2. Enter test email address
3. Set number of contacts to generate
4. Customize contact template (optional)
5. Check/uncheck contact flags (optional)

### Step 2: Generate
1. Click **"🚀 Start Generation"**
2. Confirm the action in the dialog
3. Watch real-time progress
4. Wait for completion or cancel if needed

### Step 3: Results
- Success message shows total contacts created
- Log displays detailed statistics
- Contacts are ready for load testing

## Button Functions

| Button | Function |
|--------|----------|
| 🚀 Start Generation | Begin creating test contacts |
| 🛑 Cancel | Stop generation (asks for confirmation) |
| 🗑️ Clear Log | Clear the log panel |
| ❌ Exit | Close the application |

## Important Notes

### ⚠️ Warnings
- **Large batches**: Generating 10,000+ contacts may take several minutes
- **DynamoDB costs**: Each contact is a write operation (monitor AWS costs)
- **Table schema**: Ensure your table has `contact_id` as primary key (not `email`)

### 📝 Best Practices
1. **Start small**: Test with 100-1000 contacts first
2. **Monitor logs**: Watch for errors during generation
3. **Verify table**: Check DynamoDB after generation completes
4. **Check AWS credentials**: Ensure boto3 has valid AWS credentials

### ⚡ Performance
- **Rate**: Typically 200-400 contacts/second
- **10,000 contacts**: ~30-50 seconds
- **100,000 contacts**: ~5-8 minutes

## Verification

After generation completes, verify in AWS:

```bash
# Count total contacts
aws dynamodb scan --table-name EmailContactsNew \
  --select COUNT --region us-gov-west-1

# Query specific email
aws dynamodb query --table-name EmailContactsNew \
  --index-name email-index \
  --key-condition-expression "email = :email" \
  --expression-attribute-values '{":email":{"S":"test@example.com"}}' \
  --region us-gov-west-1
```

## Troubleshooting

### Issue: GUI doesn't launch
**Solution**: Ensure tkinter is installed
```bash
# Usually included with Python
# If missing on Linux:
sudo apt-get install python3-tk
```

### Issue: boto3 not found
**Solution**: Install AWS SDK
```bash
pip install boto3
```

### Issue: Access Denied errors
**Solution**: Check AWS credentials and IAM permissions
```bash
# Configure AWS credentials
aws configure

# Required permissions:
# - dynamodb:PutItem
# - dynamodb:BatchWriteItem
```

### Issue: Table not found
**Solution**: Create the table first or update table name in GUI

### Issue: Generation is slow
**Solution**: 
- Check network connection
- Verify DynamoDB region
- Check AWS service health status

## Advanced Usage

### Custom Batch Size
The app uses DynamoDB's maximum batch size (25 items) automatically. This is optimal for performance.

### Multiple Runs
You can run the generator multiple times to add more contacts to the same table. Each run creates unique contact IDs.

### Different Emails
Run multiple times with different email addresses to create diverse test datasets.

## Support

For issues or questions:
1. Check the log panel for error messages
2. Verify AWS credentials and permissions
3. Check DynamoDB table schema
4. Review AWS service quotas

## File Structure

```
generate_test_contacts.py          - Original CLI script (with GUI launcher)
generate_test_contacts_gui.py      - GUI application (main file)
launch_test_generator.bat          - Windows launcher
TEST_GENERATOR_GUI_GUIDE.md        - This guide
```

## Requirements

- Python 3.7+
- boto3
- tkinter (usually included with Python)
- Valid AWS credentials
- DynamoDB table with contact_id as primary key

---

**Ready to load test!** 🚀

