import json
import boto3
import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
from datetime import datetime
from decimal import Decimal
import os

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
contacts_table = dynamodb.Table('EmailContacts')
campaigns_table = dynamodb.Table('EmailCampaigns')
smtp_config_table = dynamodb.Table('SMTPConfig')

def lambda_handler(event, context):
    """SMTP Bulk Email Lambda for Load Balancer"""
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Check if this is a web UI request (GET with no body)
        if event.get('httpMethod') == 'GET' and not body:
            return serve_web_ui()
        
        action = body.get('action')
        
        if action == 'send_campaign':
            return send_bulk_campaign(body)
        elif action == 'get_campaign_status':
            return get_campaign_status(body.get('campaign_id'))
        elif action == 'get_contacts':
            return get_contacts()
        elif action == 'add_contact':
            return add_contact(body)
        elif action == 'save_smtp_config':
            return save_smtp_config(body)
        elif action == 'get_smtp_config':
            return get_smtp_config()
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def send_bulk_campaign(body):
    """Send bulk email campaign with rate limiting"""
    
    campaign_id = f"smtp_campaign_{int(datetime.now().timestamp())}"
    
    # Get SMTP configuration
    config_response = smtp_config_table.get_item(Key={'config_id': 'default'})
    if 'Item' not in config_response:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'SMTP configuration not found'})
        }
    
    smtp_config = config_response['Item']
    
    # Get all contacts
    response = contacts_table.scan()
    contacts = response['Items']
    
    # Rate limiting settings
    emails_per_minute = body.get('emails_per_minute', 60)  # Default 60 emails/minute
    batch_size = body.get('batch_size', 10)  # Process in batches
    delay_between_emails = 60 / emails_per_minute  # Seconds between emails
    
    # Initialize campaign
    campaigns_table.put_item(
        Item={
            'campaign_id': campaign_id,
            'campaign_name': body.get('campaign_name', 'Bulk SMTP Campaign'),
            'status': 'in_progress',
            'total_contacts': len(contacts),
            'sent_count': 0,
            'failed_count': 0,
            'emails_per_minute': emails_per_minute,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    )
    
    sent_count = 0
    failed_count = 0
    
    # Process contacts in batches with rate limiting
    for i in range(0, len(contacts), batch_size):
        batch = contacts[i:i + batch_size]
        
        for contact in batch:
            try:
                success = send_smtp_email(
                    smtp_config,
                    contact['email'],
                    personalize_content(body['subject'], contact),
                    personalize_content(body['body'], contact)
                )
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                
                # Rate limiting delay
                time.sleep(delay_between_emails)
                
            except Exception as e:
                failed_count += 1
                print(f"Error sending to {contact['email']}: {str(e)}")
        
        # Update campaign progress after each batch
        campaigns_table.update_item(
            Key={'campaign_id': campaign_id},
            UpdateExpression="SET sent_count = :sent, failed_count = :failed, updated_at = :updated",
            ExpressionAttributeValues={
                ':sent': sent_count,
                ':failed': failed_count,
                ':updated': datetime.now().isoformat()
            }
        )
    
    # Mark campaign complete
    campaigns_table.update_item(
        Key={'campaign_id': campaign_id},
        UpdateExpression="SET #status = :status, updated_at = :updated",
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': 'completed',
            ':updated': datetime.now().isoformat()
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'campaign_id': campaign_id,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_contacts': len(contacts),
            'emails_per_minute': emails_per_minute
        })
    }

def send_smtp_email(smtp_config, to_email, subject, body):
    """Send single SMTP email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_config['from_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to SMTP server
        with smtplib.SMTP(smtp_config['smtp_server'], int(smtp_config['smtp_port'])) as server:
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        return False

def get_campaign_status(campaign_id):
    """Get campaign status"""
    try:
        response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Campaign not found'})
            }
        
        campaign = response['Item']
        
        # Convert Decimal to int for JSON serialization
        for key, value in campaign.items():
            if isinstance(value, Decimal):
                campaign[key] = int(value)
        
        return {
            'statusCode': 200,
            'body': json.dumps(campaign)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_contacts():
    """Get all contacts"""
    response = contacts_table.scan()
    
    contacts = []
    for item in response['Items']:
        contact = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                contact[key] = int(value)
            else:
                contact[key] = value
        contacts.append(contact)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'contacts': contacts, 'count': len(contacts)})
    }

def add_contact(body):
    """Add new contact"""
    contact = body.get('contact', body)
    
    contacts_table.put_item(
        Item={
            'email': contact['email'],
            'first_name': contact.get('first_name', ''),
            'last_name': contact.get('last_name', ''),
            'company': contact.get('company', ''),
            'created_at': datetime.now().isoformat()
        }
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'success': True})
    }

def save_smtp_config(body):
    """Save SMTP configuration"""
    try:
        smtp_config_table.put_item(
            Item={
                'config_id': 'default',
                'smtp_server': body.get('smtp_server', '192.168.1.100'),
                'smtp_port': body.get('smtp_port', 25),
                'from_email': body.get('from_email', ''),
                'use_tls': False,
                'updated_at': datetime.now().isoformat()
            }
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_smtp_config():
    """Get SMTP configuration"""
    try:
        response = smtp_config_table.get_item(Key={'config_id': 'default'})
        
        if 'Item' in response:
            config = response['Item']
            return {
                'statusCode': 200,
                'body': json.dumps({'config': config})
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Config not found'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def serve_web_ui():
    """Serve simple web UI for SMTP bulk email"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>SMTP Bulk Email Sender</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; margin-bottom: 10px; }
        button { padding: 10px 20px; background: #007cba; color: white; border: none; cursor: pointer; }
        .result { margin: 20px 0; padding: 10px; background: #f0f0f0; }
    </style>
</head>
<body>
    <h1>SMTP Bulk Email Sender</h1>
    
    <h2>SMTP Configuration</h2>
    <div class="form-group">
        <label>SMTP Server:</label>
        <input type="text" id="smtpServer" value="192.168.1.100">
    </div>
    <div class="form-group">
        <label>SMTP Port:</label>
        <input type="number" id="smtpPort" value="25">
    </div>
    <div class="form-group">
        <label>From Email:</label>
        <input type="email" id="fromEmail" placeholder="sender@domain.com">
    </div>
    <button onclick="saveSMTPConfig()">Save SMTP Config</button>
    
    <h2>Send Campaign</h2>
    <div class="form-group">
        <label>Campaign Name:</label>
        <input type="text" id="campaignName" placeholder="My Campaign">
    </div>
    <div class="form-group">
        <label>Subject:</label>
        <input type="text" id="subject" placeholder="Hello {{first_name}}">
    </div>
    <div class="form-group">
        <label>Email Body:</label>
        <textarea id="body" rows="5" placeholder="Dear {{first_name}}, ..."></textarea>
    </div>
    <div class="form-group">
        <label>Emails per minute:</label>
        <input type="number" id="emailsPerMinute" value="60">
    </div>
    <button onclick="sendCampaign()">Send Campaign</button>
    
    <div id="result" class="result" style="display:none;"></div>
    
    <script>
        async function saveSMTPConfig() {
            const config = {
                action: 'save_smtp_config',
                smtp_server: document.getElementById('smtpServer').value,
                smtp_port: parseInt(document.getElementById('smtpPort').value),
                from_email: document.getElementById('fromEmail').value
            };
            
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            showResult('SMTP Config: ' + JSON.stringify(result));
        }
        
        async function sendCampaign() {
            const campaign = {
                action: 'send_campaign',
                campaign_name: document.getElementById('campaignName').value,
                subject: document.getElementById('subject').value,
                body: document.getElementById('body').value,
                emails_per_minute: parseInt(document.getElementById('emailsPerMinute').value)
            };
            
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(campaign)
            });
            
            const result = await response.json();
            showResult('Campaign: ' + JSON.stringify(result));
        }
        
        function showResult(message) {
            const resultDiv = document.getElementById('result');
            resultDiv.textContent = message;
            resultDiv.style.display = 'block';
        }
    </script>
</body>
</html>
    """
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html_content
    }

def personalize_content(content, contact):
    """Replace placeholders with contact data"""
    content = content.replace('{{first_name}}', contact.get('first_name', ''))
    content = content.replace('{{last_name}}', contact.get('last_name', ''))
    content = content.replace('{{email}}', contact.get('email', ''))
    content = content.replace('{{company}}', contact.get('company', ''))
    return content