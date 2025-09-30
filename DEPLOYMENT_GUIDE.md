# 🚀 Bulk Email API - Complete Deployment Guide

This guide will walk you through deploying the complete bulk email system with AWS Secrets Manager integration.

## 📋 Prerequisites

1. AWS CLI configured with AWS GovCloud credentials
2. Python 3.9+ installed
3. Boto3 installed (`pip install boto3`)
4. Appropriate AWS permissions (Lambda, API Gateway, DynamoDB, Secrets Manager, IAM)

## 🔢 Deployment Steps

### **Step 1: Create DynamoDB Tables**

Create all required DynamoDB tables for storing contacts, campaigns, and configuration:

```bash
# Create EmailContacts table
python dynamodb_table_setup.py

# Create EmailCampaigns table
python dynamodb_campaigns_table.py

# Create EmailConfig table
python create_email_config_table.py
```

**Expected Output:**
```
✓ EmailContacts table created successfully!
✓ EmailCampaigns table created successfully!
✓ EmailConfig table created successfully!
```

---

### **Step 2: Set Up AWS Secrets Manager**

Store your AWS SES credentials securely in Secrets Manager:

```bash
# Create the secret with your AWS SES credentials
python setup_email_credentials_secret.py create
```

**You'll be prompted for:**
- Secret name (default: `email-api-credentials`)
- AWS Access Key ID
- AWS Secret Access Key

**Verify the secret was created:**
```bash
python setup_email_credentials_secret.py list
```

---

### **Step 3: Deploy Lambda Function and API Gateway**

Deploy the complete application (Lambda + API Gateway):

```bash
python deploy_bulk_email_api.py
```

**This script will:**
1. ✅ Create IAM role with necessary permissions
2. ✅ Package and deploy Lambda function
3. ✅ Create API Gateway REST API
4. ✅ Configure routes and integrations
5. ✅ Deploy to `prod` stage
6. ✅ Set up Lambda permissions

**Expected Output:**
```
Created IAM role: bulk-email-api-lambda-role
Created Lambda function: bulk-email-api-function
Created API Gateway: xxxxx
Private API Gateway Deployment Complete!
API Gateway ID: xxxxx
Private API URL: https://xxxxx.execute-api.us-gov-west-1.amazonaws.com/prod
```

---

### **Step 4: Update Lambda IAM Role with Secrets Manager Access**

Add permissions for the Lambda to access Secrets Manager:

```bash
# Get your Lambda role name
ROLE_NAME="bulk-email-api-lambda-role"

# Attach the Secrets Manager policy
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name SecretsManagerAccess \
  --policy-document file://secrets_manager_policy.json \
  --region us-gov-west-1
```

**Or manually:**
1. Go to AWS Console → IAM → Roles
2. Find `bulk-email-api-lambda-role`
3. Click "Add permissions" → "Attach policies"
4. Create inline policy using `secrets_manager_policy.json`

---

### **Step 5: Test the Deployment**

Run the test suite to verify everything is working:

```bash
python test_email_config.py
```

**Expected Output:**
```
=== Email Configuration Test Suite ===
✓ DynamoDB Connection: PASS
✓ Secrets Manager Integration: PASS
✓ Configuration Functions: PASS
🎉 All tests passed!
```

---

### **Step 6: Access the Web UI**

Open your browser and navigate to:
```
https://YOUR_API_ID.execute-api.us-gov-west-1.amazonaws.com/prod
```

**Note:** If using a private API Gateway, you'll need to access it from:
- Within your VPC
- Through a VPN connection
- Via a bastion host or load balancer

---

## 🔧 Configuration

### Configure Email Service

1. Open the web UI in your browser
2. Go to **⚙️ Email Config** tab
3. Select email service:
   - **AWS SES**: Enter region and secret name
   - **SMTP**: Enter SMTP server and port
4. Configure other settings
5. Click **💾 Save Configuration**

### Add Contacts

**Option 1: Upload CSV**
1. Go to **👥 Contacts** tab
2. Click **📁 Upload CSV**
3. Select your CSV file (format: email,first_name,last_name,company)

**Option 2: Add Manually**
1. Click **➕ Add Contact**
2. Fill in contact details
3. Click **✅ Add**

### Send Campaign

1. Go to **📧 Send Campaign** tab
2. Enter campaign name, subject, and body
3. Use placeholders: `{{first_name}}`, `{{last_name}}`, `{{email}}`, `{{company}}`
4. Click **🚀 Send Campaign**

---

## 📦 Required Files Summary

| File | Purpose | When to Run |
|------|---------|-------------|
| `dynamodb_table_setup.py` | Create EmailContacts table | Step 1 |
| `dynamodb_campaigns_table.py` | Create EmailCampaigns table | Step 1 |
| `create_email_config_table.py` | Create EmailConfig table | Step 1 |
| `setup_email_credentials_secret.py` | Create AWS Secrets Manager secret | Step 2 |
| `deploy_bulk_email_api.py` | Deploy Lambda and API Gateway | Step 3 |
| `secrets_manager_policy.json` | IAM policy for Secrets Manager | Step 4 |
| `test_email_config.py` | Test deployment | Step 5 |

---

## 🔐 Security Considerations

### AWS Secrets Manager
- ✅ Credentials stored securely in Secrets Manager
- ✅ Never exposed in DynamoDB or web UI
- ✅ Retrieved at runtime only when needed
- ✅ All access logged in CloudTrail

### API Gateway
- 🔒 Private API Gateway (default configuration)
- 🔒 IP-based access control
- 🔒 VPC-only access
- ⚠️ Update IP ranges in resource policy as needed

### IAM Permissions
- ✅ Lambda has minimal required permissions
- ✅ Separate roles for different services
- ✅ Policy follows principle of least privilege

---

## 🐛 Troubleshooting

### Issue: Lambda can't access Secrets Manager

**Solution:**
```bash
# Verify IAM role has Secrets Manager permissions
aws iam get-role-policy \
  --role-name bulk-email-api-lambda-role \
  --policy-name SecretsManagerAccess \
  --region us-gov-west-1

# If missing, attach the policy (see Step 4)
```

### Issue: Can't access API Gateway

**Solution:**
1. Verify you're accessing from allowed IP range
2. Check API Gateway resource policy
3. For private API, ensure VPC endpoint is configured
4. Check CloudWatch Logs for detailed errors

### Issue: DynamoDB table not found

**Solution:**
```bash
# List all tables
aws dynamodb list-tables --region us-gov-west-1

# If missing, recreate tables (Step 1)
python dynamodb_table_setup.py
python dynamodb_campaigns_table.py
python create_email_config_table.py
```

### Issue: Email sending fails

**Solution:**
1. Verify SES credentials in Secrets Manager
2. Check SES sending limits and verification status
3. Review Lambda CloudWatch logs
4. Test secret retrieval:
   ```bash
   python setup_email_credentials_secret.py test email-api-credentials
   ```

---

## 📊 Monitoring

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/bulk-email-api-function --follow --region us-gov-west-1

# View API Gateway logs
aws logs tail API-Gateway-Execution-Logs_YOUR_API_ID/prod --follow --region us-gov-west-1
```

### DynamoDB Monitoring
```bash
# Check table status
aws dynamodb describe-table --table-name EmailContacts --region us-gov-west-1
aws dynamodb describe-table --table-name EmailCampaigns --region us-gov-west-1
aws dynamodb describe-table --table-name EmailConfig --region us-gov-west-1
```

---

## 🔄 Updating the Application

To update the Lambda function after making changes:

```bash
python deploy_bulk_email_api.py
```

This will update the existing Lambda function with new code.

---

## 📝 Additional Resources

- [README_SecretsManager.md](README_SecretsManager.md) - Secrets Manager setup details
- [secrets_manager_policy.json](secrets_manager_policy.json) - IAM policy template
- [sample_contacts.csv](sample_contacts.csv) - Example CSV format

---

## ✅ Deployment Checklist

- [ ] Step 1: DynamoDB tables created
- [ ] Step 2: AWS Secrets Manager secret created
- [ ] Step 3: Lambda function deployed
- [ ] Step 4: IAM permissions configured
- [ ] Step 5: Tests passed
- [ ] Step 6: Web UI accessible
- [ ] Configuration saved in web UI
- [ ] Contacts imported
- [ ] Test campaign sent successfully

---

## 🎉 You're Done!

Your bulk email system is now deployed and ready to use!

Access your application at:
```
https://YOUR_API_ID.execute-api.us-gov-west-1.amazonaws.com/prod
```

For support or questions, check the CloudWatch logs or review the troubleshooting section above.
