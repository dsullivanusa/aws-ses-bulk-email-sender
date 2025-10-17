# ⚡ Quick Start Guide

Deploy the bulk email system in minutes!

## 🚀 One-Command Deployment

```bash
python deploy_complete.py
```

That's it! The script will automatically:
1. ✅ Create DynamoDB tables
2. ✅ Check for AWS Secrets Manager secret
3. ✅ Deploy Lambda function
4. ✅ Create API Gateway
5. ✅ Configure permissions
6. ✅ Run tests

## 📋 Before You Start

Make sure you have:
- [ ] AWS CLI configured with GovCloud credentials
- [ ] Python 3.9+ installed
- [ ] Boto3 installed (`pip install boto3`)

## 🔐 One-Time Secret Setup

Before running the deployment, create your AWS SES credentials secret:

```bash
python setup_email_credentials_secret.py create
```

Enter your AWS SES credentials when prompted.

## 🎯 Manual Deployment (Step by Step)

If you prefer to deploy manually:

### Step 1: Create Tables
```bash
python dynamodb_table_setup.py
python dynamodb_campaigns_table.py
python create_email_config_table.py
```

### Step 2: Create Secret
```bash
python setup_email_credentials_secret.py create
```

### Step 3: Deploy Application
```bash
python deploy_bulk_email_api.py
```

### Step 4: Add Permissions
```bash
aws iam put-role-policy \
  --role-name bulk-email-api-lambda-role \
  --policy-name SecretsManagerAccess \
  --policy-document file://secrets_manager_policy.json \
  --region us-gov-west-1
```

### Step 5: Test
```bash
python test_email_config.py
```

## 🌐 Access Your Application

After deployment, access your web UI at:
```
https://YOUR_API_ID.execute-api.us-gov-west-1.amazonaws.com/prod
```

The deployment script will display your actual URL.

## 📝 Configure and Use

1. **Configure Email Service**
   - Open web UI
   - Go to ⚙️ Email Config tab
   - Select AWS SES or SMTP
   - Enter your secret name
   - Save configuration

2. **Add Contacts**
   - Go to 👥 Contacts tab
   - Upload CSV or add manually

3. **Send Campaign**
   - Go to 📧 Send Campaign tab
   - Create your campaign
   - Click 🚀 Send Campaign

## 🆘 Need Help?

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions and troubleshooting.

## 📦 Files Overview

| File | Purpose |
|------|---------|
| `deploy_complete.py` | **One-command deployment** |
| `deploy_bulk_email_api.py` | Deploy Lambda + API Gateway |
| `setup_email_credentials_secret.py` | Create AWS Secrets Manager secret |
| `test_email_config.py` | Test deployment |
| `bulk_email_api_lambda.py` | Main Lambda function |
| `secrets_manager_policy.json` | IAM policy for Secrets Manager |

---

**🎉 That's all you need to get started!**
