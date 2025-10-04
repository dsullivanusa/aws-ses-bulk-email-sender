# 🔐 AWS Cognito Authentication - Implementation Guide

## Overview
Optional AWS Cognito authentication for the Web UI. When enabled, users must log in with their credentials before accessing the email campaign system. User identity is automatically captured from their Cognito profile.

---

## 🎯 Features

### With Cognito Enabled:
- ✅ **Secure Login**: Username/password authentication
- ✅ **Automatic Identity**: User name captured from Cognito profile
- ✅ **No Manual Entry**: User never types their name
- ✅ **Email Verification**: Users verify email on signup
- ✅ **Password Reset**: Self-service password recovery
- ✅ **Session Management**: Secure token-based sessions
- ✅ **User Management**: Centralized user administration
- ✅ **Audit Trail**: WHO did WHAT tracked automatically

### With Cognito Disabled (Default):
- ⚡ **Simple Access**: No login required
- 📝 **Name Field**: User enters name manually (saved in browser)
- 🚀 **Quick Start**: No authentication setup needed

---

## 📋 Setup Instructions

### Step 1: Create Cognito User Pool

```bash
python setup_cognito_auth.py
```

This creates:
- User Pool for authentication
- App Client for Web UI
- Cognito Domain for hosted UI
- Configuration file (`cognito_config.json`)

**Output:**
```
User Pool ID:    us-gov-west-1_aBcDeFgHi
App Client ID:   1234567890abcdefghijklmnop
Region:          us-gov-west-1
Cognito Domain:  bulk-email-auth.auth.us-gov-west-1.amazoncognito.com

Configuration saved to: cognito_config.json
Status: DISABLED (enable with: python enable_cognito_auth.py)
```

### Step 2: Create Users

Create administrator and user accounts:

```bash
# Create admin user
python create_cognito_user.py admin@example.com "Admin User"

# Create regular users
python create_cognito_user.py john.smith@example.com "John Smith"
python create_cognito_user.py jane.doe@example.com "Jane Doe"

# Create user with temporary password
python create_cognito_user.py user@example.com "Test User" "TempPass123!"
```

**Users will receive invitation emails** with temporary passwords (if no password specified).

### Step 3: Upload Configuration to S3

```bash
# Upload cognito_config.json to S3 (Lambda reads from here)
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
```

### Step 4: Enable Cognito Authentication

```bash
python enable_cognito_auth.py
```

This updates `cognito_config.json` to set `"enabled": true`.

### Step 5: Re-upload Configuration

```bash
# Upload updated config
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
```

### Step 6: Deploy Updated Lambda

```bash
python update_lambda.py
```

### Step 7: Test Login

1. Open Web UI in browser
2. You'll see Cognito login page
3. Enter email and password
4. Access granted after successful login

---

## 🔄 Enabling/Disabling Authentication

### To Enable:
```bash
python enable_cognito_auth.py
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
python update_lambda.py
```

### To Disable:
```bash
python disable_cognito_auth.py
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1
python update_lambda.py
```

**No code changes needed** - just update config and redeploy!

---

## 👥 User Management

### List All Users
```bash
python list_cognito_users.py
```

### Delete User
```bash
python delete_cognito_user.py user@example.com
```

### Reset Password
```bash
python reset_cognito_password.py user@example.com
```

---

## 🔐 How It Works

### Authentication Flow:

```
1. User opens Web UI
   ↓
2. Lambda checks: COGNITO_CONFIG['enabled']
   ↓
3a. If ENABLED:
   ├─> Show Cognito login page
   ├─> User enters credentials
   ├─> Cognito validates
   ├─> Returns JWT token with user info
   └─> Token includes: email, name
       ↓
4a. Campaign sent:
   ├─> Extract name from JWT: "John Smith"
   ├─> Append IP: "John Smith (IP: 192.168.1.100)"
   └─> Store in DynamoDB

3b. If DISABLED:
   ├─> Show simple name field
   ├─> User enters name (saved in browser)
   └─> Continue as before
```

### User Identity Capture (Cognito Enabled):

**1. User logs in:**
```javascript
// Cognito returns JWT token with user attributes
{
  "email": "john.smith@example.com",
  "name": "John Smith",
  "email_verified": true,
  ...
}
```

**2. Campaign sent:**
```javascript
// Extract from token automatically
const userName = userSession.getIdToken().payload.name;
// "John Smith"
```

**3. Backend records:**
```json
{
  "campaign_id": "campaign_1728057600",
  "campaign_name": "Security Update",
  "launched_by": "John Smith (john.smith@example.com) (IP: 192.168.1.100)",
  ...
}
```

---

## 📊 Configuration File Format

**`cognito_config.json`:**
```json
{
  "user_pool_id": "us-gov-west-1_aBcDeFgHi",
  "app_client_id": "1234567890abcdefghijklmnop",
  "region": "us-gov-west-1",
  "cognito_domain": "bulk-email-auth.auth.us-gov-west-1.amazoncognito.com",
  "enabled": false
}
```

**Change `enabled` to `true` to activate authentication.**

---

## 🎨 User Experience

### With Cognito Enabled:

**First Visit:**
```
┌─────────────────────────────────────────┐
│  🔐 Login Required                      │
├─────────────────────────────────────────┤
│  Email:    [_____________________]      │
│  Password: [_____________________]      │
│                                          │
│  [🚀 Sign In]    [Forgot Password?]     │
└─────────────────────────────────────────┘
```

**After Login:**
```
┌─────────────────────────────────────────┐
│  Welcome, John Smith! [Logout]          │
├─────────────────────────────────────────┤
│  📧 Send Campaign                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Logged in as: john.smith@example.com   │
│  Your campaigns will be tracked as:     │
│  "John Smith"                           │
└─────────────────────────────────────────┘
```

### With Cognito Disabled (Default):

```
┌─────────────────────────────────────────┐
│  📧 Send Campaign                       │
├─────────────────────────────────────────┤
│  👤 Your Name: [John Smith_______]      │
│  (Saved in your browser)                │
└─────────────────────────────────────────┘
```

---

## 🛡️ Security Features

### Password Policy:
- Minimum 8 characters
- Requires uppercase letter
- Requires lowercase letter
- Requires number
- Optional symbols

### Session Security:
- Token expires after 1 hour (access token)
- Refresh token valid for 30 days
- Automatic token refresh
- Secure HTTPS only

### User Verification:
- Email verification required
- Password reset via email
- Account recovery options

---

## 📈 Advantages

### Vs. Manual Name Entry:
| Feature | Cognito | Manual Entry |
|---------|---------|--------------|
| **Identity Verification** | ✅ Verified | ❌ Trust-based |
| **User Management** | ✅ Centralized | ❌ None |
| **Password Protection** | ✅ Yes | ❌ No |
| **Audit Trail** | ✅ Complete | ⚠️ IP only |
| **Account Control** | ✅ Enable/Disable | ❌ None |
| **Setup Complexity** | ⚠️ Medium | ✅ None |
| **User Friction** | ⚠️ Login required | ✅ Instant access |

---

## 🔍 Monitoring & Logging

### View Login Activity:
```bash
# CloudWatch Logs
aws logs tail /aws/cognito/userpools/us-gov-west-1_aBcDeFgHi --follow
```

### View Campaign Activity:
```bash
# Use existing tracking tools
python campaign_tracking_gui.py
```

**Campaigns show full user identity:**
```
Campaign: Security Alert
Launched By: John Smith (john.smith@example.com) (IP: 192.168.1.100)
Created: 2025-10-04 10:00
```

---

## 🚀 Production Checklist

### Before Enabling in Production:

- [ ] User Pool created and configured
- [ ] All users created with verified emails
- [ ] Users tested login successfully
- [ ] Configuration uploaded to S3
- [ ] Lambda deployed with Cognito support
- [ ] Password reset tested
- [ ] Session timeout tested
- [ ] Multi-device testing completed
- [ ] Backup admin account created
- [ ] Monitoring/logging configured
- [ ] Documentation shared with team

---

## 🆘 Troubleshooting

### Issue: Can't log in

**Check:**
1. User exists: `python list_cognito_users.py`
2. Email verified: Check user attributes
3. Correct password: Try password reset
4. Config enabled: Check `cognito_config.json`

**Solution:**
```bash
# Reset password
python reset_cognito_password.py user@example.com
```

### Issue: Shows name field instead of login

**Cause:** Cognito not enabled or config not uploaded

**Solution:**
```bash
# Verify config
cat cognito_config.json | grep enabled
# Should show: "enabled": true

# Verify uploaded to S3
aws s3 ls s3://jcdc-ses-contact-list/cognito_config.json

# Re-upload if needed
aws s3 cp cognito_config.json s3://jcdc-ses-contact-list/cognito_config.json --region us-gov-west-1

# Redeploy Lambda
python update_lambda.py
```

### Issue: Token expired

**Cause:** Session timeout after 1 hour

**Solution:**
- User logs in again
- Or implement auto-refresh (see advanced section)

---

## 🔧 Advanced Configuration

### Custom Password Policy:

Edit `setup_cognito_auth.py`:
```python
'PasswordPolicy': {
    'MinimumLength': 12,  # Longer passwords
    'RequireSymbols': True,  # Require symbols
    ...
}
```

### Custom Domain:

```bash
# Use your own domain instead of Cognito domain
aws cognito-idp create-user-pool-domain \
  --domain your-company-auth \
  --user-pool-id us-gov-west-1_aBcDeFgHi \
  --custom-domain-config CertificateArn=arn:aws:acm:...
```

### MFA (Multi-Factor Authentication):

```python
# Add to setup_cognito_auth.py
'MfaConfiguration': 'OPTIONAL',  # or 'REQUIRED'
'EnabledMfas': ['SOFTWARE_TOKEN_MFA']
```

---

## 📝 Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup_cognito_auth.py` | Create User Pool | `python setup_cognito_auth.py` |
| `create_cognito_user.py` | Add user | `python create_cognito_user.py email "Name"` |
| `enable_cognito_auth.py` | Enable auth | `python enable_cognito_auth.py` |
| `disable_cognito_auth.py` | Disable auth | `python disable_cognito_auth.py` |
| `list_cognito_users.py` | List all users | `python list_cognito_users.py` |
| `delete_cognito_user.py` | Remove user | `python delete_cognito_user.py email` |
| `reset_cognito_password.py` | Reset password | `python reset_cognito_password.py email` |

---

## 💰 Cost Considerations

### AWS Cognito Pricing (as of 2025):
- **Free tier**: 50,000 MAUs (Monthly Active Users)
- **After free tier**: $0.00550 per MAU
- **For 10 users**: FREE
- **For 100 users**: FREE
- **For 1000 users**: FREE

**Bottom line:** Likely FREE for most deployments!

---

## 🎓 Training Materials

### For End Users:

**Email Template:**
```
Subject: New Login Required for Email Campaign System

Hi Team,

We've enhanced security for our email campaign system.

What's New:
• You now need to log in with your email and password
• Your identity is automatically tracked (no more name field)
• Secure password reset if needed

Your Credentials:
• Username: your.email@example.com
• Temporary Password: (in separate email from AWS)
• Change password on first login

Login URL:
https://your-api-gateway-url/prod/

Questions? Contact IT Support.
```

### For Administrators:

See full documentation in this guide.

---

## 📚 Additional Resources

- AWS Cognito Documentation: https://docs.aws.amazon.com/cognito/
- User Pool Best Practices: https://docs.aws.amazon.com/cognito/latest/developerguide/best-practices.html
- Security Best Practices: https://aws.amazon.com/cognito/security/

---

**Authentication is now optional and easy to enable!** 🔐✅

Choose the mode that fits your needs:
- **Development/Testing**: Disabled (simple name field)
- **Production/Enterprise**: Enabled (secure login)

