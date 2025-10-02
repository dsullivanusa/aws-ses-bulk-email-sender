# CSV Import Troubleshooting Guide

## Changes Made to Fix CSV Import

I've improved the CSV import functionality with:

1. ✅ **Better CSV Parsing** - Now handles quoted fields with commas
2. ✅ **Detailed Logging** - Shows what's happening in browser console
3. ✅ **Error Reporting** - Shows which rows failed and why
4. ✅ **Column Validation** - Checks if column counts match

## How to Use CSV Import

### Step 1: Prepare Your CSV File

Your CSV file should have these columns (order doesn't matter):

**Required:**
- `email` - Email address (required)
- `first_name` - First name
- `last_name` - Last name

**Optional (but recommended):**
- `group` - Group name for filtering
- `state` - State code (e.g., CA, NY, TX)
- `agency_name` - Agency or organization name

**All Available Fields:**
- `email`, `first_name`, `last_name`, `title`, `entity_type`, `state`, `agency_name`, `sector`, `subsection`, `phone`, `ms_isac_member`, `soc_call`, `fusion_center`, `k12`, `water_wastewater`, `weekly_rollup`, `alternate_email`, `region`, `group`

### Step 2: CSV Format Examples

**Simple CSV (Minimum):**
```csv
email,first_name,last_name,group
john@example.com,John,Doe,State CISOs
jane@example.com,Jane,Smith,City Managers
```

**Full CSV:**
```csv
email,first_name,last_name,title,state,agency_name,group
john@example.com,John,Doe,IT Director,CA,CA Office of Tech,State CISOs
jane@example.com,Jane,Smith,Security Manager,NY,NYC IT Dept,City Managers
```

### Step 3: Import Process

1. **Update Lambda Function**
   - Deploy the updated `bulk_email_api_lambda.py` with improved CSV handling

2. **Open Web UI**
   - Go to Contact Management tab
   - Click "Upload CSV" button
   - Select your CSV file

3. **Monitor Progress**
   - Open Browser Console (F12)
   - Watch the upload progress in console logs
   - Check for any errors

4. **Review Results**
   - An alert will show how many contacts were imported
   - Any errors will be listed
   - Console shows detailed information about each row

## Troubleshooting

### Problem 1: "0 contacts imported"

**Check Console Logs:**
1. Press F12 to open Developer Tools
2. Go to Console tab
3. Look for these messages:

```
Starting CSV upload...
Total lines in CSV: X
CSV Headers: [...]
Row 1: Processing contact email@example.com
```

**Common Causes:**

**A. Wrong CSV format**
- Make sure first row is headers
- Headers should match expected field names
- Use comma as delimiter (not semicolon or tab)

**B. Column count mismatch**
```
Row 5: Column count mismatch. Got 15, expected 19
```
Solution: Make sure every row has the same number of columns as the header

**C. Missing email address**
```
Row 3: No email address found
```
Solution: Every row must have a valid email in the email column

**D. API endpoint issues**
```
Row 1: Failed to import john@example.com 404
```
Solution: Make sure Lambda function is deployed and API Gateway is configured

### Problem 2: "Column count mismatch"

This happens when a row has more or fewer columns than the header.

**Solution:**
- Check for commas inside field values - wrap them in quotes:
  ```csv
  email,name,agency
  john@example.com,John Doe,"Department of Tech, City of LA"
  ```
- Make sure all rows have the same number of columns
- Remove any trailing commas

### Problem 3: "API Error 500"

**Check Lambda Logs:**
```bash
aws logs tail /aws/lambda/bulk_email_api_lambda --follow --region us-gov-west-1
```

**Common causes:**
- DynamoDB table doesn't exist
- Lambda doesn't have permissions
- Invalid data format

### Problem 4: Some contacts imported, some failed

**Check the alert message - it will show:**
```
CSV Upload Complete!
Imported: 45 contacts
Errors: 5

First few errors:
Row 23 (test@example.com): 500
Row 45: Missing email address
Row 67: Column count mismatch
```

**Then check browser console for details on each failed row**

## Testing Your CSV Import

### Test 1: Use Sample File
```bash
# Use the provided sample file
# It's located at: sample_contacts_import.csv
```

### Test 2: Create Minimal Test CSV
```csv
email,first_name,last_name,group
test1@example.com,Test,User1,TestGroup
test2@example.com,Test,User2,TestGroup
```

### Test 3: Check Import Results

**In Browser Console:**
```javascript
// After import, check what was loaded
console.log('Loaded contacts:', allContacts.length);
console.log('Loaded groups:', allGroups);
```

**In DynamoDB:**
```bash
aws dynamodb scan \
  --table-name EmailContacts \
  --region us-gov-west-1 \
  --max-items 5
```

## CSV Field Name Aliases

The import function accepts multiple column names for flexibility:

| Standard Field | Also Accepts |
|---------------|--------------|
| email | email_address |
| first_name | firstname, first |
| last_name | lastname, last |
| agency_name | agencyname, agency |
| entity_type | entitytype |
| ms_isac_member | ms-isac, msisac |
| soc_call | soc |
| fusion_center | fusion |
| k12 | k-12 |
| water_wastewater | water/wastewater, water |
| weekly_rollup | weekly, rollup |
| alternate_email | alt_email |
| phone | phone_number |

## Common CSV Issues

### Issue: Excel adds extra columns
Excel sometimes adds empty columns. Solution:
- Save as CSV UTF-8
- Open in text editor to verify format
- Remove trailing commas from each line

### Issue: Special characters not displaying
Solution:
- Save CSV as UTF-8 encoding
- Avoid special characters in field names

### Issue: Line breaks in fields
If you have multi-line text in a field:
```csv
email,notes
john@example.com,"This is a note
with multiple lines"
```
The improved parser now handles this!

## Next Steps After Import

1. **Verify Contacts**
   - Click "Load Contacts" button
   - Check that contacts appear in table
   - Verify group names are correct

2. **Check Groups Dropdown**
   - Groups should automatically populate
   - Both "Filter by Group" and "Target Group" dropdowns

3. **Test Filtering**
   - Select a group from Filter by Group
   - Verify correct contacts are shown

4. **Test Campaign**
   - Go to Send Campaign tab
   - Select a group from Target Group
   - Verify contact count is correct

## Need More Help?

1. Open browser console (F12) during import
2. Check the detailed logs
3. Take a screenshot of any error messages
4. Check Lambda CloudWatch logs for backend errors

