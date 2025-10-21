import json
import boto3
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
ses = boto3.client('ses', region_name='us-gov-west-1')
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
contacts_table = dynamodb.Table('EmailContacts')

def lambda_handler(event, context):
    """
    API Gateway Lambda handler for bulk email operations
    """
    
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
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
        path = event.get('resource', event.get('path', '/'))
        method = event['httpMethod']
        
        # Parse request body with error handling
        try:
            if event.get('body'):
                body_str = event.get('body', '{}')
                print(f"📨 Request: {method} {path} (body length: {len(body_str)} chars)")
                body = json.loads(body_str)
            else:
                body = {}
        except json.JSONDecodeError as je:
            print(f"❌ JSON decode error: {str(je)}")
            print(f"   Body preview: {event.get('body', '')[:500]}")
            return {
                'statusCode': 400, 
                'headers': headers, 
                'body': json.dumps({
                    'error': f'Invalid JSON in request body: {str(je)}',
                    'success': False
                })
            }
        
        # Route requests
        if path == '/contacts' and method == 'GET':
            return get_contacts(headers)
        elif path == '/contacts' and method == 'POST':
            return add_contact(body, headers)
        elif path == '/campaign' and method == 'POST':
            return send_campaign(body, headers)
        elif path == '/log-csv-error' and method == 'POST':
            print("   → Calling log_csv_error()")
            return log_csv_error(body, headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'Not found: {method} {path}'})
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

def log_csv_error(body, headers):
    """Log CSV parsing errors to CloudWatch"""
    try:
        row_num = body.get('row', 'Unknown')
        error_msg = body.get('error', 'No error provided')
        raw_line = body.get('rawLine', 'No raw line provided')
        
        print(f"🚨 CSV Parse Error Logged")
        print(f"   Row Number: {row_num}")
        print(f"   Error: {error_msg}")
        print(f"   Raw Line (first 500 chars): {raw_line[:500]}")
        if len(raw_line) > 500:
            print(f"   (Line truncated - full length: {len(raw_line)} chars)")
        
        # Additional context if available
        if 'userAgent' in body:
            print(f"   User Agent: {body['userAgent']}")
        if 'timestamp' in body:
            print(f"   Timestamp: {body['timestamp']}")
        
        print(f"🔍 End CSV Error Log")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': f'CSV error for row {row_num} logged to CloudWatch'
            })
        }
    except Exception as e:
        print(f"❌ Error logging CSV parse error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f'Failed to log error: {str(e)}',
                'success': False
            })
        }