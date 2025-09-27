import json
import boto3
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
import os
from datetime import datetime
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
contacts_table = dynamodb.Table('EmailContacts')
campaigns_table = dynamodb.Table('EmailCampaigns')

def lambda_handler(event, context):
    """VPC API Gateway Lambda handler for SMTP email operations"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    try:
        if event['httpMethod'] == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}
        
        path = event['resource']
        method = event['httpMethod']
        body = json.loads(event['body']) if event.get('body') else {}
        
        # VPC endpoint validation
        if not is_vpc_request(event):
            return {'statusCode': 403, 'headers': headers, 'body': json.dumps({'error': 'VPC access required'})}
        
        if path == '/smtp-campaign' and method == 'POST':
            return send_smtp_campaign(body, headers)
        elif path == '/campaign-status/{campaign_id}' and method == 'GET':
            campaign_id = event['pathParameters']['campaign_id']
            return get_campaign_status(campaign_id, headers)
        elif path == '/contacts' and method == 'GET':
            return get_contacts(headers)
        elif path == '/contacts' and method == 'POST':
            return add_contact(body, headers)
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}
            
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def is_vpc_request(event):
    """Validate request comes from VPC"""
    request_context = event.get('requestContext', {})
    domain_name = request_context.get('domainName', '')
    
    # VPC endpoint domain pattern
    if 'vpce-' in domain_name or 'execute-api' in domain_name:
        return True
    
    # Check source IP is private
    source_ip = request_context.get('identity', {}).get('sourceIp', '')
    if source_ip.startswith(('10.', '172.', '192.168.')):
        return True
    
    return False

def send_smtp_campaign(body, headers):
    """Send SMTP email campaign with attachments in VPC"""
    
    campaign_id = f"vpc_smtp_campaign_{int(datetime.now().timestamp())}"
    
    # Get SMTP config from environment or body
    smtp_config = {
        'server': os.environ.get('SMTP_SERVER') or body.get('smtp_server'),
        'port': int(os.environ.get('SMTP_PORT', '587')),
        'username': os.environ.get('SMTP_USERNAME') or body.get('smtp_username'),
        'password': os.environ.get('SMTP_PASSWORD') or body.get('smtp_password'),
        'use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    }
    
    # Get contacts from DynamoDB
    response = contacts_table.scan()
    contacts = response['Items']
    
    # Initialize campaign status
    campaigns_table.put_item(
        Item={
            'campaign_id': campaign_id,
            'campaign_name': body.get('campaign_name', 'VPC SMTP Campaign'),
            'status': 'in_progress',
            'total_contacts': len(contacts),
            'sent_count': 0,
            'failed_count': 0,
            'vpc_endpoint': True,
            'smtp_server': smtp_config['server'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    )
    
    # Process attachments
    attachments = []
    if body.get('attachments'):
        for att in body['attachments']:
            attachments.append({
                'filename': att['filename'],
                'content': base64.b64decode(att['content']),
                'content_type': att.get('content_type', 'application/octet-stream')
            })
    
    sent_count = 0
    failed_count = 0
    results = []
    
    # Send emails via SMTP
    for contact in contacts:
        try:
            success = send_smtp_email(
                smtp_config,
                body['from_email'],
                contact['email'],
                personalize_content(body['subject'], contact),
                personalize_content(body['body'], contact),
                attachments
            )
            
            if success:
                sent_count += 1
                update_contact_email_sent(contact['email'], body.get('campaign_name', 'VPC SMTP'))
                results.append({'email': contact['email'], 'status': 'sent'})
            else:
                failed_count += 1
                results.append({'email': contact['email'], 'status': 'failed'})
            
            # Update campaign progress
            campaigns_table.update_item(
                Key={'campaign_id': campaign_id},
                UpdateExpression="SET sent_count = :sent, failed_count = :failed, updated_at = :updated",
                ExpressionAttributeValues={
                    ':sent': sent_count,
                    ':failed': failed_count,
                    ':updated': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            failed_count += 1
            results.append({'email': contact['email'], 'status': 'failed', 'error': str(e)})
    
    # Mark campaign complete
    campaigns_table.update_item(
        Key={'campaign_id': campaign_id},
        UpdateExpression="SET #status = :status, sent_count = :sent, failed_count = :failed, updated_at = :updated",
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': 'completed',
            ':sent': sent_count,
            ':failed': failed_count,
            ':updated': datetime.now().isoformat()
        }
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'campaign_id': campaign_id,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_contacts': len(contacts),
            'vpc_endpoint': True,
            'smtp_server': smtp_config['server'],
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    }

def send_smtp_email(smtp_config, from_email, to_email, subject, body, attachments=None):
    """Send single SMTP email with attachments"""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        if attachments:
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename= {attachment["filename"]}')
                msg.attach(part)
        
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            if smtp_config['use_tls']:
                server.starttls(context=context)
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        return False

def get_campaign_status(campaign_id, headers):
    """Get campaign progress status"""
    try:
        response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
        
        if 'Item' not in response:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Campaign not found'})}
        
        campaign = response['Item']
        
        for key, value in campaign.items():
            if isinstance(value, Decimal):
                campaign[key] = int(value)
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(campaign)}
        
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def get_contacts(headers):
    """Get all contacts from DynamoDB"""
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
    
    return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'contacts': contacts, 'count': len(contacts)})}

def add_contact(body, headers):
    """Add new contact to DynamoDB"""
    contact = body['contact']
    
    contacts_table.put_item(
        Item={
            'email': contact['email'],
            'first_name': contact.get('first_name', ''),
            'last_name': contact.get('last_name', ''),
            'company': contact.get('company', ''),
            'created_at': datetime.now().isoformat(),
            'last_email_sent': None,
            'email_count': 0
        }
    )
    
    return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': 'Contact added successfully'})}

def update_contact_email_sent(email, campaign_name):
    """Update contact with last email sent timestamp"""
    contacts_table.update_item(
        Key={'email': email},
        UpdateExpression="SET last_email_sent = :timestamp, last_campaign = :campaign, email_count = email_count + :inc",
        ExpressionAttributeValues={
            ':timestamp': datetime.now().isoformat(),
            ':campaign': campaign_name,
            ':inc': 1
        }
    )

def personalize_content(content, contact):
    """Replace placeholders with contact data"""
    content = content.replace('{{first_name}}', contact.get('first_name', ''))
    content = content.replace('{{last_name}}', contact.get('last_name', ''))
    content = content.replace('{{email}}', contact.get('email', ''))
    content = content.replace('{{company}}', contact.get('company', ''))
    return content