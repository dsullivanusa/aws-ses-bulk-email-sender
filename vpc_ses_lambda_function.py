import json
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import base64
import os
from datetime import datetime
from decimal import Decimal

# Initialize clients
ses = boto3.client('ses', region_name='us-gov-west-1')
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
contacts_table = dynamodb.Table('EmailContacts')
campaigns_table = dynamodb.Table('EmailCampaigns')

def lambda_handler(event, context):
    """VPC API Gateway Lambda handler for SES email operations"""
    
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
        source_vpc = event.get('requestContext', {}).get('identity', {}).get('sourceIp')
        if not is_vpc_request(event):
            return {'statusCode': 403, 'headers': headers, 'body': json.dumps({'error': 'VPC access required'})}
        
        if path == '/ses-campaign' and method == 'POST':
            return send_ses_campaign(body, headers)
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
    # Check for VPC endpoint or private IP
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

def send_ses_campaign(body, headers):
    """Send SES email campaign with attachments in VPC"""
    
    campaign_id = f"vpc_ses_campaign_{int(datetime.now().timestamp())}"
    
    # Get contacts from DynamoDB
    response = contacts_table.scan()
    contacts = response['Items']
    
    # Initialize campaign status
    campaigns_table.put_item(
        Item={
            'campaign_id': campaign_id,
            'campaign_name': body.get('campaign_name', 'VPC SES Campaign'),
            'status': 'in_progress',
            'total_contacts': len(contacts),
            'sent_count': 0,
            'failed_count': 0,
            'vpc_endpoint': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
    )
    
    sent_count = 0
    failed_count = 0
    results = []
    
    # Send emails via SES
    for contact in contacts:
        try:
            success = send_ses_email_with_attachments(
                body['from_email'],
                contact['email'],
                personalize_content(body['subject'], contact),
                personalize_content(body['body'], contact),
                body.get('attachments', [])
            )
            
            if success:
                sent_count += 1
                update_contact_email_sent(contact['email'], body.get('campaign_name', 'VPC Campaign'))
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
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    }

def send_ses_email_with_attachments(from_email, to_email, subject, body, attachments):
    """Send SES email with attachments using raw email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        for attachment in attachments:
            file_content = base64.b64decode(attachment['content'])
            part = MIMEApplication(file_content)
            part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'])
            msg.attach(part)
        
        response = ses.send_raw_email(
            Source=from_email,
            Destinations=[to_email],
            RawMessage={'Data': msg.as_string()}
        )
        
        return True
        
    except Exception as e:
        print(f"SES Error: {str(e)}")
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