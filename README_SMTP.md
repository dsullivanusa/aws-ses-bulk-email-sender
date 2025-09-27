# SMTP Bulk Email Sender with Attachments

Alternative email sending solution using SMTP relay servers instead of AWS SES, with full attachment support.

## Features

- **SMTP Relay Support**: Works with any SMTP server (Gmail, Outlook, custom servers)
- **Attachment Support**: Send files with your email campaigns
- **Multiple Interfaces**: Desktop GUI and Web UI options
- **Contact Management**: CSV import/export functionality
- **Email Personalization**: Dynamic content with placeholders
- **Progress Tracking**: Real-time sending progress and results

## SMTP Servers Supported

### Gmail
- Server: `smtp.gmail.com`
- Port: `587` (TLS) or `465` (SSL)
- Requires App Password (not regular password)

### Outlook/Hotmail
- Server: `smtp-mail.outlook.com`
- Port: `587`
- Use regular credentials

### Custom SMTP
- Configure your own SMTP server settings
- Supports TLS/SSL encryption

## Setup Instructions

### 1. Install Dependencies
```bash
pip install smtplib ssl email
```

### 2. Gmail Setup (if using Gmail)
1. Enable 2-Factor Authentication
2. Generate App Password: Google Account → Security → App passwords
3. Use App Password instead of regular password

### 3. Run Applications

**Desktop GUI:**
```bash
python smtp_gui_client.py
```

**Web UI:**
Open `web_ui_smtp.html` in browser

## Usage Guide

### 1. SMTP Configuration
- Enter SMTP server details
- Test connection before sending
- Save configuration for future use

### 2. Contact Management
- Import contacts from CSV
- Add contacts manually
- Export contact lists

### 3. Email Template with Attachments
- Create HTML email content
- Add multiple file attachments
- Use personalization placeholders
- Preview before sending

### 4. Send Campaign
- Configure campaign settings
- Monitor real-time progress
- View detailed results

## Attachment Support

**Supported File Types:**
- Documents: PDF, DOC, DOCX, TXT
- Images: JPG, PNG, GIF
- Archives: ZIP, RAR
- Any file type supported

**Size Limits:**
- Depends on SMTP server limits
- Gmail: 25MB total per email
- Most servers: 10-25MB limit

## Personalization Placeholders

- `{{first_name}}` - Contact's first name
- `{{last_name}}` - Contact's last name
- `{{email}}` - Contact's email address
- `{{company}}` - Contact's company

## Security Notes

- Use App Passwords for Gmail (never regular passwords)
- Enable TLS encryption for secure transmission
- Store credentials securely
- Test with small batches first

## Troubleshooting

### Common Issues:

**Authentication Failed:**
- Use App Password for Gmail
- Check username/password
- Verify 2FA is enabled (Gmail)

**Connection Timeout:**
- Check server/port settings
- Verify firewall settings
- Try different port (587 vs 465)

**Attachment Too Large:**
- Check file size limits
- Compress large files
- Split into multiple emails

**Rate Limiting:**
- Add delays between emails
- Use smaller batch sizes
- Check provider limits

## Advantages over SES

- **No AWS Account Required**: Works with any SMTP provider
- **Attachment Support**: Native file attachment capability
- **Familiar Setup**: Standard SMTP configuration
- **Cost Effective**: Use existing email accounts
- **No Regional Restrictions**: Works globally

## File Structure

- `smtp_email_sender.py` - Core SMTP sending logic
- `smtp_gui_client.py` - Desktop GUI application
- `web_ui_smtp.html` - Web-based interface
- `smtp_config.json` - Saved SMTP configuration

## Lambda Integration

The SMTP sender can also be deployed as a Lambda function with environment variables for SMTP configuration, providing serverless email sending without AWS SES dependency.