import json
import boto3
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
ses = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')
contacts_table = dynamodb.Table('EmailContacts')

def lambda_handler(event, context):
    """
    API Gateway Lambda handler for bulk email operations
    """
    
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event['httpMethod'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Parse request
        path = event['resource']
        method = event['httpMethod']
        body = json.loads(event['body']) if event.get('body') else {}
        
        # Route requests
        if path == '/contacts' and method == 'GET':
            return get_contacts(headers)
        elif path == '/contacts' and method == 'POST':
            return add_contact(body, headers)
        elif path == '/campaign' and method == 'POST':
            return send_campaign(body, headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_contacts(headers):
    """Get all contacts from DynamoDB"""
    response = contacts_table.scan()
    
    # Convert Decimal to int for JSON serialization
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
        'headers': headers,
        'body': json.dumps({
            'contacts': contacts,
            'count': len(contacts)
        })
    }

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
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'Contact added successfully'})
    }

def send_campaign(body, headers):
    """Send email campaign to all contacts"""
    subject = body['subject']
    email_body = body['body']
    from_email = body['from_email']
    campaign_name = body.get('campaign_name', 'Untitled Campaign')
    
    # Get all contacts
    response = contacts_table.scan()
    contacts = response['Items']
    
    sent_count = 0
    failed_count = 0
    results = []
    
    for contact in contacts:
        try:
            # Personalize content
            personalized_subject = personalize_content(subject, contact)
            personalized_body = personalize_content(email_body, contact)
            
            # Send email via SES
            ses_response = ses.send_email(
                Source=from_email,
                Destination={'ToAddresses': [contact['email']]},
                Message={
                    'Subject': {'Data': personalized_subject},
                    'Body': {'Html': {'Data': personalized_body}}
                }
            )
            
            # Update contact with last email sent date
            update_last_email_sent(contact['email'], campaign_name)
            
            sent_count += 1
            results.append({
                'email': contact['email'],
                'status': 'sent',
                'message_id': ses_response['MessageId']
            })
            
        except Exception as e:
            failed_count += 1
            results.append({
                'email': contact['email'],
                'status': 'failed',
                'error': str(e)
            })
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'campaign_name': campaign_name,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_contacts': len(contacts),
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    }

def update_last_email_sent(email, campaign_name):
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