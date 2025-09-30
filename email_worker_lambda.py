"""
Email Worker Lambda Function
Processes email messages from SQS queue and sends them via SES or SMTP
"""

import json
import boto3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
campaigns_table = dynamodb.Table('EmailCampaigns')
secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')

def lambda_handler(event, context):
    """Process SQS messages and send emails"""
    
    print(f"Processing {len(event['Records'])} messages from SQS")
    
    results = {
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for record in event['Records']:
        try:
            # Parse message body
            message = json.loads(record['body'])
            
            campaign_id = message.get('campaign_id')
            contact = message.get('contact', {})
            email_config = message.get('config', {})
            subject = message.get('subject', '')
            body = message.get('body', '')
            
            print(f"Processing email for {contact.get('email')} (Campaign: {campaign_id})")
            
            # Personalize content
            personalized_subject = personalize_content(subject, contact)
            personalized_body = personalize_content(body, contact)
            
            # Send email based on service type
            if email_config.get('email_service') == 'ses':
                success = send_ses_email(email_config, contact, personalized_subject, personalized_body)
            else:
                success = send_smtp_email(email_config, contact, personalized_subject, personalized_body)
            
            if success:
                results['successful'] += 1
                print(f"✓ Email sent successfully to {contact.get('email')}")
                
                # Update campaign sent count
                try:
                    campaigns_table.update_item(
                        Key={'campaign_id': campaign_id},
                        UpdateExpression="SET sent_count = sent_count + :inc",
                        ExpressionAttributeValues={':inc': 1}
                    )
                except Exception as e:
                    print(f"Warning: Could not update campaign stats: {e}")
            else:
                results['failed'] += 1
                error_msg = f"Failed to send email to {contact.get('email')}"
                results['errors'].append(error_msg)
                print(f"✗ {error_msg}")
                
                # Update campaign failed count
                try:
                    campaigns_table.update_item(
                        Key={'campaign_id': campaign_id},
                        UpdateExpression="SET failed_count = failed_count + :inc",
                        ExpressionAttributeValues={':inc': 1}
                    )
                except Exception as e:
                    print(f"Warning: Could not update campaign stats: {e}")
                    
        except Exception as e:
            results['failed'] += 1
            error_msg = f"Error processing message: {str(e)}"
            results['errors'].append(error_msg)
            print(f"✗ {error_msg}")
    
    print(f"Batch processing complete: {results['successful']} sent, {results['failed']} failed")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_aws_credentials_from_secrets_manager(secret_name):
    """Retrieve AWS credentials from Secrets Manager"""
    try:
        print(f"Retrieving credentials from secret: {secret_name}")
        response = secrets_client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret (assuming it's stored as JSON)
        secret_data = json.loads(response['SecretString'])
        
        credentials = {
            'aws_access_key_id': secret_data.get('aws_access_key_id'),
            'aws_secret_access_key': secret_data.get('aws_secret_access_key')
        }
        
        if not credentials['aws_access_key_id'] or not credentials['aws_secret_access_key']:
            raise ValueError("Missing aws_access_key_id or aws_secret_access_key in secret")
        
        return credentials
        
    except Exception as e:
        print(f"Error retrieving credentials from Secrets Manager: {str(e)}")
        raise

def send_ses_email(config, contact, subject, body):
    """Send email via AWS SES"""
    try:
        # Get credentials from Secrets Manager
        credentials = get_aws_credentials_from_secrets_manager(config.get('aws_secret_name'))
        
        ses_client = boto3.client(
            'ses',
            region_name=config.get('aws_region', 'us-gov-west-1'),
            aws_access_key_id=credentials['aws_access_key_id'],
            aws_secret_access_key=credentials['aws_secret_access_key']
        )
        
        ses_client.send_email(
            Source=config['from_email'],
            Destination={'ToAddresses': [contact['email']]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': body}}
            }
        )
        return True
    except Exception as e:
        print(f"SES Error: {str(e)}")
        return False

def send_smtp_email(config, contact, subject, body):
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = contact['email']
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(config['smtp_server'], int(config['smtp_port'])) as server:
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        return False

def personalize_content(content, contact):
    """Replace placeholders with contact data"""
    if not content:
        return content
        
    content = content.replace('{{first_name}}', contact.get('first_name', ''))
    content = content.replace('{{last_name}}', contact.get('last_name', ''))
    content = content.replace('{{email}}', contact.get('email', ''))
    content = content.replace('{{company}}', contact.get('company', ''))
    return content
