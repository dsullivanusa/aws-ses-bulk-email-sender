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
    Lambda function to send bulk emails and track in DynamoDB
    """
    try:
        action = event.get('action')
        
        if action == 'send_campaign':
            return send_campaign(event)
        elif action == 'add_contact':
            return add_contact(event)
        elif action == 'get_contacts':
            return get_contacts()
        elif action == 'update_contact':
            return update_contact(event)
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

def send_campaign(event):
    """Send email campaign to all contacts"""
    subject = event['subject']
    body = event['body']
    from_email = event['from_email']
    campaign_name = event.get('campaign_name', 'Untitled Campaign')
    
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
            personalized_body = personalize_content(body, contact)
            
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
        'body': json.dumps({
            'campaign_name': campaign_name,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_contacts': len(contacts),
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    }

def add_contact(event):
    """Add new contact to DynamoDB"""
    contact = event['contact']
    
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
        'body': json.dumps({'message': 'Contact added successfully'})
    }

def get_contacts():
    """Get all contacts from DynamoDB"""
    response = contacts_table.scan()
    
    # Convert Decimal to float for JSON serialization
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
        'body': json.dumps({
            'contacts': contacts,
            'count': len(contacts)
        })
    }

def update_contact(event):
    """Update existing contact"""
    email = event['email']
    updates = event['updates']
    
    update_expression = "SET "
    expression_values = {}
    
    for key, value in updates.items():
        if key != 'email':  # Don't update primary key
            update_expression += f"{key} = :{key}, "
            expression_values[f":{key}"] = value
    
    update_expression = update_expression.rstrip(', ')
    
    contacts_table.update_item(
        Key={'email': email},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Contact updated successfully'})
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