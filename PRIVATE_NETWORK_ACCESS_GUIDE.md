# Private Network Access Fix Guide

## Problem
Your web UI is accessed from a private network, but the API Gateway is configured as PRIVATE with restrictive policies that don't allow access from your private network IP ranges.

## Root Cause
Private API Gateways require explicit IP address ranges in their resource policy. The current policy likely doesn't include your private network ranges.

## Quick Fix (Recommended)

Run the automated fix script:

```bash
python quick_fix_private_access.py
```

This will:
- Find your API Gateway
- Update the resource policy to allow common private network ranges
- Redeploy the API Gateway
- Provide access URLs

## Manual Fix

### Step 1: Find Your API Gateway

```bash
# List all API Gateways
aws apigateway get-rest-apis --region us-gov-west-1 --query 'items[].{Name:name,Id:id}'

# Get specific API Gateway ID
API_ID=$(aws apigateway get-rest-apis --region us-gov-west-1 --query 'items[?name==`bulk-email-api`].id' --output text)
```

### Step 2: Update Resource Policy

```bash
# Update API Gateway policy to allow private network access
aws apigateway update-rest-api \
  --rest-api-id $API_ID \
  --region us-gov-west-1 \
  --patch-ops op=replace,path=/policy,value='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"execute-api:Invoke","Resource":"arn:aws-us-gov:execute-api:us-gov-west-1:*:'$API_ID'/*","Condition":{"IpAddress":{"aws:sourceIp":["10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","127.0.0.0/8"]}}}]}'
```

### Step 3: Redeploy API Gateway

```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region us-gov-west-1
```

## Allowed IP Ranges

The fix includes these common private network ranges:

- `10.0.0.0/8` - Class A private networks
- `172.16.0.0/12` - Class B private networks  
- `192.168.0.0/16` - Class C private networks
- `127.0.0.0/8` - Loopback addresses

## Custom IP Ranges

If you need to add specific IP ranges, modify the policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws-us-gov:execute-api:us-gov-west-1:*:your-api-id/*",
      "Condition": {
        "IpAddress": {
          "aws:sourceIp": [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "YOUR.SPECIFIC.IP.RANGE/24"
          ]
        }
      }
    }
  ]
}
```

## Testing

After applying the fix:

```bash
# Test API access
curl -I https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/

# Test specific endpoint
curl https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts?limit=1

# Test in browser
# Open: https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/
```

## Troubleshooting

### Still Getting 403 Errors

1. **Check your IP address**:
   ```bash
   # Find your public IP
   curl ifconfig.me
   
   # Check if it's in allowed ranges
   ```

2. **Verify policy was applied**:
   ```bash
   aws apigateway get-rest-api --rest-api-id your-api-id --region us-gov-west-1 --query 'policy'
   ```

3. **Check API Gateway logs**:
   ```bash
   aws logs filter-log-events \
     --log-group-name API-Gateway-Execution-Logs_your-api-id/prod \
     --region us-gov-west-1 \
     --filter-pattern "403"
   ```

### Network Issues

1. **Firewall blocking HTTPS**: Ensure port 443 is open
2. **DNS resolution**: Try accessing by IP if DNS fails
3. **Proxy/VPN**: May need to configure proxy settings

### Lambda Function Issues

If API responds but Lambda fails:

```bash
# Check Lambda logs
aws logs tail /aws/lambda/bulk-email-api-function --follow --region us-gov-west-1

# Check Lambda permissions
aws lambda get-policy --function-name bulk-email-api-function --region us-gov-west-1
```

## Security Considerations

### Current Security Level
- ✅ Private API Gateway (not publicly accessible)
- ✅ IP-based access control
- ✅ Private network only access
- ⚠️ Broad private IP ranges allowed

### Enhanced Security (Optional)

For tighter security, restrict to specific IP ranges:

```bash
# Replace with your specific IP ranges
SPECIFIC_IPS='["10.1.0.0/24","192.168.1.0/24","YOUR.OFFICE.IP/32"]'

aws apigateway update-rest-api \
  --rest-api-id $API_ID \
  --region us-gov-west-1 \
  --patch-ops op=replace,path=/policy,value='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"execute-api:Invoke","Resource":"arn:aws-us-gov:execute-api:us-gov-west-1:*:'$API_ID'/*","Condition":{"IpAddress":{"aws:sourceIp":'$SPECIFIC_IPS'}}}]}'
```

## Expected Results

- **Before Fix**: 403 Forbidden when accessing from private network
- **After Fix**: 200 OK with web UI or JSON data
- **Web UI**: Should load and display the email campaign interface
- **API Endpoints**: Should return data instead of 403 errors

## Next Steps

1. **Apply the fix** using the quick fix script
2. **Test the web UI** from your private network
3. **Verify data loading** (contacts, groups, etc.)
4. **Check browser console** for any remaining JavaScript errors
5. **Monitor Lambda logs** for any backend issues

## Support

If issues persist after applying the fix:

1. **Share your network IP range** for more specific policy configuration
2. **Check browser developer tools** (F12) for detailed error messages
3. **Verify Lambda function logs** for backend errors
4. **Test API endpoints individually** to isolate the issue


