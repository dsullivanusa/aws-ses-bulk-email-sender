# Final Solution: Private API Gateway with Private Network Access

## Your Requirements
✅ Keep API Gateway as PRIVATE  
✅ Access from private network  
✅ Maintain security (no public access)

## The Issue
Your API Gateway has:
- `"Principal": "*"` ✅
- `"Resource": "*"` ✅
- Endpoint Type: **PRIVATE** ✅

**But still getting 403 errors because:**
Private API Gateways require EITHER:
1. VPC Endpoint access, OR
2. IP-based conditions in the resource policy

## Solution: Update Resource Policy for Private Network Access

Since you're accessing from a private network (not from within a VPC), you need to add an IP-based condition to your resource policy.

### **Quick Fix**

Run this script to immediately fix the 403 error:

```bash
python quick_fix_private_access.py
```

This will:
1. Find your API Gateway
2. Update the resource policy to allow private network IP ranges
3. Redeploy the API
4. Test the connection

### **What Gets Changed**

Your resource policy will be updated from:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "*"
    }
  ]
}
```

To:
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
            "127.0.0.0/8"
          ]
        }
      }
    }
  ]
}
```

### **Manual Fix (AWS CLI)**

If you prefer to do it manually:

```bash
# Get your API Gateway ID
API_ID=$(aws apigateway get-rest-apis --region us-gov-west-1 --query 'items[?contains(name,`bulk-email`)].id' --output text)

# Get your AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

# Update the resource policy
aws apigateway update-rest-api \
  --rest-api-id $API_ID \
  --region us-gov-west-1 \
  --patch-ops op=replace,path=/policy,value='{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "execute-api:Invoke",
        "Resource": "arn:aws-us-gov:execute-api:us-gov-west-1:*:'$API_ID'/*",
        "Condition": {
          "IpAddress": {
            "aws:sourceIp": [
              "10.0.0.0/8",
              "172.16.0.0/12",
              "192.168.0.0/16",
              "127.0.0.0/8"
            ]
          }
        }
      }
    ]
  }'

# Redeploy the API
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --description "Allow private network access" \
  --region us-gov-west-1

echo "API URL: https://$API_ID.execute-api.us-gov-west-1.amazonaws.com/prod"
```

### **Custom IP Ranges**

If you need to restrict to specific IP ranges (more secure):

```bash
# Example: Only allow specific networks
aws apigateway update-rest-api \
  --rest-api-id $API_ID \
  --region us-gov-west-1 \
  --patch-ops op=replace,path=/policy,value='{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "execute-api:Invoke",
        "Resource": "arn:aws-us-gov:execute-api:us-gov-west-1:*:'$API_ID'/*",
        "Condition": {
          "IpAddress": {
            "aws:sourceIp": [
              "10.1.0.0/24",
              "192.168.1.0/24"
            ]
          }
        }
      }
    ]
  }'
```

## Security Benefits (API Remains Private)

✅ **Still PRIVATE endpoint** - Not accessible from public internet  
✅ **IP-based restrictions** - Only allowed IP ranges can access  
✅ **No VPN required** - Direct access from private network  
✅ **Lambda execution** - Backend still secure in VPC  
✅ **Network isolation** - Traffic stays on private networks

## Testing After Fix

### Test from Command Line
```bash
# Get API URL
API_ID=$(aws apigateway get-rest-apis --region us-gov-west-1 --query 'items[?contains(name,`bulk-email`)].id' --output text)
API_URL="https://$API_ID.execute-api.us-gov-west-1.amazonaws.com/prod"

# Test web UI
curl -I $API_URL/

# Test config endpoint
curl $API_URL/config

# Test contacts endpoint
curl $API_URL/contacts?limit=1
```

### Test from Browser
1. Open: `https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/`
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Look for successful API calls (no 403 errors)
5. Check that config loads (From Email field populated)

## What This Fixes

✅ Web UI will load successfully  
✅ Email config will load from DynamoDB  
✅ Contacts will load  
✅ Groups will load  
✅ Campaigns can be sent  
✅ All API endpoints accessible from private network

## Troubleshooting

### Still Getting 403?

**Check your source IP:**
```bash
curl ifconfig.me
```

**Verify it's in one of these ranges:**
- 10.0.0.0 - 10.255.255.255 (10.0.0.0/8)
- 172.16.0.0 - 172.31.255.255 (172.16.0.0/12)
- 192.168.0.0 - 192.168.255.255 (192.168.0.0/16)
- 127.0.0.0 - 127.255.255.255 (127.0.0.0/8)

**If your IP is outside these ranges:**
Add your specific IP range to the policy.

### Check Lambda Permissions

```bash
# Verify Lambda can be invoked by API Gateway
aws lambda get-policy --function-name bulk-email-api-function --region us-gov-west-1
```

Should show API Gateway as allowed principal.

### Check Deployment

```bash
# Verify API is deployed to prod stage
aws apigateway get-stages --rest-api-id $API_ID --region us-gov-west-1
```

Should show "prod" stage with recent deployment.

## Network Architecture

```
┌─────────────────────┐
│  Private Network    │
│  (Your location)    │
│  IP: 10.x.x.x       │
└──────────┬──────────┘
           │
           │ HTTPS (allowed by IP condition)
           ▼
┌─────────────────────┐
│  API Gateway        │
│  (PRIVATE)          │
│  Resource Policy:   │
│  - Principal: *     │
│  - Resource: *      │
│  - Condition:       │
│    IpAddress: 10.x  │
└──────────┬──────────┘
           │
           │ Invokes
           ▼
┌─────────────────────┐
│  Lambda Function    │
│  bulk-email-api     │
└──────────┬──────────┘
           │
           │ Reads/Writes
           ▼
┌─────────────────────┐
│  DynamoDB Tables    │
│  - EmailConfig      │
│  - EmailContacts    │
│  - EmailCampaigns   │
└─────────────────────┘
```

## Summary

**The Fix:**
- Add IP-based condition to resource policy
- Keep API Gateway as PRIVATE
- Allow access from private network IP ranges
- Maintain security (no public internet access)

**Run:**
```bash
python quick_fix_private_access.py
```

**Result:**
- 403 errors resolved
- Web UI accessible from private network
- API Gateway remains private and secure
