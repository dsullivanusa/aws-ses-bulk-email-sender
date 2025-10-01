# Custom Domain Setup Guide

## Overview
By default, the Bulk Email API uses the AWS API Gateway URL (e.g., `https://abc123.execute-api.us-gov-west-1.amazonaws.com/prod`). You can configure a custom domain to make the URL more user-friendly.

## Quick Setup - Environment Variable Only

### Step 1: Set Lambda Environment Variable
1. Go to AWS Lambda Console
2. Select your `bulk_email_api_lambda` function
3. Go to **Configuration** → **Environment variables**
4. Click **Edit**
5. Add new environment variable:
   - **Key**: `CUSTOM_API_URL`
   - **Value**: Your desired URL (e.g., `https://yourdomain.com` or `https://api.yourdomain.com`)
6. Click **Save**

### Step 2: Test
- Access your Lambda function URL or API Gateway endpoint
- Open browser developer tools (F12) → Network tab
- Click any button (Load Contacts, Save Config, etc.)
- Verify that API calls are going to your custom URL instead of the API Gateway URL

## Full Setup - With Custom Domain (Recommended)

If you want the custom domain to actually work (not just change the URL), you need to set up API Gateway Custom Domain:

### Step 1: Create Custom Domain in API Gateway
1. Go to **API Gateway Console**
2. Click **Custom domain names** → **Create**
3. Enter your domain name (e.g., `api.yourdomain.com`)
4. Choose **Regional** or **Edge-optimized**
5. Select or create an ACM certificate for your domain
6. Click **Create**

### Step 2: Configure API Mappings
1. After creating the custom domain, go to **API mappings** tab
2. Click **Configure API mappings**
3. Click **Add new mapping**
4. Select your API and stage (e.g., `prod`)
5. Leave path empty or specify one (e.g., `/` or `/api`)
6. Click **Save**

### Step 3: Update DNS
1. Note the API Gateway's **Target domain name** (ends with `.cloudfront.net` or `.execute-api.amazonaws.com`)
2. Go to your DNS provider (Route 53, Cloudflare, etc.)
3. Create a CNAME record:
   - **Name**: `api` (or your subdomain)
   - **Value**: The target domain name from API Gateway
   - **TTL**: 300 (or your preference)

### Step 4: Set Lambda Environment Variable
1. Follow **Step 1** from "Quick Setup" above
2. Set `CUSTOM_API_URL` to your custom domain with the correct path:
   - Example: `https://api.yourdomain.com/prod`
   - Or if you mapped to root path: `https://api.yourdomain.com`

### Step 5: Verify
1. Wait for DNS propagation (can take 5-60 minutes)
2. Test your custom domain: `https://api.yourdomain.com/prod`
3. You should see the web UI
4. Check that all buttons work correctly

## Troubleshooting

### API calls fail after setting custom URL
- Make sure your custom domain is properly configured in API Gateway
- Verify DNS is pointing to the correct target
- Check that the URL in `CUSTOM_API_URL` matches your API Gateway mapping path

### Still seeing AWS API Gateway URL
- Clear browser cache and hard refresh (Ctrl+F5 or Cmd+Shift+R)
- Verify the environment variable is set correctly in Lambda
- Redeploy your Lambda function after setting the environment variable

### CORS errors
- Make sure API Gateway has CORS enabled on all resources
- The Lambda function already includes proper CORS headers

## Example Configurations

### Example 1: Simple Custom Domain
```
CUSTOM_API_URL = https://email.mycompany.com
```

### Example 2: With API Path
```
CUSTOM_API_URL = https://api.mycompany.com/email
```

### Example 3: With Stage
```
CUSTOM_API_URL = https://api.mycompany.com/prod
```

## Removing Custom Domain

To revert to the default API Gateway URL:
1. Go to Lambda Console → Your function → Configuration → Environment variables
2. Delete the `CUSTOM_API_URL` variable
3. Click **Save**

The system will automatically fall back to using the API Gateway URL.

## Security Note

When using a custom domain:
- Ensure SSL/TLS certificate is valid
- Use HTTPS only (never HTTP)
- Keep ACM certificates up to date
- Consider using AWS WAF for additional security

