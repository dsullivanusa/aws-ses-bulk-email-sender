# 📋 Files to Run for Deployment

## ⚡ FASTEST WAY (Recommended)

### **One Command Deployment:**
```bash
python deploy_complete.py
```

This automatically runs everything for you!

---

## 🔧 Manual Deployment (Step by Step)

If you prefer to run each step manually:

### **1. Set Up AWS Secrets (ONE TIME ONLY)**
```bash
python setup_email_credentials_secret.py create
```
**What it does:** Creates a secret in AWS Secrets Manager to store your AWS SES credentials securely.

**You'll need:**
- Secret name (e.g., "email-api-credentials")
- Your AWS Access Key ID
- Your AWS Secret Access Key

---

### **2. Create Database Tables**
```bash
python dynamodb_table_setup.py
python dynamodb_campaigns_table.py
python create_email_config_table.py
```
**What it does:** Creates 3 DynamoDB tables:
- `EmailContacts` - stores your contact list
- `EmailCampaigns` - tracks campaign status
- `EmailConfig` - stores email configuration

---

### **3. Deploy the Application**
```bash
python deploy_bulk_email_api.py
```
**What it does:**
- Creates IAM role with permissions
- Packages and deploys Lambda function
- Creates API Gateway
- Connects everything together

**Output:** Your API URL

---

### **4. Add Secrets Manager Permissions**
```bash
aws iam put-role-policy \
  --role-name bulk-email-api-lambda-role \
  --policy-name SecretsManagerAccess \
  --policy-document file://secrets_manager_policy.json \
  --region us-gov-west-1
```
**What it does:** Allows Lambda to read credentials from Secrets Manager

---

### **5. Test Everything**
```bash
python test_email_config.py
```
**What it does:** Verifies all components are working correctly

---

## 📁 Core Files You Need

### **Essential Files:**
- `bulk_email_api_lambda.py` - Main application code
- `deploy_complete.py` - Automated deployment script
- `deploy_bulk_email_api.py` - Manual deployment script
- `setup_email_credentials_secret.py` - Secret management
- `secrets_manager_policy.json` - IAM policy for Secrets Manager
- `dynamodb_table_setup.py` - Creates EmailContacts table
- `dynamodb_campaigns_table.py` - Creates EmailCampaigns table
- `create_email_config_table.py` - Creates EmailConfig table
- `test_email_config.py` - Test suite

### **Optional Files:**
- `sample_contacts.csv` - Example contact list format
- `DEPLOYMENT_GUIDE.md` - Detailed deployment instructions
- `QUICKSTART.md` - Quick start guide
- `README_SecretsManager.md` - Secrets Manager documentation

---

## 🎯 Quick Reference

### **First Time Setup:**
```bash
# 1. Create secret
python setup_email_credentials_secret.py create

# 2. Deploy everything
python deploy_complete.py
```

### **Update Application After Changes:**
```bash
python deploy_bulk_email_api.py
```

### **Manage Secrets:**
```bash
# List secrets
python setup_email_credentials_secret.py list

# Test secret retrieval
python setup_email_credentials_secret.py test email-api-credentials

# Update secret
python setup_email_credentials_secret.py create
```

### **Test Deployment:**
```bash
python test_email_config.py
```

---

## 🚀 Deployment Flowchart

```
START
  ↓
Create AWS Secret (setup_email_credentials_secret.py)
  ↓
Create DynamoDB Tables (dynamodb_*.py)
  ↓
Deploy Lambda + API Gateway (deploy_bulk_email_api.py)
  ↓
Add IAM Permissions (aws iam put-role-policy)
  ↓
Test Deployment (test_email_config.py)
  ↓
Access Web UI
  ↓
DONE! 🎉
```

---

## ⚙️ What Each Script Does

| Script | Purpose | Run When |
|--------|---------|----------|
| `deploy_complete.py` | **Runs everything automatically** | **First deployment** |
| `setup_email_credentials_secret.py` | Manages AWS Secrets Manager secret | Before first deployment |
| `dynamodb_table_setup.py` | Creates EmailContacts table | First deployment only |
| `dynamodb_campaigns_table.py` | Creates EmailCampaigns table | First deployment only |
| `create_email_config_table.py` | Creates EmailConfig table | First deployment only |
| `deploy_bulk_email_api.py` | Deploys Lambda + API Gateway | First time & updates |
| `test_email_config.py` | Tests the deployment | After deployment |

---

## 💡 Pro Tips

1. **Use `deploy_complete.py`** - It handles everything for you
2. **Keep your secret name** - You'll need it when configuring the web UI
3. **Run tests** - Always test after deployment
4. **Check CloudWatch logs** - If something goes wrong, logs are your friend
5. **Update frequently** - Run `deploy_bulk_email_api.py` to deploy code changes

---

## 🆘 Troubleshooting

### **"Module not found" errors:**
```bash
pip install boto3
```

### **"Credentials not configured" errors:**
```bash
aws configure
# Enter your AWS GovCloud credentials
```

### **"Table already exists" errors:**
- This is normal! The scripts skip existing tables

### **"Permission denied" errors:**
- Make sure your AWS user has appropriate permissions
- Check IAM policies

### **Can't access web UI:**
- If using private API, access from VPC or VPN
- Check API Gateway resource policy
- Review IP whitelist

---

## 📞 Getting Help

- **Detailed Guide:** See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Quick Start:** See [QUICKSTART.md](QUICKSTART.md)
- **Secrets Setup:** See [README_SecretsManager.md](README_SecretsManager.md)
- **CloudWatch Logs:** Check Lambda and API Gateway logs for errors

---

**Remember:** Just run `python deploy_complete.py` and let it handle everything! 🚀
