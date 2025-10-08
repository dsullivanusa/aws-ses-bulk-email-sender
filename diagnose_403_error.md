# 403 Error Diagnosis and Fix

## Problem Identified

The web UI is getting a 403 error when reading from the database because:

**The API Gateway is configured as PRIVATE, which requires VPC endpoint access, but the web UI is being accessed from the public internet.**

## Evidence

1. **API Gateway Configuration**: The deployment scripts show that the API Gateway is created with:
   ```python
   endpointConfiguration={'types': ['PRIVATE']}
   ```

2. **Resource Policy**: Private APIs have restrictive policies that only allow access from specific VPC endpoints or IP ranges.

3. **Error Pattern**: 403 Forbidden is the typical response when trying to access a private API Gateway from outside the allowed network.

## Solution

### Option 1: Convert to Public API Gateway (Recommended)

Run these AWS CLI commands to fix the issue:

```bash
# 1. Find your API Gateway ID
aws apigateway get-rest-apis --region us-gov-west-1 --query 'items[?name==`bulk-email-api`].id' --output text

# 2. Update endpoint configuration to REGIONAL (public)
API_ID="your-api-id-here"
aws apigateway update-rest-api --rest-api-id $API_ID --region us-gov-west-1 --patch-ops op=replace,path=/endpointConfiguration/types/0,value=REGIONAL

# 3. Remove restrictive resource policy
aws apigateway update-rest-api --rest-api-id $API_ID --region us-gov-west-1 --patch-ops op=remove,path=/policy

# 4. Redeploy the API
aws apigateway create-deployment --rest-api-id $API_ID --stage-name prod --region us-gov-west-1
```

### Option 2: Use VPC Endpoint (If you need private access)

If you want to keep the API private, you need to:

1. **Create VPC Endpoint** for API Gateway:
   ```bash
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-xxxxxxxxx \
     --service-name com.amazonaws.us-gov-west-1.execute-api \
     --route-table-ids rtb-xxxxxxxxx \
     --region us-gov-west-1
   ```

2. **Update Resource Policy** to allow VPC endpoint access:
   ```bash
   # Get VPC endpoint ID
   VPC_ENDPOINT_ID=$(aws ec2 describe-vpc-endpoints --region us-gov-west-1 --query 'VpcEndpoints[0].VpcEndpointId' --output text)
   
   # Update policy
   aws apigateway update-rest-api \
     --rest-api-id $API_ID \
     --region us-gov-west-1 \
     --patch-ops op=replace,path=/policy,value='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"execute-api:Invoke","Resource":"*","Condition":{"StringEquals":{"aws:sourceVpce":"'$VPC_ENDPOINT_ID'"}}}]}'
   ```

## Quick Test

After applying the fix, test the API:

```bash
# Test the web UI
curl -I https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/

# Test contacts endpoint
curl https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts?limit=1
```

## Expected Results

- **Before Fix**: 403 Forbidden error
- **After Fix**: 200 OK with HTML content (web UI) or JSON data (API endpoints)

## Alternative: Use Existing Script

If you have Python with boto3 installed, you can use the automated fix script:

```bash
python fix_403_error.py
```

This script will:
1. Detect the current API Gateway configuration
2. Convert from PRIVATE to REGIONAL
3. Remove restrictive policies
4. Redeploy the API
5. Test the access

## Verification

After the fix:

1. **Open the web UI** in your browser
2. **Check browser console** (F12) for any remaining errors
3. **Test data loading** - try clicking tabs and loading contacts
4. **Check Lambda logs** if issues persist:
   ```bash
   aws logs tail /aws/lambda/bulk-email-api-function --follow --region us-gov-west-1
   ```

## Common Issues After Fix

1. **CORS Errors**: May need to redeploy Lambda function
2. **Lambda Timeout**: Check Lambda function configuration
3. **DynamoDB Permissions**: Verify Lambda role has DynamoDB access
4. **Browser Cache**: Clear browser cache (Ctrl+F5)

## Next Steps

1. Apply the fix using Option 1 (convert to public)
2. Test the web UI functionality
3. If issues persist, check Lambda logs for specific errors
4. Verify all API endpoints are working correctly


