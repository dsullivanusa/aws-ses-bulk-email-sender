# Bulk Email Sender - AWS SES

A professional bulk email sending application with a GUI interface similar to Mailchimp, built with Python and AWS SES.

## Features

- **Modern GUI Interface**: Clean, tabbed interface for easy navigation
- **AWS SES Integration**: Reliable email delivery using Amazon Simple Email Service
- **Contact Management**: Import/export contacts via CSV files
- **Email Templates**: HTML email templates with personalization
- **Campaign Management**: Send tracking and progress monitoring
- **Rate Limiting**: Control sending speed to comply with SES limits
- **Personalization**: Dynamic content with {{first_name}}, {{last_name}}, {{email}}, {{company}} placeholders

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. AWS SES Configuration
1. Set up AWS SES in your AWS account
2. Verify your sender email address in SES console
3. If in sandbox mode, verify recipient email addresses
4. Create IAM user with SES sending permissions

### 3. Run the Application
```bash
python bulk_email_sender.py
```

## Usage Guide

### 1. AWS Configuration Tab
- Enter your AWS credentials and region
- Set your verified sender email address
- Test the SES connection

### 2. Contacts Tab
- Import contacts from CSV file (use sample_contacts.csv as template)
- Add individual contacts manually
- Export your contact list

### 3. Email Template Tab
- Create HTML email templates
- Use personalization placeholders: {{first_name}}, {{last_name}}, {{email}}, {{company}}
- Load/save templates from files
- Preview emails before sending

### 4. Send Campaign Tab
- Set campaign name and sending rate
- Monitor progress with real-time updates
- View detailed sending results

## CSV Format

Your contact CSV file should have these columns:
```
email,first_name,last_name,company
john.doe@example.com,John,Doe,Tech Corp
jane.smith@example.com,Jane,Smith,Design Studio
```

## AWS SES Limits

- **Sandbox Mode**: 200 emails per 24 hours, 1 email per second
- **Production Mode**: Higher limits based on your account
- Always respect AWS SES sending limits to avoid account suspension

## Security Notes

- Store AWS credentials securely
- Use IAM roles with minimal required permissions
- Never commit credentials to version control
- Consider using AWS credential profiles instead of hardcoded keys

## Troubleshooting

### Common Issues:
1. **SES Connection Failed**: Check credentials and region
2. **Email Not Delivered**: Verify sender/recipient emails in SES
3. **Rate Limit Exceeded**: Reduce sending rate in campaign settings
4. **Template Not Loading**: Check file path and permissions

## License

This project is for educational and commercial use. Ensure compliance with email marketing regulations (CAN-SPAM, GDPR, etc.) in your jurisdiction.