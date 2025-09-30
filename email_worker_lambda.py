"""
Email Worker Lambda Function
Processes email messages from SQS queue
Retrieves campaign data and contact data from DynamoDB
Sends emails via AWS SES
"""

import json
import boto3
import logging
from decimal import Decimal
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
campaigns_table = dynamodb.Table('EmailCampaigns')
contacts_table = dynamodb.Table('EmailContacts')
secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')

def lambda_handler(event, context):
    """Process SQS messages and send emails"""
    
    start_time = datetime.now()
    logger.info(f"Lambda invocation started at {start_time.isoformat()}")
    logger.info(f"Processing {len(event['Records'])} messages from SQS queue")
    logger.info(f"Request ID: {context.request_id}")
    logger.info(f"Function Name: {context.function_name}")
    logger.info(f"Memory Limit: {context.memory_limit_in_mb} MB")
    
    results = {
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for idx, record in enumerate(event['Records'], 1):
        message_id = record.get('messageId', 'unknown')
        logger.info(f"[Message {idx}/{len(event['Records'])}] Processing message ID: {message_id}")
        
        try:
            # Parse message body (contains only campaign_id and contact_email)
            message = json.loads(record['body'])
            logger.debug(f"[Message {idx}] Raw message body: {record['body']}")
            
            campaign_id = message.get('campaign_id')
            contact_email = message.get('contact_email')
            
            if not campaign_id or not contact_email:
                raise ValueError("Missing campaign_id or contact_email in message")
            
            logger.info(f"[Message {idx}] Campaign ID: {campaign_id}, Contact: {contact_email}")
            
            # Retrieve campaign data from DynamoDB
            logger.info(f"[Message {idx}] Retrieving campaign data from DynamoDB")
            campaign_response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
            if 'Item' not in campaign_response:
                logger.error(f"[Message {idx}] Campaign {campaign_id} not found in DynamoDB")
                raise ValueError(f"Campaign {campaign_id} not found in DynamoDB")
            
            campaign = campaign_response['Item']
            logger.info(f"[Message {idx}] Campaign retrieved: {campaign.get('campaign_name', 'Unnamed')}")
            
            # Convert Decimal types to appropriate Python types
            for key, value in campaign.items():
                if isinstance(value, Decimal):
                    campaign[key] = int(value) if value % 1 == 0 else float(value)
            
            # Retrieve contact data from DynamoDB
            logger.info(f"[Message {idx}] Retrieving contact data from DynamoDB")
            contact_response = contacts_table.get_item(Key={'email': contact_email})
            if 'Item' not in contact_response:
                logger.warning(f"[Message {idx}] Contact {contact_email} not found in DynamoDB")
                raise ValueError(f"Contact {contact_email} not found in DynamoDB")
            
            contact = contact_response['Item']
            logger.info(f"[Message {idx}] Contact retrieved: {contact.get('first_name', '')} {contact.get('last_name', '')}")
            
            # Extract campaign details
            subject = campaign.get('subject', '')
            body = campaign.get('body', '')
            from_email = campaign.get('from_email', '')
            email_service = campaign.get('email_service', 'ses')
            
            logger.info(f"[Message {idx}] Email service: {email_service}")
            logger.info(f"[Message {idx}] From: {from_email}")
            logger.info(f"[Message {idx}] To: {contact_email}")
            
            # Personalize content
            personalized_subject = personalize_content(subject, contact)
            personalized_body = personalize_content(body, contact)
            
            logger.info(f"[Message {idx}] Subject: {personalized_subject}")
            logger.debug(f"[Message {idx}] Body length: {len(personalized_body)} characters")
            
            # Send email via AWS SES or SMTP
            logger.info(f"[Message {idx}] Sending email via {email_service.upper()}")
            send_start = datetime.now()
            
            if email_service == 'ses':
                success = send_ses_email(campaign, contact, from_email, personalized_subject, personalized_body, idx)
            else:
                success = send_smtp_email(campaign, contact, from_email, personalized_subject, personalized_body, idx)
            
            send_duration = (datetime.now() - send_start).total_seconds()
            logger.info(f"[Message {idx}] Email send attempt completed in {send_duration:.2f} seconds")
            
            if success:
                results['successful'] += 1
                logger.info(f"[Message {idx}] SUCCESS: Email sent to {contact_email}")
                
                # Update campaign sent count
                try:
                    campaigns_table.update_item(
                        Key={'campaign_id': campaign_id},
                        UpdateExpression="SET sent_count = sent_count + :inc",
                        ExpressionAttributeValues={':inc': 1}
                    )
                    logger.debug(f"[Message {idx}] Campaign stats updated (sent_count incremented)")
                except Exception as e:
                    logger.warning(f"[Message {idx}] Could not update campaign stats: {str(e)}")
            else:
                results['failed'] += 1
                error_msg = f"Failed to send email to {contact_email}"
                results['errors'].append(error_msg)
                logger.error(f"[Message {idx}] FAILED: {error_msg}")
                
                # Update campaign failed count
                try:
                    campaigns_table.update_item(
                        Key={'campaign_id': campaign_id},
                        UpdateExpression="SET failed_count = failed_count + :inc",
                        ExpressionAttributeValues={':inc': 1}
                    )
                    logger.debug(f"[Message {idx}] Campaign stats updated (failed_count incremented)")
                except Exception as e:
                    logger.warning(f"[Message {idx}] Could not update campaign stats: {str(e)}")
                    
        except Exception as e:
            results['failed'] += 1
            error_msg = f"Error processing message: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"[Message {idx}] EXCEPTION: {error_msg}")
            logger.exception(f"[Message {idx}] Stack trace:")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"=" * 80)
    logger.info(f"Batch processing complete")
    logger.info(f"Total messages: {len(event['Records'])}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Average: {duration/len(event['Records']):.2f} seconds per message")
    if results['errors']:
        logger.error(f"Errors encountered: {len(results['errors'])}")
        for error in results['errors']:
            logger.error(f"  - {error}")
    logger.info(f"=" * 80)
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_aws_credentials_from_secrets_manager(secret_name, msg_idx=0):
    """Retrieve AWS credentials from Secrets Manager"""
    try:
        logger.info(f"[Message {msg_idx}] Retrieving credentials from Secrets Manager")
        logger.debug(f"[Message {msg_idx}] Secret name: {secret_name}")
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        
        # Parse the secret (assuming it's stored as JSON)
        secret_data = json.loads(response['SecretString'])
        
        credentials = {
            'aws_access_key_id': secret_data.get('aws_access_key_id'),
            'aws_secret_access_key': secret_data.get('aws_secret_access_key')
        }
        
        if not credentials['aws_access_key_id'] or not credentials['aws_secret_access_key']:
            logger.error(f"[Message {msg_idx}] Missing credentials in secret")
            raise ValueError("Missing aws_access_key_id or aws_secret_access_key in secret")
        
        logger.info(f"[Message {msg_idx}] Successfully retrieved AWS credentials from Secrets Manager")
        return credentials
        
    except Exception as e:
        logger.error(f"[Message {msg_idx}] Error retrieving credentials from Secrets Manager: {str(e)}")
        raise

def send_ses_email(campaign, contact, from_email, subject, body, msg_idx=0):
    """Send email via AWS SES using IAM role or Secrets Manager credentials"""
    try:
        aws_region = campaign.get('aws_region', 'us-gov-west-1')
        secret_name = campaign.get('aws_secret_name')
        
        # Check if we should use IAM role or explicit credentials
        if secret_name:
            # Use credentials from Secrets Manager (for cross-account or specific credentials)
            logger.info(f"[Message {msg_idx}] Using credentials from Secrets Manager")
            credentials = get_aws_credentials_from_secrets_manager(secret_name, msg_idx)
            
            ses_client = boto3.client(
                'ses',
                region_name=aws_region,
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )
        else:
            # Use Lambda's IAM role (recommended for same-account SES)
            logger.info(f"[Message {msg_idx}] Using Lambda IAM role for SES authentication")
            ses_client = boto3.client('ses', region_name=aws_region)
        
        logger.info(f"[Message {msg_idx}] Creating SES client for region: {aws_region}")
        
        # Send email
        logger.info(f"[Message {msg_idx}] Calling SES send_email API")
        logger.debug(f"[Message {msg_idx}] From: {from_email}, To: {contact['email']}")
        
        response = ses_client.send_email(
            Source=from_email,
            Destination={'ToAddresses': [contact['email']]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': body}}
            }
        )
        
        message_id = response.get('MessageId', 'unknown')
        logger.info(f"[Message {msg_idx}] SES send successful. Message ID: {message_id}")
        return True
        
    except Exception as e:
        logger.error(f"[Message {msg_idx}] SES Error: {str(e)}")
        logger.exception(f"[Message {msg_idx}] SES Exception details:")
        return False

def send_smtp_email(campaign, contact, from_email, subject, body, msg_idx=0):
    """Send email via SMTP"""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        smtp_server = campaign.get('smtp_server')
        smtp_port = int(campaign.get('smtp_port', 25))
        
        logger.info(f"[Message {msg_idx}] Connecting to SMTP server: {smtp_server}:{smtp_port}")
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = contact['email']
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        logger.debug(f"[Message {msg_idx}] SMTP message prepared")
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.info(f"[Message {msg_idx}] Sending via SMTP")
            server.send_message(msg)
        
        logger.info(f"[Message {msg_idx}] SMTP send successful")
        return True
        
    except Exception as e:
        logger.error(f"[Message {msg_idx}] SMTP Error: {str(e)}")
        logger.exception(f"[Message {msg_idx}] SMTP Exception details:")
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