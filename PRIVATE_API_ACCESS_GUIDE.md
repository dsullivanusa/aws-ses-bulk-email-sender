# Private API Gateway Access Guide

## Overview

Your API Gateway is configured as **PRIVATE**, which means it can only be accessed from within your VPC or through a VPC endpoint. This provides enhanced security but requires proper network configuration.

## Current Issue

The 403 error occurs because:
1. Your API Gateway is private (requires VPC access)
2. The web UI is trying to access it from outside the VPC
3. No VPC endpoint is configured for API Gateway access

## Solution Options

### Option 1: Set Up VPC Endpoint Access (Recommended)

Run the automated setup script:

```bash
python setup_private_api_access.py
```

This will:
- Create a VPC endpoint for the execute-api service
- Update API Gateway resource policy to allow VPC endpoint access
- Redeploy the API Gateway
- Provide access URLs and testing instructions

### Option 2: Manual Setup

#### Step 1: Create VPC Endpoint

```bash
# Get your VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ses-email-vpc" --query 'Vpcs[0].VpcId' --output text --region us-gov-west-1)

# Get subnet ID
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text --region us-gov-west-1)

# Create VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-gov-west-1.execute-api \
  --vpc-endpoint-type Interface \
  --subnet-ids $SUBNET_ID \
  --private-dns-enabled \
  --region us-gov-west-1
```

#### Step 2: Update API Gateway Policy

```bash
# Get API Gateway ID
API_ID=$(aws apigateway get-rest-apis --region us-gov-west-1 --query 'items[?name==`bulk-email-api`].id' --output text)

# Get VPC endpoint ID
VPCE_ID=$(aws ec2 describe-vpc-endpoints --filters "Name=service-name,Values=com.amazonaws.us-gov-west-1.execute-api" --query 'VpcEndpoints[0].VpcEndpointId' --output text --region us-gov-west-1)

# Update API Gateway policy
aws apigateway update-rest-api \
  --rest-api-id $API_ID \
  --patch-ops op=replace,path=/policy,value='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"execute-api:Invoke","Resource":"*","Condition":{"StringEquals":{"aws:sourceVpce":"'$VPCE_ID'"}}}]}' \
  --region us-gov-west-1
```

#### Step 3: Redeploy API

```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region us-gov-west-1
```

## Access Methods

### Method 1: From Within VPC

If you're accessing from an EC2 instance or resource within the VPC:

**URL:** `https://{api-id}.execute-api.us-gov-west-1.amazonaws.com/prod`

**Web UI:** `https://{api-id}.execute-api.us-gov-west-1.amazonaws.com/prod/`

### Method 2: Via VPC Endpoint

If you have VPC endpoint access configured:

**URL:** `https://{api-id}-{vpce-id}.execute-api.us-gov-west-1.vpce.amazonaws.com/prod`

**Web UI:** `https://{api-id}-{vpce-id}.execute-api.us-gov-west-1.vpce.amazonaws.com/prod/`

### Method 3: VPN Connection

If you have a VPN connection to your VPC:

1. Connect to your VPC via VPN
2. Use the standard API Gateway URL
3. Access the web UI from your browser

## Testing Access

### Test API Endpoints

```bash
# Test web UI (should return HTML)
curl -I https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/

# Test contacts endpoint (should return JSON)
curl https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts?limit=1

# Test config endpoint
curl https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/config
```

### Test from Browser

1. **From within VPC**: Open the web UI URL in your browser
2. **Via VPN**: Connect to VPN, then open the web UI URL
3. **Via VPC endpoint**: Use the VPC endpoint URL if configured

## Troubleshooting

### Issue: Still Getting 403 Errors

**Check:**
1. VPC endpoint is created and active
2. API Gateway policy allows VPC endpoint access
3. You're using the correct URL for your access method
4. Network connectivity to VPC endpoint

**Debug Commands:**
```bash
# Check VPC endpoint status
aws ec2 describe-vpc-endpoints --filters "Name=service-name,Values=com.amazonaws.us-gov-west-1.execute-api" --region us-gov-west-1

# Check API Gateway policy
aws apigateway get-rest-api --rest-api-id your-api-id --region us-gov-west-1 --query 'policy'

# Test connectivity
curl -v https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/
```

### Issue: DNS Resolution Problems

**Enable Private DNS:**
```bash
# Enable private DNS for VPC endpoint
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id your-vpce-id \
  --private-dns-enabled \
  --region us-gov-west-1
```

### Issue: Security Group Restrictions

**Check security groups:**
```bash
# List security groups for VPC endpoint
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids your-vpce-id \
  --query 'VpcEndpoints[0].Groups' \
  --region us-gov-west-1
```

## Alternative: Convert to Public API

If you need public access and can't use VPC endpoints, you can convert to a public API:

```bash
# Convert to regional (public) API
aws apigateway update-rest-api \
  --rest-api-id your-api-id \
  --patch-ops op=replace,path=/endpointConfiguration/types/0,value=REGIONAL \
  --region us-gov-west-1

# Remove resource policy
aws apigateway update-rest-api \
  --rest-api-id your-api-id \
  --patch-ops op=remove,path=/policy \
  --region us-gov-west-1

# Redeploy
aws apigateway create-deployment \
  --rest-api-id your-api-id \
  --stage-name prod \
  --region us-gov-west-1
```

**Note:** This makes your API publicly accessible, which may not meet your security requirements.

## Security Considerations

### Private API Benefits
- ✅ No internet exposure
- ✅ VPC-only access
- ✅ Enhanced security
- ✅ Network isolation

### Access Requirements
- 🔒 Must be within VPC or have VPC endpoint access
- 🔒 Requires proper network configuration
- 🔒 May need VPN connection for external access

## Next Steps

1. **Run the setup script**: `python setup_private_api_access.py`
2. **Test access** using the provided URLs
3. **Configure your network** for VPC endpoint access
4. **Set up VPN** if external access is needed
5. **Update web UI configuration** to use the correct API URL

## Support

If you continue to have issues:
1. Check CloudWatch logs for Lambda function errors
2. Verify VPC endpoint connectivity
3. Test API endpoints individually
4. Check IAM permissions for Lambda function
5. Verify DynamoDB table access permissions


