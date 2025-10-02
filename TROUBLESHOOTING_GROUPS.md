# Troubleshooting: Filter by Group Not Working

## Problem
The "Filter by Group" dropdown in Contact Management and "Target Group" in Send Campaign are not loading groups from DynamoDB.

## Root Cause
The `/groups` endpoint needs to be added to your API Gateway configuration. This is a new endpoint that was added to query distinct groups from DynamoDB.

## Solution

### Step 1: Update Lambda Function
First, make sure your Lambda function has been updated with the latest code:

```bash
# If using deployment script
python update_lambda.py

# Or manually update through AWS Console:
# 1. Go to Lambda Console
# 2. Select your bulk_email_api_lambda function
# 3. Upload the updated bulk_email_api_lambda.py file
```

### Step 2: Add /groups Endpoint to API Gateway

**Option A: Use the Automated Script (Recommended)**
```bash
python add_groups_endpoint.py
```

**Option B: Manual Configuration via AWS Console**

1. **Open API Gateway Console**
   - Navigate to API Gateway in AWS Console
   - Select your BulkEmailAPI

2. **Create /groups Resource**
   - Select the root resource `/`
   - Click "Actions" → "Create Resource"
   - Resource Name: `groups`
   - Resource Path: `/groups`
   - Click "Create Resource"

3. **Add GET Method**
   - Select the `/groups` resource
   - Click "Actions" → "Create Method"
   - Select "GET" from dropdown
   - Click the checkmark
   
4. **Configure GET Method**
   - Integration type: Lambda Function
   - Use Lambda Proxy integration: ✓ (checked)
   - Lambda Region: us-gov-west-1
   - Lambda Function: bulk_email_api_lambda
   - Click "Save"
   - Click "OK" to give API Gateway permission

5. **Enable CORS**
   - Select the `/groups` resource
   - Click "Actions" → "Enable CORS"
   - Leave default settings
   - Click "Enable CORS and replace existing CORS headers"
   - Click "Yes, replace existing values"

6. **Deploy API**
   - Click "Actions" → "Deploy API"
   - Deployment stage: prod
   - Deployment description: "Added /groups endpoint"
   - Click "Deploy"

### Step 3: Test the Endpoint

**Using curl:**
```bash
curl https://YOUR-API-ID.execute-api.us-gov-west-1.amazonaws.com/prod/groups
```

**Expected Response:**
```json
{
  "groups": ["Group1", "Group2", "Group3"]
}
```

### Step 4: Verify in Browser

1. Open your web UI
2. Open browser Developer Tools (F12)
3. Go to the Console tab
4. Refresh the page
5. Look for these log messages:
   ```
   Loading groups from DynamoDB...
   API URL: https://...amazonaws.com/prod/groups
   Loaded groups from API: [...]
   Number of groups found: X
   ```

6. If you see an error, check:
   - The API endpoint URL is correct
   - The /groups resource exists in API Gateway
   - The Lambda function has been updated
   - CORS is properly configured

## Debugging Steps

### Check 1: Verify Endpoint Exists
```bash
aws apigateway get-resources --rest-api-id YOUR-API-ID --region us-gov-west-1
```

Look for a resource with `"path": "/groups"`

### Check 2: Test Lambda Function Directly
```bash
aws lambda invoke \
  --function-name bulk_email_api_lambda \
  --region us-gov-west-1 \
  --payload '{"httpMethod":"GET","path":"/groups","resource":"/groups"}' \
  response.json

cat response.json
```

Expected output should contain groups.

### Check 3: Check Lambda Logs
```bash
aws logs tail /aws/lambda/bulk_email_api_lambda --follow --region us-gov-west-1
```

### Check 4: Verify Contacts Have Groups
Make sure your contacts in DynamoDB have the 'group' field populated:
```bash
aws dynamodb scan \
  --table-name EmailContacts \
  --projection-expression "email,#grp" \
  --expression-attribute-names '{"#grp":"group"}' \
  --region us-gov-west-1
```

## Common Issues

### Issue 1: 404 Not Found
**Cause:** The `/groups` endpoint doesn't exist in API Gateway  
**Solution:** Follow Step 2 above to add the endpoint

### Issue 2: 403 Forbidden
**Cause:** Lambda doesn't have permission to be invoked by API Gateway  
**Solution:** In API Gateway, delete and recreate the GET method (this will re-add permissions)

### Issue 3: Empty Groups Array
**Cause:** No contacts have the 'group' field populated  
**Solution:** Add or edit contacts to include group information

### Issue 4: CORS Error
**Cause:** CORS not properly configured on /groups endpoint  
**Solution:** Follow Step 2, substep 5 to enable CORS

### Issue 5: Old Code Running
**Cause:** Lambda function hasn't been updated  
**Solution:** 
- Update Lambda function code
- Redeploy API Gateway
- Hard refresh browser (Ctrl+F5)

## Quick Test Command
```bash
# Replace YOUR-API-ID with your actual API Gateway ID
curl -v https://YOUR-API-ID.execute-api.us-gov-west-1.amazonaws.com/prod/groups
```

## Need Help?
If you're still having issues:
1. Check browser console for JavaScript errors
2. Check API Gateway execution logs
3. Check Lambda CloudWatch logs
4. Verify your contacts table has data with 'group' field

