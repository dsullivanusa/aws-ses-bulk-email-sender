# Fix for Campaign History 403 Error

## Problem
The Campaign History tab shows a 403 error because the `/campaigns` endpoint (and several others) exist in your Lambda function but are **NOT configured in your API Gateway**.

## Root Cause
Your `api_gateway_config.json` only has these endpoints:
- `/contacts` (GET, POST, OPTIONS)
- `/campaign` (POST, OPTIONS)

But your Lambda function has many more endpoints that are missing from API Gateway:
- ❌ `/campaigns` (GET) - **This is causing the 403 error**
- ❌ `/config` (GET, POST)
- ❌ `/contacts/distinct` (GET)
- ❌ `/contacts/filter` (POST)
- ❌ `/contacts/batch` (POST)
- ❌ `/contacts/search` (POST)
- ❌ `/groups` (GET)
- ❌ `/upload-attachment` (POST)
- ❌ `/preview` (POST, GET)
- ❌ `/campaign/{campaign_id}` (GET)

## Solution
Run the `add_missing_api_endpoints.py` script to add all missing endpoints to your existing API Gateway.

## Prerequisites
```bash
pip install boto3
```

Make sure you have AWS credentials configured for the `us-gov-west-1` region.

## How to Run

### Step 1: Run the Script
```bash
python add_missing_api_endpoints.py
```

### Step 2: What the Script Does
1. ✅ Finds your existing API Gateway (bulk-email-api)
2. ✅ Gets your Lambda function ARN
3. ✅ Checks which resources already exist
4. ✅ Creates missing resources:
   - `/campaigns` ← **This fixes the 403 error**
   - `/config`
   - `/contacts/distinct`
   - `/contacts/filter`
   - `/contacts/batch`
   - `/contacts/search`
   - `/groups`
   - `/upload-attachment`
   - `/preview`
5. ✅ Adds HTTP methods (GET, POST, PUT, DELETE) to each resource
6. ✅ Adds CORS (OPTIONS) support to all endpoints
7. ✅ Grants API Gateway permission to invoke Lambda
8. ✅ Deploys changes to the `prod` stage

### Step 3: Verify
After running the script, you'll see output like:
```
✅ API Gateway updated successfully!
🎉 Your campaign history tab should now work!
   Try accessing: https://[api-id].execute-api.us-gov-west-1.amazonaws.com/prod/campaigns
```

### Step 4: Test Campaign History
1. Open your bulk email UI
2. Go to the **History** tab
3. The campaign history should now load successfully! 🎉

## Expected Output
```
================================================================================
ADDING MISSING ENDPOINTS TO API GATEWAY
================================================================================

✅ Found API Gateway: [api-id]
✅ Found Lambda: arn:aws-us-gov:lambda:us-gov-west-1:[account]:function:bulk-email-api-function
✅ Root resource ID: [resource-id]

📋 Existing resources: ['/', '/contacts', '/campaign']

================================================================================
CREATING MISSING RESOURCES AND METHODS
================================================================================

📍 Processing /config...
  ✅ Created resource: /config
    ✅ Added GET method
    ✅ Added POST method
    ✅ Added CORS OPTIONS method

📍 Processing /campaigns...
  ✅ Created resource: /campaigns
    ✅ Added GET method
    ✅ Added CORS OPTIONS method

... (and so on)

================================================================================
DEPLOYING CHANGES
================================================================================
✅ Successfully deployed to 'prod' stage
   Deployment ID: [deployment-id]

🌐 API URL: https://[api-id].execute-api.us-gov-west-1.amazonaws.com/prod

================================================================================
SUMMARY
================================================================================
✅ Added 9 new resources
✅ Added 15 new methods

================================================================================
✅ API Gateway updated successfully!
================================================================================

🎉 Your campaign history tab should now work!
```

## Alternative: Manual Fix (If Script Fails)

If the script doesn't work, you can manually add the `/campaigns` endpoint:

1. Go to AWS Console → API Gateway
2. Find "bulk-email-api"
3. Click "Resources"
4. Click "Actions" → "Create Resource"
5. Set Resource Path: `campaigns`
6. Click "Create Resource"
7. Select the new `/campaigns` resource
8. Click "Actions" → "Create Method"
9. Select "GET" from dropdown
10. Configure:
    - Integration type: Lambda Function
    - Lambda Region: us-gov-west-1
    - Lambda Function: bulk-email-api-function
    - Use Lambda Proxy integration: ✅ Checked
11. Click "Save"
12. Click "Actions" → "Enable CORS"
13. Click "Actions" → "Deploy API"
14. Select Stage: prod
15. Click "Deploy"

## Why This Happened

The API Gateway configuration was incomplete. When you access the Campaign History tab, JavaScript tries to fetch from `/campaigns`, but since that route doesn't exist in API Gateway, it returns a 403 Forbidden error (API Gateway's way of saying "this route doesn't exist").

The Lambda function HAS the code to handle `/campaigns` requests, but API Gateway never forwards those requests to Lambda because the route isn't configured.

## Files Modified
- ✅ Created: `add_missing_api_endpoints.py` - Script to add missing endpoints
- ✅ Created: `FIX_CAMPAIGN_HISTORY_403.md` - This documentation

## No New API Gateway Needed! ✅
You do **NOT** need to create a new API Gateway. The script updates your existing one.

