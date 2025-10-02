# Batch CSV Import Guide - For 20,000+ Contacts

## Overview

The new batch import feature can handle CSV files with 20,000+ contacts efficiently:
- ✅ **Fast:** Completes in ~5-10 minutes (vs 5-10 hours with old method)
- ✅ **Progress Bar:** Real-time progress tracking
- ✅ **Cancellable:** Stop anytime, progress is saved
- ✅ **Efficient:** Processes 25 contacts per batch (DynamoDB limit)
- ✅ **Reliable:** Automatic error handling and retry logic

## How It Works

### Old Method (Single Contact):
```
20,000 contacts × 1-2 seconds each = 5-10 HOURS ❌
```

### New Method (Batch Processing):
```
20,000 contacts ÷ 25 per batch = 800 batches
800 batches × 0.5 seconds each = ~7 MINUTES ✅
```

## Setup Instructions

### Step 1: Update Lambda Function
```bash
# Upload the updated bulk_email_api_lambda.py to Lambda
python update_lambda.py
```

### Step 2: Add Batch Endpoint to API Gateway
```bash
# Run the automated script
python add_batch_endpoint.py
```

This script will:
- Find your existing API Gateway
- Create `/contacts/batch` endpoint
- Configure Lambda integration
- Set up CORS
- Deploy to prod stage

### Step 3: Verify Setup
Test the batch endpoint:
```bash
curl -X POST https://YOUR-API-ID.execute-api.us-gov-west-1.amazonaws.com/prod/contacts/batch \
  -H "Content-Type: application/json" \
  -d '{"contacts":[{"email":"test@example.com","first_name":"Test","last_name":"User"}]}'
```

Expected response:
```json
{"success": true, "imported": 1, "unprocessed": 0}
```

## Using Batch Import

### 1. Prepare Your CSV

**Required Columns:**
- `email` - Must be present in every row

**Recommended Columns:**
- `first_name`, `last_name` - For personalization
- `group` - For filtering and campaigns

**All Available Columns:**
```csv
email,first_name,last_name,title,entity_type,state,agency_name,sector,subsection,phone,ms_isac_member,soc_call,fusion_center,k12,water_wastewater,weekly_rollup,alternate_email,region,group
```

### 2. Import Process

1. **Open Web UI**
   - Navigate to Contact Management tab

2. **Click "Upload CSV (Batch)"**
   - Select your CSV file
   - Progress bar will appear

3. **Monitor Progress**
   - Real-time progress bar shows: "Batch X/Y - Imported: Z, Errors: E"
   - Console (F12) shows detailed logs

4. **Complete**
   - Alert shows final count
   - Contacts auto-load
   - Groups refresh automatically

### 3. Progress Indicators

**Progress Bar Shows:**
```
CSV Import Progress
████████░░ 75%
Batch 600/800 - Imported: 14,850, Errors: 25 (14,850 / 20,000)
[Cancel Import]
```

**Console Logs Show:**
```
Starting batch CSV upload... contacts.csv
Total lines in CSV: 20001
Parsed 20000 valid contacts from CSV
Processing batch 1/800: contacts 1-25
✓ Batch 1 complete: +25 imported, 0 failed
Processing batch 2/800: contacts 26-50
✓ Batch 2 complete: +25 imported, 0 failed
...
```

## Performance Benchmarks

| Contacts | Batches | Time (approx) | Old Method Time |
|----------|---------|---------------|-----------------|
| 100 | 4 | ~3 seconds | ~2 minutes |
| 1,000 | 40 | ~30 seconds | ~20 minutes |
| 5,000 | 200 | ~2 minutes | ~2 hours |
| 10,000 | 400 | ~4 minutes | ~4 hours |
| 20,000 | 800 | ~7 minutes | ~8 hours |
| 50,000 | 2,000 | ~18 minutes | ~20 hours |

## Features

### Real-Time Progress
- Progress bar updates after each batch
- Shows imported count and errors
- Displays batch number and percentage

### Cancel Anytime
- Click "Cancel Import" button
- Confirmation dialog appears
- All contacts imported up to that point are saved
- Remaining contacts are not processed

### Error Handling
- Each batch is independent
- If one batch fails, others continue
- Final report shows total imported vs errors
- Check console for detailed error messages

### Resumable
- If cancelled or interrupted, already-imported contacts are saved
- Can re-run import with same or different CSV
- Duplicate emails will be updated (not duplicated)

## Troubleshooting

### Issue 1: Endpoint Not Found (404)

**Cause:** `/contacts/batch` endpoint not added to API Gateway

**Solution:**
```bash
python add_batch_endpoint.py
```

### Issue 2: Progress Bar Stuck

**Cause:** Large file being parsed

**Check:**
- Open Console (F12)
- Look for "Parsed X valid contacts from CSV"
- Wait for parsing to complete

### Issue 3: All Batches Failing

**Cause:** Lambda function not updated or permission issue

**Solution:**
1. Verify Lambda function is updated
2. Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/bulk_email_api_lambda --follow --region us-gov-west-1
```

### Issue 4: Slow Performance

**Expected:** ~0.5 seconds per batch (25 contacts)

**If slower:**
- Check Lambda concurrent execution limits
- Check DynamoDB write capacity
- Check network connection

### Issue 5: Some Contacts Not Imported

**Check:**
- CSV format is correct (no missing columns)
- All rows have email addresses
- No special characters causing parsing issues
- Console logs show which rows failed

## Advanced Usage

### Import Multiple Files
You can import multiple CSV files sequentially:
1. Import first file → wait for completion
2. Import second file → wait for completion
3. Groups and contacts will merge automatically

### Update Existing Contacts
- If email already exists in DynamoDB, it will be **updated**
- New fields will overwrite old values
- Use this to bulk-update contact information

### Cancel and Resume
```
1. Import 20,000 contacts
2. Cancel after 5,000 imported
3. Fix remaining CSV data
4. Re-import updated CSV
5. Only new/changed contacts will be processed
```

## API Details

### Endpoint
```
POST /contacts/batch
```

### Request Format
```json
{
  "contacts": [
    {
      "email": "user1@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "group": "State CISOs"
    },
    {
      "email": "user2@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "group": "City Managers"
    }
    // ... up to 25 contacts per request
  ]
}
```

### Response Format
```json
{
  "success": true,
  "imported": 25,
  "unprocessed": 0
}
```

### Limits
- **Maximum per batch:** 25 contacts (DynamoDB limit)
- **Maximum total:** No limit (unlimited batches)
- **Timeout:** 29 seconds per batch (API Gateway limit)

## Best Practices

### 1. Test With Small File First
```csv
email,first_name,last_name,group
test1@example.com,Test,User1,TestGroup
test2@example.com,Test,User2,TestGroup
```

### 2. Clean Your Data Before Import
- Remove duplicate emails
- Verify column headers match expected names
- Check for special characters
- Ensure consistent formatting

### 3. Monitor First Import
- Watch progress bar
- Check console for errors
- Verify contacts appear in table

### 4. Large Imports (20,000+)
- Keep browser tab active
- Don't close laptop/sleep computer
- Stable internet connection
- Can take 5-15 minutes

### 5. Backup Before Major Updates
Export existing contacts before doing bulk update imports:
- Use DynamoDB export feature
- Or use `Load Contacts` to verify existing data

## Comparison: Old vs New

| Feature | Old Method | New Method |
|---------|-----------|------------|
| 20,000 contacts | 5-10 hours | 5-10 minutes |
| Progress tracking | None | Real-time bar |
| Cancellable | No | Yes |
| Browser timeout | Likely | No risk |
| Error recovery | Start over | Continue from failure |
| Efficiency | 1 per request | 25 per request |
| Cost | High (20K API calls) | Low (800 API calls) |

## Next Steps

After successful import:
1. ✅ Click "Load Contacts" to verify
2. ✅ Check "Filter by Group" dropdown
3. ✅ Go to Send Campaign tab
4. ✅ Test "Target Group" dropdown
5. ✅ Send test campaign to one group

## Support

If you encounter issues:
1. Check browser console (F12) for detailed errors
2. Check Lambda CloudWatch logs
3. Verify API Gateway endpoints are deployed
4. Test with small CSV file first
5. Review this guide's troubleshooting section

