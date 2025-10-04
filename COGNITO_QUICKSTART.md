# 🚀 Cognito Authentication - Quick Start

## Enable AWS Cognito Login in 5 Minutes

This guide will enable secure Cognito authentication for your Web UI.

---

## ⚡ Quick Setup (5 Steps)

### 1️⃣ Create Cognito User Pool (1 minute)

```bash
python setup_cognito_auth.py
```

Answer "yes" when prompted.

**Result:** User Pool created, config saved to `cognito_config.json`

---

### 2️⃣ Create Your First User (30 seconds)

```bash
python create_cognito_user.py your.email@example.com "Your Name"
```

**Result:** User created, invitation email sent

---

### 3️⃣ Upload Configuration to S3 (10 seconds)

```bash
# Upload config so Lambda can read it
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
```

---

### 4️⃣ Enable Authentication (10 seconds)

```bash
python enable_cognito_auth.py

# Re-upload updated config
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
```

---

### 5️⃣ Deploy Lambda (30 seconds)

```bash
python update_lambda.py
```

**Result:** Authentication is now ENABLED! 🎉

---

## ✅ Test It

1. Open your Web UI in browser
2. You'll see login page (not the campaign form)
3. Enter email and temporary password (from email)
4. Set new password when prompted
5. You're in! Campaign form appears with your name auto-filled

---

## 🔄 To Disable (Return to Simple Mode)

```bash
python disable_cognito_auth.py
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
python update_lambda.py
```

**Result:** Back to simple name field (no login required)

---

## 👥 Manage Users

### Add User
```bash
python create_cognito_user.py email@example.com "Full Name"
```

### List Users
```bash
python list_cognito_users.py
```

### Reset Password
```bash
python reset_cognito_password.py email@example.com
```

### Delete User
```bash
python delete_cognito_user.py email@example.com
```

---

## 🎯 What You Get

### Before (No Cognito):
```
Web UI → User enters name manually → Campaign sent
```

### After (With Cognito):
```
Web UI → User logs in → Identity from Cognito → Campaign sent
       ↓
   Secure, verified, tracked
```

---

## 📊 Files Created

| File | Purpose |
|------|---------|
| `cognito_config.json` | Configuration (local + S3) |
| `setup_cognito_auth.py` | Initial setup script |
| `create_cognito_user.py` | Add users |
| `enable_cognito_auth.py` | Turn on auth |
| `disable_cognito_auth.py` | Turn off auth |
| `list_cognito_users.py` | View all users |
| `reset_cognito_password.py` | Password reset |
| `delete_cognito_user.py` | Remove users |

---

## 🆘 Troubleshooting

### Can't see login page?
**Fix:** Check if config uploaded to S3
```bash
aws s3 ls s3://jcdc-ses-contact-list/cognito_config.json
```

### Still shows name field?
**Fix:** Config not enabled or Lambda not redeployed
```bash
cat cognito_config.json | grep enabled
# Should show: "enabled": true

python update_lambda.py
```

### Forgot password?
**Fix:** Reset it
```bash
python reset_cognito_password.py your.email@example.com
```

---

## 💡 Pro Tips

### Bulk Create Users
```bash
# Create multiple users at once
for email in user1@example.com user2@example.com user3@example.com; do
    python create_cognito_user.py $email "User Name"
done
```

### Import from CSV
Create `users.csv`:
```csv
email,name
john@example.com,John Smith
jane@example.com,Jane Doe
```

Then:
```bash
python import_cognito_users.py users.csv
```

### Backup Configuration
```bash
cp cognito_config.json cognito_config.backup.json
```

---

## 🎓 Decision Matrix

### Use Cognito When:
- ✅ You need verified user identities
- ✅ You have 2+ users
- ✅ You want accountability
- ✅ You need password protection
- ✅ You're in production

### Use Simple Mode When:
- ✅ Quick testing
- ✅ Single user
- ✅ Development environment
- ✅ Proof of concept
- ✅ Low security needs

---

## 🔐 Security Notes

- **Cognito = Verified Identity**
- **Simple Mode = Trust-Based**
- **Both track IP addresses**
- **Both store campaign history**
- **Cognito adds email/password layer**

---

## 📈 Next Steps

After setup:
1. ✅ Create users for your team
2. ✅ Test login with each user
3. ✅ Send test campaign
4. ✅ Verify identity in tracking reports
5. ✅ Train team on new login process

---

## 📚 Full Documentation

See `COGNITO_AUTH_GUIDE.md` for complete details.

---

**That's it! You now have optional Cognito authentication!** 🔐✨

Switch it on/off anytime with no code changes.

