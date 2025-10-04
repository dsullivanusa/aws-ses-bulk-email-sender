# 🌐 API Gateway Management Guide

## Overview
Complete guide for managing your API Gateway infrastructure, including creation, deletion, and troubleshooting.

---

## 📋 Available Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| **`recreate_api_gateway.py`** | Create new API Gateway with all endpoints | `python recreate_api_gateway.py` |
| **`get_api_gateway_info.py`** | View current API Gateway details | `python get_api_gateway_info.py` |
| **`delete_api_gateway.py`** | Delete existing API Gateway | `python delete_api_gateway.py` |

---

## 🚀 Recreate API Gateway

### When to Use:
- Original API Gateway deleted
- Starting fresh
- Migration to new account/region
- Major API restructuring

### Process:

```bash
python recreate_api_gateway.py
```

**What it does:**
1. ✅ Creates new REST API
2. ✅ Creates all 13 endpoints
3. ✅ Configures Lambda integrations
4. ✅ Enables CORS on all endpoints
5. ✅ Adds Lambda invoke permissions
6. ✅ Deploys to 'prod' stage
7. ✅ Saves configuration to file

**Output:**
```
API ID:       abc123def456
API URL:      https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod
Web UI:       https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod/

Configuration saved to: api_gateway_info.json
```

### Endpoints Created:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Web UI |
| GET | `/config` | Get email config |
| POST | `/config` | Save email config |
| GET | `/contacts` | Get all contacts |
| POST | `/contacts` | Add contact |
| PUT | `/contacts` | Update contact |
| DELETE | `/contacts` | Delete contact |
| POST | `/contacts/batch` | Batch add contacts |
| POST | `/contacts/search` | Search contacts |
| GET | `/groups` | Get groups |
| POST | `/upload-attachment` | Upload attachment |
| POST | `/campaign` | Send campaign |
| GET | `/campaign/{campaign_id}` | Get campaign status |

---

## 🔍 View Current API Gateway

### Get Information:

```bash
# Find API by name
python get_api_gateway_info.py

# Get specific API by ID
python get_api_gateway_info.py abc123def456
```

**Output:**
```
API GATEWAY INFORMATION
================================================================================

API ID:       abc123def456
API Name:     bulk-email-api
Description:  Bulk Email Campaign Management API
Created:      2025-10-04 10:00:00
Region:       us-gov-west-1

--------------------------------------------------------------------------------
STAGES:
--------------------------------------------------------------------------------

Stage: prod
  URL:     https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod
  Deployed: 2025-10-04 10:05:00

--------------------------------------------------------------------------------
ENDPOINTS (13 resources):
--------------------------------------------------------------------------------
GET      https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod/
GET      https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod/config
POST     https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod/config
...

Information saved to: current_api_info.json
```

---

## 🗑️ Delete API Gateway

### When to Use:
- Cleaning up old/unused APIs
- Before recreating API
- Decommissioning service

### Process:

```bash
# Interactive mode (lists all APIs)
python delete_api_gateway.py

# Direct deletion by ID
python delete_api_gateway.py abc123def456
```

**Safety Features:**
- Lists all APIs first
- Shows API name before deletion
- Requires "yes" confirmation
- Cannot be undone warning

**Output:**
```
EXISTING API GATEWAYS
================================================================================
API ID                    Name                                Created
--------------------------------------------------------------------------------
abc123def456              bulk-email-api                      2025-10-04 10:00
xyz789ghi012              old-bulk-email-api                  2025-09-01 08:00
================================================================================

Enter API ID to delete (or 'cancel' to exit):
> abc123def456

API to delete:
  ID:   abc123def456
  Name: bulk-email-api

⚠️  Delete this API Gateway? This cannot be undone! (yes/no): yes

🗑️  Deleting API Gateway...

✅ API Gateway deleted successfully!
```

---

## 🔄 Full Recreation Workflow

### Scenario: Replace Existing API

```bash
# Step 1: Get current API info (for reference)
python get_api_gateway_info.py

# Step 2: Delete old API (optional - only if cleaning up)
python delete_api_gateway.py

# Step 3: Create new API
python recreate_api_gateway.py

# Step 4: Test new API
curl https://NEW_API_ID.execute-api.us-gov-west-1.amazonaws.com/prod/

# Step 5: Update bookmarks with new URL
```

---

## 📊 Configuration Files

### `api_gateway_info.json` (Created by recreate script)
```json
{
  "api_id": "abc123def456",
  "api_name": "bulk-email-api",
  "region": "us-gov-west-1",
  "stage": "prod",
  "api_url": "https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod",
  "lambda_function": "bulk-email-api-function",
  "created_at": "2025-10-04 10:00:00",
  "endpoints": {
    "web_ui": "https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod/",
    "config_get": "https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod/config",
    ...
  }
}
```

### `current_api_info.json` (Created by info script)
```json
{
  "api_id": "abc123def456",
  "api_name": "bulk-email-api",
  "region": "us-gov-west-1",
  "resources": 13,
  "deployments": 1,
  "stages": ["prod"],
  "api_url": "https://abc123def456.execute-api.us-gov-west-1.amazonaws.com/prod"
}
```

---

## 🛡️ Prerequisites

### Required:
- ✅ Lambda function deployed (`bulk-email-api-function`)
- ✅ AWS credentials configured
- ✅ IAM permissions for API Gateway
- ✅ Python 3.7+
- ✅ boto3 installed

### IAM Permissions Needed:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apigateway:*",
        "lambda:AddPermission",
        "lambda:GetFunction",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 🧪 Testing

### Test API Endpoints:

```bash
# Get API URL from config
API_URL=$(cat api_gateway_info.json | jq -r '.api_url')

# Test Web UI (should return HTML)
curl $API_URL/

# Test config endpoint
curl $API_URL/config

# Test contacts endpoint
curl $API_URL/contacts

# Test groups endpoint
curl $API_URL/groups
```

### Test in Browser:

1. Open Web UI: `https://YOUR_API_ID.execute-api.us-gov-west-1.amazonaws.com/prod/`
2. Should see Email Campaign form
3. Try loading contacts
4. Try sending test campaign

---

## 🔧 Troubleshooting

### Issue: "Lambda function not found"

**Cause:** Lambda function doesn't exist or wrong name

**Solution:**
```bash
# Check Lambda exists
aws lambda get-function --function-name bulk-email-api-function --region us-gov-west-1

# If wrong name, update script:
LAMBDA_FUNCTION_NAME = 'your-actual-function-name'
```

### Issue: "Access Denied" errors

**Cause:** Insufficient IAM permissions

**Solution:**
```bash
# Check current permissions
aws sts get-caller-identity

# Add required permissions to your IAM user/role
```

### Issue: API Gateway not accessible

**Cause:** Not deployed to stage

**Solution:**
```bash
# Redeploy to prod stage
aws apigateway create-deployment \
  --rest-api-id YOUR_API_ID \
  --stage-name prod \
  --region us-gov-west-1
```

### Issue: "404 Not Found" on endpoints

**Cause:** Endpoint path doesn't match Lambda routing

**Solution:**
- Verify paths in `bulk_email_api_lambda.py` match API Gateway resources
- Check Lambda handler event parsing

### Issue: CORS errors in browser

**Cause:** CORS not properly configured

**Solution:**
```bash
# Script already adds CORS, but if needed manually:
# Add OPTIONS method to each resource
# Add proper CORS headers in Lambda responses
```

---

## 📈 Advanced Configuration

### Custom Domain:

```bash
# After creating API, add custom domain
aws apigateway create-domain-name \
  --domain-name api.yourdomain.com \
  --regional-certificate-arn arn:aws:acm:... \
  --endpoint-configuration types=REGIONAL

# Map domain to API
aws apigateway create-base-path-mapping \
  --domain-name api.yourdomain.com \
  --rest-api-id YOUR_API_ID \
  --stage prod
```

### Add API Key:

```bash
# Create API key
aws apigateway create-api-key \
  --name BulkEmailAPIKey \
  --enabled

# Create usage plan
aws apigateway create-usage-plan \
  --name BulkEmailUsage \
  --api-stages apiId=YOUR_API_ID,stage=prod

# Associate key with plan
aws apigateway create-usage-plan-key \
  --usage-plan-id PLAN_ID \
  --key-id KEY_ID \
  --key-type API_KEY
```

### Enable CloudWatch Logging:

```bash
# Update stage to enable logging
aws apigateway update-stage \
  --rest-api-id YOUR_API_ID \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/accessLogSettings/destinationArn,value=arn:aws:logs:... \
    op=replace,path=/accessLogSettings/format,value='$context.requestId'
```

---

## 🔄 Migration Checklist

### Before Migration:
- [ ] Get current API info
- [ ] Export current configuration
- [ ] Document custom settings
- [ ] Test backup API access
- [ ] Notify users of planned change

### During Migration:
- [ ] Run `get_api_gateway_info.py` (save current)
- [ ] Run `recreate_api_gateway.py` (create new)
- [ ] Test new API thoroughly
- [ ] Update DNS/bookmarks
- [ ] Verify all endpoints work

### After Migration:
- [ ] Delete old API (if needed)
- [ ] Update documentation
- [ ] Notify users of new URL
- [ ] Monitor for issues
- [ ] Keep backup of old config

---

## 📝 Best Practices

### 1. Always Save Config
```bash
# After creating API
cp api_gateway_info.json api_gateway_info.backup.json

# Commit to git
git add api_gateway_info.json
git commit -m "Updated API Gateway configuration"
```

### 2. Test Before Deleting
```bash
# Create new first
python recreate_api_gateway.py

# Test new API thoroughly

# Only then delete old
python delete_api_gateway.py OLD_API_ID
```

### 3. Document Changes
Keep a log of API changes:
```
2025-10-04: Created new API (abc123def456) - Initial setup
2025-10-10: Added /groups endpoint
2025-10-15: Recreated API due to corruption
```

### 4. Monitor API Usage
```bash
# Check API metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=bulk-email-api \
  --start-time 2025-10-01T00:00:00Z \
  --end-time 2025-10-04T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

---

## 🆘 Emergency Recovery

### If API Deleted Accidentally:

```bash
# 1. Don't panic - Lambda function still exists
# 2. Run recreation script immediately
python recreate_api_gateway.py

# 3. New API created with all endpoints
# 4. Update any saved URLs/bookmarks
# 5. Service restored in < 2 minutes
```

### If Lambda Function Deleted:

```bash
# 1. Redeploy Lambda first
python deploy_complete.py

# 2. Then recreate API
python recreate_api_gateway.py
```

---

## 💰 Cost Considerations

### API Gateway Pricing:
- **REST API Requests**: $3.50 per million requests
- **Data Transfer**: $0.09/GB (out)
- **Typical usage (100 campaigns/month)**: < $1/month

### Free Tier:
- 1 million API calls per month (first 12 months)
- Likely FREE for most deployments

---

## 📚 Additional Resources

- [AWS API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [REST API Reference](https://docs.aws.amazon.com/apigateway/latest/api/API_Operations.html)
- [Best Practices](https://docs.aws.amazon.com/apigateway/latest/developerguide/best-practices.html)

---

## 🎯 Quick Reference

### Common Commands:
```bash
# View current API
python get_api_gateway_info.py

# Create new API
python recreate_api_gateway.py

# Delete old API
python delete_api_gateway.py OLD_API_ID

# Test API
curl https://API_ID.execute-api.us-gov-west-1.amazonaws.com/prod/
```

### Files:
- `recreate_api_gateway.py` - Creation script
- `get_api_gateway_info.py` - Info script
- `delete_api_gateway.py` - Deletion script
- `api_gateway_info.json` - Configuration output
- `current_api_info.json` - Current state output

---

**Your API Gateway can now be recreated in minutes!** 🌐✅

All endpoints, integrations, and permissions configured automatically.

