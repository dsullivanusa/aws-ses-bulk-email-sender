# 🔐 Using IAM Role for AWS SES (Recommended)

## Overview

The email worker Lambda function now supports **two authentication methods** for AWS SES:

1. **IAM Role** (Recommended) ✅ - Lambda uses its own IAM role
2. **Secrets Manager** (Optional) - Explicit credentials for cross-account access

## 🎯 IAM Role Method (Recommended)

### **Benefits:**
- ✅ **More Secure** - No credentials stored anywhere
- ✅ **Simpler Setup** - No Secrets Manager needed
- ✅ **Automatic Rotation** - AWS manages credentials
- ✅ **Cost Effective** - No Secrets Manager charges
- ✅ **AWS Best Practice** - Follows AWS security guidelines
- ✅ **Easier Audit** - CloudTrail shows all actions

### **How It Works:**

1. Lambda function runs with IAM role `email-worker-lambda-role`
2. Role has SES permissions attached
3. Boto3 automatically uses role credentials
4. No explicit credentials needed in code

### **Code:**
```python
# Lambda automatically uses its IAM role
ses_client = boto3.client('ses', region_name='us-gov-west-1')
ses_client.send_email(...)  # Just works!
```

## 🔧 Setup Instructions

### **Step 1: Leave Secret Name Empty in Web UI**

When configuring email settings:
- Go to **Email Config** tab
- Select **AWS SES**
- Enter **AWS Region** (e.g., `us-gov-west-1`)
- **Leave "AWS Secrets Manager Secret Name" empty** ⚠️
- Click **Save Configuration**

### **Step 2: Ensure Lambda Has SES Permissions**

The deployment script automatically adds these permissions to the Lambda role:

```json
{
  "Effect": "Allow",
  "Action": [
    "ses:SendEmail",
    "ses:SendRawEmail"
  ],
  "Resource": "*"
}
```

This is done via the AWS managed policy: `AmazonSESFullAccess`

### **Step 3: Deploy the Lambda**

```bash
python deploy_email_worker.py
```

This automatically:
- ✅ Creates IAM role `email-worker-lambda-role`
- ✅ Attaches `AmazonSESFullAccess` policy
- ✅ Deploys Lambda function with the role

## 📊 Comparison: IAM Role vs Secrets Manager

| Feature | IAM Role | Secrets Manager |
|---------|----------|-----------------|
| **Security** | Excellent | Good |
| **Setup Complexity** | Simple | Complex |
| **Cost** | Free | $0.40/month per secret |
| **Credential Rotation** | Automatic | Manual |
| **Cross-Account** | No | Yes |
| **AWS Best Practice** | Yes | For cross-account only |
| **Audit Trail** | CloudTrail | CloudTrail + Secrets Manager |

## 🔍 When to Use Each Method

### **Use IAM Role When:**
- ✅ Lambda and SES are in the **same AWS account**
- ✅ You want the **simplest setup**
- ✅ Following **AWS best practices**
- ✅ **Most common scenario** (recommended)

### **Use Secrets Manager When:**
- 🔄 Need **cross-account access** (Lambda in Account A, SES in Account B)
- 🔄 Need **specific user credentials** (not role-based)
- 🔄 Have **compliance requirements** for credential storage
- 🔄 Need to **share credentials** across multiple services

## 🚀 Quick Start (IAM Role Method)

### **1. Configure Email Settings:**
```
Email Service: AWS SES
AWS Region: us-gov-west-1
AWS Secrets Manager Secret Name: [LEAVE EMPTY]
From Email: noreply@example.com
Emails per minute: 60
```

### **2. Deploy Lambda:**
```bash
python deploy_email_worker.py
```

### **3. Test Campaign:**
- Add contacts in web UI
- Create campaign
- Click "Send Campaign"
- Check CloudWatch logs

## 📝 IAM Policy Required

The Lambda's IAM role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail",
        "ses:GetSendQuota",
        "ses:GetSendStatistics"
      ],
      "Resource": "*"
    }
  ]
}
```

This is included in the `AmazonSESFullAccess` managed policy automatically attached by the deployment script.

## 🔍 Verification

### **Check Lambda IAM Role:**
```bash
aws iam get-role --role-name email-worker-lambda-role --region us-gov-west-1
```

### **Check Attached Policies:**
```bash
aws iam list-attached-role-policies --role-name email-worker-lambda-role --region us-gov-west-1
```

### **Test SES Access:**
```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws-us-gov:iam::ACCOUNT_ID:role/email-worker-lambda-role \
  --action-names ses:SendEmail \
  --region us-gov-west-1
```

## 📊 Lambda Logs

When using IAM role, you'll see this in CloudWatch Logs:

```
[INFO] [Message 1] Using Lambda IAM role for SES authentication
[INFO] [Message 1] Creating SES client for region: us-gov-west-1
[INFO] [Message 1] Calling SES send_email API
[INFO] [Message 1] SES send successful. Message ID: 01000...
```

When using Secrets Manager, you'll see:

```
[INFO] [Message 1] Using credentials from Secrets Manager
[INFO] [Message 1] Retrieving credentials from Secrets Manager
[INFO] [Message 1] Successfully retrieved AWS credentials
[INFO] [Message 1] Creating SES client for region: us-gov-west-1
[INFO] [Message 1] Calling SES send_email API
[INFO] [Message 1] SES send successful. Message ID: 01000...
```

## 🐛 Troubleshooting

### **Error: "User is not authorized to perform: ses:SendEmail"**

**Solution:** Add SES permissions to Lambda role:
```bash
aws iam attach-role-policy \
  --role-name email-worker-lambda-role \
  --policy-arn arn:aws-us-gov:iam::aws:policy/AmazonSESFullAccess \
  --region us-gov-west-1
```

### **Error: "Email address is not verified"**

**Solution:** Verify sender email in SES:
```bash
aws ses verify-email-identity --email-address noreply@example.com --region us-gov-west-1
```

### **Still Using Secrets Manager Accidentally?**

1. Go to web UI → Email Config
2. Clear the "AWS Secrets Manager Secret Name" field
3. Click "Save Configuration"
4. Send a new campaign

## 🎯 Migration from Secrets Manager to IAM Role

If you're currently using Secrets Manager and want to switch to IAM role:

### **Step 1: Update Configuration**
- Open web UI
- Go to Email Config
- Clear "AWS Secrets Manager Secret Name" field
- Save

### **Step 2: Verify Lambda Role**
```bash
aws iam get-role-policy \
  --role-name email-worker-lambda-role \
  --policy-name SESFullAccess \
  --region us-gov-west-1
```

### **Step 3: Test**
- Send a test campaign
- Check CloudWatch logs for "Using Lambda IAM role"
- Verify emails are sent

### **Step 4: (Optional) Delete Secret**
If no longer needed:
```bash
aws secretsmanager delete-secret \
  --secret-id email-api-credentials \
  --region us-gov-west-1
```

## ✅ Best Practices

1. **Use IAM Role** for same-account SES access
2. **Verify sender email** in SES before sending
3. **Monitor CloudWatch** logs for authentication method
4. **Set SES sending limits** appropriately
5. **Use IAM policies** with least privilege
6. **Enable CloudTrail** for audit logging

## 📚 Related Documentation

- [AWS SES IAM Policies](https://docs.aws.amazon.com/ses/latest/dg/control-user-access.html)
- [Lambda IAM Roles](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)
- [Boto3 Credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)

---

**Recommended Setup:** Use IAM role by leaving the secret name field empty in the web UI! 🎉
