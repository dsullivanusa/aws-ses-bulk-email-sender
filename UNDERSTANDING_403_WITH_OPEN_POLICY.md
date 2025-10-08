# Understanding 403 Errors with Open Resource Policy

## The Situation

You have an API Gateway with:
- `"Resource": "*"` (allows all resources)
- `"Principal": "*"` (allows all principals)

**But you're still getting 403 Forbidden errors!**

## Why This Happens

Having `"Principal": "*"` and `"Resource": "*"` in the resource policy **does not automatically make the API publicly accessible**. Here's why:

### **1. PRIVATE API Gateway Endpoint Type** ⚠️ MOST LIKELY CAUSE

**The Problem:**
- Your API Gateway is configured as `PRIVATE` (not `REGIONAL` or `EDGE`)
- PRIVATE APIs **require VPC Endpoint access** regardless of resource policy
- Even with an open resource policy, you MUST access through a VPC endpoint

**How to Check:**
```bash
aws apigateway get-rest-api --rest-api-id your-api-id --region us-gov-west-1 --query 'endpointConfiguration.types'
```

**If it returns `["PRIVATE"]`, this is your issue!**

**The Fix:**

Option A: Access via VPC Endpoint (keeps API private)
```bash
python setup_private_api_access.py
```

Option B: Convert to REGIONAL (makes API public)
```bash
aws apigateway update-rest-api \
  --rest-api-id your-api-id \
  --region us-gov-west-1 \
  --patch-ops op=replace,path=/endpointConfiguration/types/0,value=REGIONAL

aws apigateway create-deployment \
  --rest-api-id your-api-id \
  --stage-name prod \
  --region us-gov-west-1
```

### **2. IP Address Conditions in Resource Policy**

**The Problem:**
Your resource policy might look like this:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "*",
      "Condition": {
        "IpAddress": {
          "aws:sourceIp": ["10.0.0.0/8"]
        }
      }
    }
  ]
}
```

Even though `Principal: *` and `Resource: *`, the **Condition** restricts access to specific IP ranges.

**The Fix:**
```bash
python fix_private_network_access.py
```

Or add your IP range to the condition.

### **3. VPC Endpoint Condition in Resource Policy**

**The Problem:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:sourceVpce": "vpce-xxxxxxxx"
        }
      }
    }
  ]
}
```

Access is only allowed from a specific VPC endpoint.

**The Fix:**
- Access from within the VPC, or
- Remove the condition, or
- Add your VPC endpoint ID

### **4. Method-Level Authorization**

**The Problem:**
- Individual API methods may have `authorizationType` set to `AWS_IAM`, `COGNITO`, or `CUSTOM`
- Resource policy is checked first, but then method authorization is checked
- 403 occurs if you don't provide valid credentials

**How to Check:**
```bash
aws apigateway get-method \
  --rest-api-id your-api-id \
  --resource-id your-resource-id \
  --http-method GET \
  --region us-gov-west-1 \
  --query 'authorizationType'
```

**The Fix:**
Change methods to `authorizationType: NONE` or provide valid credentials.

### **5. Missing Lambda Permissions**

**The Problem:**
- Lambda function doesn't have permission to be invoked by API Gateway
- Returns 403 even if API Gateway policy is open

**How to Check:**
```bash
aws lambda get-policy \
  --function-name bulk-email-api-function \
  --region us-gov-west-1
```

**The Fix:**
```bash
aws lambda add-permission \
  --function-name bulk-email-api-function \
  --statement-id apigateway-invoke-$(date +%s) \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws-us-gov:execute-api:us-gov-west-1:*:your-api-id/*" \
  --region us-gov-west-1
```

### **6. API Not Deployed to Stage**

**The Problem:**
- API changes aren't deployed to the stage (e.g., "prod")
- Old deployment doesn't reflect new permissions

**The Fix:**
```bash
aws apigateway create-deployment \
  --rest-api-id your-api-id \
  --stage-name prod \
  --region us-gov-west-1
```

## Diagnosis Tool

Run the comprehensive diagnostic script:

```bash
python diagnose_403_with_open_policy.py
```

This will check:
- ✅ API endpoint type (PRIVATE vs REGIONAL)
- ✅ Resource policy details and conditions
- ✅ VPC endpoint configuration
- ✅ Method-level authorization
- ✅ Lambda permissions
- ✅ Deployment status

## Understanding the Hierarchy

API Gateway access control has multiple layers:

```
1. Endpoint Type (PRIVATE requires VPC endpoint)
   ↓
2. Resource Policy (Principal, Resource, Conditions)
   ↓
3. Method Authorization (IAM, Cognito, Custom, None)
   ↓
4. Lambda Permissions (Can API Gateway invoke Lambda?)
   ↓
5. Lambda Execution (IAM role for Lambda)
```

**403 errors can occur at ANY of these levels!**

## Quick Checklist

- [ ] Is API endpoint type PRIVATE? (Requires VPC endpoint)
- [ ] Does resource policy have IP address conditions?
- [ ] Does resource policy have VPC endpoint conditions?
- [ ] Are you accessing from the right network/VPC?
- [ ] Do methods have authorization requirements?
- [ ] Does Lambda have API Gateway invoke permissions?
- [ ] Is API deployed to stage?
- [ ] Did you hard refresh browser (Ctrl+F5)?

## Common Scenarios

### Scenario 1: Private Network Access
**Setup:**
- API: PRIVATE
- Policy: `Principal: *`, `Resource: *`, `Condition: {IpAddress: ["10.0.0.0/8"]}`
- Access from: 192.168.1.100

**Result:** 403 (IP not in allowed range)

**Fix:** Add your IP range or use VPC endpoint

### Scenario 2: VPC Endpoint Required
**Setup:**
- API: PRIVATE
- Policy: `Principal: *`, `Resource: *` (no conditions)
- Access from: Public internet

**Result:** 403 (PRIVATE API requires VPC endpoint)

**Fix:** Create VPC endpoint or convert to REGIONAL

### Scenario 3: Public API Works
**Setup:**
- API: REGIONAL
- Policy: `Principal: *`, `Resource: *` (no conditions)
- Access from: Anywhere

**Result:** 200 OK ✅

## Your Specific Case

Since you confirmed:
- Resource policy has `"Resource": "*"`
- Resource policy has `"Principal": "*"`

The 403 error is **most likely** caused by:

1. **API is PRIVATE** (requires VPC endpoint access)
2. **Resource policy has IP-based Condition** (restricts by IP range)
3. **Resource policy has VPC endpoint Condition** (requires specific VPC endpoint)

Run the diagnostic script to identify the exact cause:
```bash
python diagnose_403_with_open_policy.py
```
