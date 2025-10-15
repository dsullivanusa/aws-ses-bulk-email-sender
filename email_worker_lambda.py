"""
Email Worker Lambda Function
Processes email messages from SQS queue
Retrieves campaign data and contact data from DynamoDB
Sends emails via AWS SES with adaptive rate control
"""

import json
import boto3
import logging
import time
import os
from decimal import Decimal
from datetime import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from lib.adaptive_rate_control import AdaptiveRateControl

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Verbose logging enabled

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
campaigns_table = dynamodb.Table('EmailCampaigns')
contacts_table = dynamodb.Table('EmailContacts')
secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')
s3_client = boto3.client('s3', region_name='us-gov-west-1')
cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')

# S3 bucket for attachments
ATTACHMENTS_BUCKET = 'jcdc-ses-contact-list'

# Global rate control instance
rate_control = AdaptiveRateControl(logger)

def send_cloudwatch_metric(metric_name, value, unit='Count', dimensions=None):
    """Send custom metric to CloudWatch"""
    try:
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.now()
        }
        
        if dimensions:
            metric_data['Dimensions'] = dimensions
        
        cloudwatch.put_metric_data(
            Namespace='EmailWorker/Custom',  # Namespace goes here, not in metric_data
            MetricData=[metric_data]
        )
        
        logger.debug(f"Sent CloudWatch metric: {metric_name}={value} {unit}")
        
    except Exception as e:
        logger.warning(f"Failed to send CloudWatch metric {metric_name}: {str(e)}")

def check_campaign_completion_status(campaign_id, expected_total):
    """Check if campaign is completed and send metric if incomplete"""
    try:
        # Get current campaign status
        campaign_response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
        if 'Item' in campaign_response:
            campaign = campaign_response['Item']
            
            sent_count = campaign.get('sent_count', 0)
            failed_count = campaign.get('failed_count', 0)
            total_processed = sent_count + failed_count
            
            # Check if campaign is significantly behind
            if expected_total > 0:
                completion_percentage = (total_processed / expected_total) * 100
                
                # If less than 90% complete and we've been processing for a while
                if completion_percentage < 90:
                    logger.warning(f"Campaign {campaign_id} only {completion_percentage:.1f}% complete ({total_processed}/{expected_total})")
                    
                    # Send metric for incomplete campaign
                    print(f"📊 ERROR METRIC → CloudWatch: IncompleteCampaigns (Campaign: {campaign_id}, Completion: {completion_percentage:.1f}%)")
                    logger.warning(f"📊 Sending ERROR metric to CloudWatch: IncompleteCampaigns - Campaign {campaign_id} is {completion_percentage:.1f}% complete")
                    send_cloudwatch_metric(
                        'IncompleteCampaigns',
                        1,
                        'Count',
                        [
                            {'Name': 'CampaignId', 'Value': campaign_id},
                            {'Name': 'CompletionPercentage', 'Value': f"{completion_percentage:.1f}"}
                        ]
                    )
                    
                    return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking campaign completion status: {str(e)}")
        return True

def lambda_handler(event, context):
    """Process SQS messages and send emails with adaptive rate control"""
    
    start_time = datetime.now()
    logger.info(f"Lambda invocation started at {start_time.isoformat()}")
    logger.info(f"Processing {len(event['Records'])} messages from SQS queue")
    logger.info(f"Request ID: {context.aws_request_id}")
    logger.info(f"Function Name: {context.function_name}")
    logger.info(f"Memory Limit: {context.memory_limit_in_mb} MB")
    
    results = {
        'successful': 0,
        'failed': 0,
        'errors': [],
        'rate_control_stats': {
            'total_delay_applied': 0,
            'throttles_detected': 0,
            'attachment_delays_applied': 0
        },
        'campaigns_processed': set(),
        'total_expected_emails': 0
    }
    
    # Wrap main processing in try-catch to prevent fatal errors from causing message re-delivery
    try:
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
                
                # Track campaigns being processed
                results['campaigns_processed'].add(campaign_id)
                
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
                
                # Try to retrieve contact data from DynamoDB (optional - campaigns are independent)
                logger.info(f"[Message {idx}] Attempting to retrieve contact data from DynamoDB")
                contact = None
                
                try:
                    # Query using email-index GSI (email is not the primary key)
                    response = contacts_table.query(
                        IndexName='email-index',
                        KeyConditionExpression=Key('email').eq(contact_email),
                        Limit=1
                    )
                    
                    if response.get('Items'):
                        contact = response['Items'][0]
                        logger.info(f"[Message {idx}] Contact found: {contact.get('first_name', '')} {contact.get('last_name', '')}")
                    else:
                        logger.info(f"[Message {idx}] Contact {contact_email} not in Contacts table (using email-only mode)")
                except Exception as contact_error:
                    logger.warning(f"[Message {idx}] Could not query contact: {str(contact_error)}")
                
                # If contact not found, create minimal contact object with just email
                if not contact:
                    logger.info(f"[Message {idx}] Using email-only contact for {contact_email}")
                    contact = {
                        'email': contact_email,
                        'first_name': '',
                        'last_name': '',
                        'company': '',
                        'title': '',
                        'agency_name': ''
                    }
                
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
                
                # Check message role: normal per-contact sends vs single-send for cc/bcc/to
                role = message.get('role')  # None, 'cc', 'bcc', or 'to'

                if role in ('cc', 'bcc', 'to'):
                    # For single-send CC/BCC/To messages, do not include campaign-level CC/BCC in the envelope
                    cc_list = []
                    bcc_list = []
                    logger.info(f"[Message {idx}] Special role message detected: {role} (single-send to {contact_email})")
                else:
                    # Regular contact messages should NOT include campaign-level CC/BCC
                    # because those recipients are already getting dedicated single-send messages
                    cc_list = []
                    bcc_list = []
                    logger.info(f"[Message {idx}] Regular contact message (CC/BCC recipients get separate messages)")

                # Apply adaptive rate control delay before sending
                attachments = campaign.get('attachments', [])
                delay = rate_control.get_delay_for_email(attachments, s3_client=s3_client, attachments_bucket=ATTACHMENTS_BUCKET)
                
                if delay > 0:
                    logger.info(f"[Message {idx}] Applying adaptive rate control delay: {delay:.3f}s")
                    time.sleep(delay)
                    results['rate_control_stats']['total_delay_applied'] += delay
                    
                    # Track if delay was due to attachments
                    if attachments:
                        results['rate_control_stats']['attachment_delays_applied'] += 1
                        
                        # Send metric for attachment delays
                        total_attachment_size = 0
                        for attachment in attachments:
                            try:
                                s3_key = attachment.get('s3_key')
                                if s3_key:
                                    response = s3_client.head_object(Bucket=ATTACHMENTS_BUCKET, Key=s3_key)
                                    total_attachment_size += response.get('ContentLength', 0)
                            except:
                                total_attachment_size += 1024 * 1024  # Estimate 1MB if unknown
                        
                        send_cloudwatch_metric(
                            'AttachmentDelays',
                            len(attachments),
                            'Count',
                            [
                                {'Name': 'CampaignId', 'Value': campaign_id},
                                {'Name': 'TotalSizeMB', 'Value': f"{total_attachment_size // 1024 // 1024}"}
                            ]
                        )
                
                # Send email via AWS SES or SMTP
                logger.info(f"[Message {idx}] Sending email via {email_service.upper()}")
                send_start = datetime.now()
                
                try:
                    if email_service == 'ses':
                        success = send_ses_email(campaign, contact, from_email, personalized_subject, personalized_body, idx, cc_list=cc_list, bcc_list=bcc_list)
                    else:
                        success = send_smtp_email(campaign, contact, from_email, personalized_subject, personalized_body, idx, cc_list=cc_list, bcc_list=bcc_list)
                    
                    send_duration = (datetime.now() - send_start).total_seconds()
                    logger.info(f"[Message {idx}] Email send attempt completed in {send_duration:.2f} seconds")
                    
                except Exception as send_exception:
                    # Check if this is a throttle exception and handle it
                    if rate_control.detect_throttle_exception(send_exception):
                        results['rate_control_stats']['throttles_detected'] += 1
                        logger.warning(f"[Message {idx}] Throttle exception detected: {str(send_exception)}")
                        
                        # Send CloudWatch metric for throttle exception
                        print(f"📊 ERROR METRIC → CloudWatch: ThrottleExceptions (Campaign: {campaign_id}, Type: SES_Throttle)")
                        logger.error(f"📊 Sending ERROR metric to CloudWatch: ThrottleExceptions - Campaign {campaign_id} hit SES throttle limit")
                        send_cloudwatch_metric(
                            'ThrottleExceptions',
                            1,
                            'Count',
                            [
                                {'Name': 'CampaignId', 'Value': campaign_id},
                                {'Name': 'ErrorType', 'Value': 'SES_Throttle'}
                            ]
                        )
                        
                        # Update rate control for future emails
                        rate_control.handle_throttle_detected()
                    
                    # Re-raise the exception to be handled by the outer try-catch
                    raise send_exception
                
                if success:
                    results['successful'] += 1
                    logger.info(f"[Message {idx}] SUCCESS: Email sent to {contact_email}")
                    
                    # Update campaign sent count and timestamp
                    try:
                        # Update sent_count and set sent_at timestamp if first email
                        campaigns_table.update_item(
                            Key={'campaign_id': campaign_id},
                            UpdateExpression="SET sent_count = sent_count + :inc, sent_at = if_not_exists(sent_at, :timestamp), #status = :status",
                            ExpressionAttributeNames={'#status': 'status'},
                            ExpressionAttributeValues={
                                ':inc': 1,
                                ':timestamp': datetime.now().isoformat(),
                                ':status': 'sending'
                            }
                        )
                        logger.debug(f"[Message {idx}] Campaign stats updated (sent_count incremented, sent_at set)")
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
        
        # Check campaign completion status and send metrics
        for campaign_id in results['campaigns_processed']:
            try:
                # Get campaign details to check completion
                campaign_response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
                if 'Item' in campaign_response:
                    campaign = campaign_response['Item']
                    total_contacts = campaign.get('total_contacts', 0)
                    sent_count = campaign.get('sent_count', 0)
                    failed_count = campaign.get('failed_count', 0)
                    
                    # Check if campaign appears to be stuck or incomplete
                    if total_contacts > 0:
                        check_campaign_completion_status(campaign_id, total_contacts)
                        
                        # Calculate campaign-specific send rate
                        campaign_total_processed = sent_count + failed_count
                        if campaign_total_processed > 0 and total_contacts > 0:
                            campaign_progress = (campaign_total_processed / total_contacts) * 100
                            
                            # Send campaign-specific metrics
                            send_cloudwatch_metric(
                                'CampaignProgress',
                                campaign_progress,
                                'Percent',
                                [
                                    {'Name': 'CampaignId', 'Value': campaign_id}
                                ]
                            )
                            
                            send_cloudwatch_metric(
                                'CampaignEmailsSent',
                                sent_count,
                                'Count',
                                [
                                    {'Name': 'CampaignId', 'Value': campaign_id}
                                ]
                            )
                        
                        # Send general campaign processing metric
                        send_cloudwatch_metric(
                            'CampaignProcessing',
                            1,
                            'Count',
                            [
                                {'Name': 'CampaignId', 'Value': campaign_id},
                                {'Name': 'TotalContacts', 'Value': str(total_contacts)}
                            ]
                        )
            except Exception as e:
                logger.warning(f"Error checking campaign completion for {campaign_id}: {str(e)}")
        
        # Calculate send rate metrics
        total_emails = results['successful'] + results['failed']
        send_rate_per_second = total_emails / duration if duration > 0 else 0
        send_rate_per_minute = send_rate_per_second * 60
        success_rate = (results['successful'] / total_emails * 100) if total_emails > 0 else 0
        failure_rate = (results['failed'] / total_emails * 100) if total_emails > 0 else 0
        
        # Send batch processing metrics
        send_cloudwatch_metric('BatchProcessing', 1, 'Count')
        send_cloudwatch_metric('EmailsProcessed', total_emails, 'Count')
        send_cloudwatch_metric('EmailsSentSuccessfully', results['successful'], 'Count')
        
        # EmailsFailed metric - Log if any failures
        if results['failed'] > 0:
            print(f"📊 ERROR METRIC → CloudWatch: EmailsFailed = {results['failed']} (out of {total_emails} total)")
            logger.error(f"📊 Sending ERROR metric to CloudWatch: EmailsFailed = {results['failed']} emails failed to send")
            send_cloudwatch_metric('EmailsFailed', results['failed'], 'Count')
        
        send_cloudwatch_metric('ProcessingDuration', duration, 'Seconds')
        
        # Send rate metrics
        send_cloudwatch_metric('SendRatePerSecond', send_rate_per_second, 'Count/Second')
        send_cloudwatch_metric('SendRatePerMinute', send_rate_per_minute, 'Count/Second')  # SES measures in emails/second
        send_cloudwatch_metric('SuccessRate', success_rate, 'Percent')
        
        # FailureRate metric - Log if failure rate is significant
        if failure_rate > 0:
            print(f"📊 ERROR METRIC → CloudWatch: FailureRate = {failure_rate:.1f}%")
            logger.warning(f"📊 Sending ERROR metric to CloudWatch: FailureRate = {failure_rate:.1f}% ({results['failed']}/{total_emails})")
            send_cloudwatch_metric('FailureRate', failure_rate, 'Percent')
        
        if results['rate_control_stats']['throttles_detected'] > 0:
            print(f"📊 ERROR METRIC → CloudWatch: ThrottleExceptionsInBatch = {results['rate_control_stats']['throttles_detected']}")
            logger.error(f"📊 Sending ERROR metric to CloudWatch: ThrottleExceptionsInBatch = {results['rate_control_stats']['throttles_detected']} throttles detected in this batch")
            send_cloudwatch_metric('ThrottleExceptionsInBatch', results['rate_control_stats']['throttles_detected'], 'Count')
        
        # Log rate control statistics and send rate metrics
        rate_stats = results['rate_control_stats']
        logger.info(f"=" * 80)
        logger.info(f"📊 BATCH PROCESSING COMPLETE")
        logger.info(f"=" * 80)
        logger.info(f"Total messages: {len(event['Records'])}")
        logger.info(f"✅ Successful: {results['successful']}")
        logger.info(f"❌ Failed: {results['failed']}")
        logger.info(f"⏱️  Duration: {duration:.2f} seconds")
        logger.info(f"📈 Average: {duration/len(event['Records']):.2f} seconds per message")
        logger.info(f"📧 Campaigns processed: {len(results['campaigns_processed'])}")
        logger.info(f"-" * 80)
        logger.info(f"📊 SEND RATE METRICS")
        logger.info(f"-" * 80)
        logger.info(f"📤 Send Rate: {send_rate_per_second:.2f} emails/second")
        logger.info(f"📤 Send Rate: {send_rate_per_minute:.2f} emails/minute")
        logger.info(f"✅ Success Rate: {success_rate:.1f}%")
        logger.info(f"❌ Failure Rate: {failure_rate:.1f}%")
        logger.info(f"-" * 80)
        logger.info(f"Rate Control Statistics:")
        logger.info(f"  Total delay applied: {rate_stats['total_delay_applied']:.3f} seconds")
        logger.info(f"  Throttles detected: {rate_stats['throttles_detected']}")
        logger.info(f"  Attachment delays applied: {rate_stats['attachment_delays_applied']}")
        logger.info(f"  Current adaptive delay: {rate_control.current_delay:.3f} seconds")
        if results['errors']:
            logger.error(f"Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                logger.error(f"  - {error}")
    
    except Exception as fatal_error:
        # Critical: Catch any unhandled exceptions to prevent SQS message re-delivery
        logger.error(f"=" * 80)
        logger.error(f"❌ FATAL ERROR IN LAMBDA HANDLER")
        logger.error(f"=" * 80)
        logger.error(f"Exception Type: {type(fatal_error).__name__}")
        logger.error(f"Exception Message: {str(fatal_error)}")
        logger.exception(f"Full Stack Trace:")
        logger.error(f"=" * 80)
        logger.error(f"⚠️  RETURNING SUCCESS TO PREVENT MESSAGE RE-DELIVERY")
        logger.error(f"=" * 80)
    
    logger.info(f"=" * 80)
    
    # Convert set to list for JSON serialization (sets are not JSON serializable)
    results['campaigns_processed'] = list(results['campaigns_processed'])
    
    # Always return success (200) to ensure SQS deletes the messages
    # Even if there were errors, we've logged them and handled them gracefully
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

def hide_ses_tracking_pixel(html_body):
    """
    Inject CSS to hide AWS SES tracking pixel (1x1 image)
    AWS recommends: visibility:hidden; opacity:0; position:absolute; left:-9999px;
    """
    print("🔍 hide_ses_tracking_pixel() called")
    logger.info("🔍 hide_ses_tracking_pixel() function called")
    
    if not html_body:
        # Empty body, return as-is
        print("⚠️  Email body is empty - skipping tracking pixel CSS injection")
        logger.warning("Email body is empty - skipping tracking pixel CSS injection")
        return html_body
    
    # CSS to hide tracking pixels (1x1 images)
    # AWS Support recommends: visibility:hidden; opacity:0; position:absolute; left:-9999px;
    tracking_pixel_css = """
<style type="text/css">
    /* Hide AWS SES tracking pixel (1x1 images) - AWS Support recommended */
    img[width="1"][height="1"] {
        visibility: hidden !important;
        opacity: 0 !important;
        display: none !important;
        position: absolute !important;
        left: -9999px !important;
    }
    img[width="1px"][height="1px"] {
        visibility: hidden !important;
        opacity: 0 !important;
        display: none !important;
        position: absolute !important;
        left: -9999px !important;
    }
    /* Also hide any images with very small dimensions */
    img[style*="width: 1px"][style*="height: 1px"],
    img[style*="width:1px"][style*="height:1px"] {
        visibility: hidden !important;
        opacity: 0 !important;
        display: none !important;
        position: absolute !important;
        left: -9999px !important;
    }
    /* Catch-all for any 1-pixel images */
    img[width="1"], img[height="1"],
    img[width="1px"], img[height="1px"] {
        visibility: hidden !important;
        opacity: 0 !important;
        display: none !important;
        position: absolute !important;
        left: -9999px !important;
    }
    /* Normalize paragraph spacing for single-line spacing */
    p {
        margin: 0 !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
    }
    /* Remove extra space from empty paragraphs */
    p:empty {
        margin: 0 !important;
        line-height: 0 !important;
        height: 0 !important;
        display: none !important;
    }
    /* Ensure line height is normal */
    body, p, div {
        line-height: 1.4 !important;
    }
</style>"""
    
    # Try to insert CSS in <head> section
    import re
    
    # Check if <head> exists
    head_pattern = re.compile(r'<head[^>]*>', re.IGNORECASE)
    head_match = head_pattern.search(html_body)
    
    if head_match:
        # Insert after <head> tag
        insert_pos = head_match.end()
        html_body = html_body[:insert_pos] + tracking_pixel_css + html_body[insert_pos:]
        print("✅ CSS injected after <head> tag")
        logger.info("✅ Tracking pixel hiding CSS injected after <head> tag")
    else:
        # No <head> tag, try to insert after <html> tag
        html_pattern = re.compile(r'<html[^>]*>', re.IGNORECASE)
        html_match = html_pattern.search(html_body)
        
        if html_match:
            insert_pos = html_match.end()
            html_body = html_body[:insert_pos] + tracking_pixel_css + html_body[insert_pos:]
            print("✅ CSS injected after <html> tag (no <head> found)")
            logger.info("✅ Tracking pixel hiding CSS injected after <html> tag (no <head> found)")
        else:
            # HTML fragment without proper structure (common from Quill editor)
            # Wrap in basic HTML structure and inject CSS
            html_body = f'''<html>
<head>
{tracking_pixel_css}
</head>
<body>
{html_body}
</body>
</html>'''
            print("✅ CSS injected by wrapping HTML fragment in full HTML document")
            logger.info("✅ Tracking pixel hiding CSS injected by wrapping HTML fragment in full HTML document")
    
    print(f"✅ hide_ses_tracking_pixel() completed - CSS injected ({len(tracking_pixel_css)} chars)")
    logger.info(f"✅ hide_ses_tracking_pixel() completed - CSS successfully injected ({len(tracking_pixel_css)} characters)")
    
    return html_body

def send_ses_email(campaign, contact, from_email, subject, body, msg_idx=0, cc_list=None, bcc_list=None):
    """Send email via AWS SES using IAM role or Secrets Manager credentials with attachment support"""
    try:
        import re
        import urllib.request
        import base64
        import mimetypes
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email.mime.image import MIMEImage
        from email import encoders
        
        aws_region = campaign.get('aws_region', 'us-gov-west-1')
        secret_name = campaign.get('aws_secret_name')
        attachments = campaign.get('attachments', [])

        # Prefer message-level cc/bcc passed from the worker; otherwise fall back to campaign-level lists
        if cc_list is None:
            cc_list = campaign.get('cc') or []
        if bcc_list is None:
            bcc_list = campaign.get('bcc') or []
        
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
        logger.info(f"[Message {msg_idx}] Attachments in campaign: {len(attachments)}")
        # Diagnostic: log any <img src=> occurrences in the HTML body to help debug Outlook image prompts
        try:
            img_srcs = re.findall(r'<img[^>]+src=[\"\']([^\"\']+)[\"\']', body or '', flags=re.IGNORECASE)
            if img_srcs:
                logger.info(f"[Message {msg_idx}] Found img srcs in HTML body: {img_srcs}")
            else:
                logger.info(f"[Message {msg_idx}] No <img> tags found in HTML body")
        except Exception as img_err:
            logger.warning(f"[Message {msg_idx}] Failed to scan HTML body for <img> tags: {str(img_err)}")

        # Prepare body and inline images found in the HTML body (data:, http(s) and s3 references)
        body_with_hidden_pixel = hide_ses_tracking_pixel(body)
        logger.debug(f"[Message {msg_idx}] Applied tracking pixel hiding CSS to email body")

        pre_inline_parts = []
        pre_inline_cids = []

        try:
            img_srcs = re.findall(r'<img[^>]+src=[\"\']([^\"\']+)[\"\']', body_with_hidden_pixel or '', flags=re.IGNORECASE)
            for i_src, src in enumerate(img_srcs, 1):
                try:
                    if not src or src.lower().startswith('cid:'):
                        continue

                    # Data URI
                    if src.startswith('data:'):
                        header, b64 = src.split(',', 1)
                        if ';base64' in header:
                            mime_type = header.split(':', 1)[1].split(';', 1)[0] if ':' in header else 'image/png'
                            data_bytes = base64.b64decode(b64)
                            maintype, subtype = mime_type.split('/', 1) if '/' in mime_type else ('image', 'octet-stream')
                            if maintype.lower() == 'image':
                                try:
                                    img_part = MIMEImage(data_bytes, _subtype=subtype)
                                except Exception:
                                    img_part = MIMEBase(maintype, subtype)
                                    img_part.set_payload(data_bytes)
                                    encoders.encode_base64(img_part)
                                cid = f"inline-data-{i_src}-{int(time.time())}@inline"
                                img_part.add_header('Content-ID', f'<{cid}>')
                                img_part.add_header('Content-Disposition', 'inline')
                                pre_inline_parts.append(img_part)
                                pre_inline_cids.append({'cid': cid, 'filename': None, 's3_key': None})
                                body_with_hidden_pixel = body_with_hidden_pixel.replace(src, f'cid:{cid}')
                                logger.info(f"[Message {msg_idx}] Inlined data URI as CID <{cid}>")

                    # HTTP/HTTPS URL
                    elif src.lower().startswith('http://') or src.lower().startswith('https://'):
                        try:
                            req = urllib.request.Request(src, headers={'User-Agent': 'aws-ses-inline-agent/1.0'})
                            with urllib.request.urlopen(req, timeout=8) as resp:
                                data_bytes = resp.read()
                                content_type = resp.headers.get('Content-Type') or mimetypes.guess_type(src)[0] or 'application/octet-stream'
                            maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                            if maintype.lower() == 'image':
                                try:
                                    img_part = MIMEImage(data_bytes, _subtype=subtype)
                                except Exception:
                                    img_part = MIMEBase(maintype, subtype)
                                    img_part.set_payload(data_bytes)
                                    encoders.encode_base64(img_part)
                                cid = f"inline-http-{i_src}-{int(time.time())}@inline"
                                img_part.add_header('Content-ID', f'<{cid}>')
                                img_part.add_header('Content-Disposition', 'inline', filename=os.path.basename(src))
                                pre_inline_parts.append(img_part)
                                pre_inline_cids.append({'cid': cid, 'filename': os.path.basename(src), 's3_key': None})
                                body_with_hidden_pixel = body_with_hidden_pixel.replace(src, f'cid:{cid}')
                                logger.info(f"[Message {msg_idx}] Downloaded and inlined HTTP image as CID <{cid}>")
                        except Exception as http_err:
                            logger.warning(f"[Message {msg_idx}] Failed to download image {src}: {str(http_err)}")

                    # S3-like references
                    elif src.startswith('s3://') or (ATTACHMENTS_BUCKET in src and ('s3.amazonaws.com' in src or src.startswith('/'))):
                        s3_key_candidate = None
                        try:
                            if src.startswith('s3://'):
                                parts = src.split('/', 3)
                                s3_key_candidate = parts[3] if len(parts) > 3 else None
                            elif 's3.amazonaws.com' in src:
                                parts = src.split('/', 3)
                                s3_key_candidate = parts[3] if len(parts) > 3 else None
                            else:
                                s3_key_candidate = src.lstrip('/')

                            if s3_key_candidate:
                                try:
                                    s3_resp = s3_client.get_object(Bucket=ATTACHMENTS_BUCKET, Key=s3_key_candidate)
                                    data_bytes = s3_resp['Body'].read()
                                    content_type = s3_resp.get('ContentType') or mimetypes.guess_type(s3_key_candidate)[0] or 'application/octet-stream'
                                    maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')
                                    if maintype.lower() == 'image':
                                        try:
                                            img_part = MIMEImage(data_bytes, _subtype=subtype)
                                        except Exception:
                                            img_part = MIMEBase(maintype, subtype)
                                            img_part.set_payload(data_bytes)
                                            encoders.encode_base64(img_part)
                                        cid = f"inline-s3-{i_src}-{int(time.time())}@inline"
                                        img_part.add_header('Content-ID', f'<{cid}>')
                                        img_part.add_header('Content-Disposition', 'inline', filename=os.path.basename(s3_key_candidate))
                                        pre_inline_parts.append(img_part)
                                        pre_inline_cids.append({'cid': cid, 'filename': os.path.basename(s3_key_candidate), 's3_key': s3_key_candidate})
                                        body_with_hidden_pixel = body_with_hidden_pixel.replace(src, f'cid:{cid}')
                                        logger.info(f"[Message {msg_idx}] Inlined S3 image {s3_key_candidate} as CID <{cid}>")
                                except Exception as s3_err:
                                    logger.warning(f"[Message {msg_idx}] Could not retrieve S3 object {s3_key_candidate}: {str(s3_err)}")
                        except Exception:
                            continue

                    else:
                        logger.debug(f"[Message {msg_idx}] Found image src that may be matched to attachments later: {src}")

                except Exception as single_err:
                    logger.warning(f"[Message {msg_idx}] Error inlining image {src}: {str(single_err)}")
                    continue
        except Exception as inline_err:
            logger.warning(f"[Message {msg_idx}] Failed to scan/inline images: {str(inline_err)}")

        # If there are no attachments and no inlined HTML images, use send_email
        if not attachments and not pre_inline_parts:
            logger.info(f"[Message {msg_idx}] No attachments and no inlined HTML images - using send_email API")
            logger.info(f"[Message {msg_idx}] Sending to: {contact['email']}, From: {from_email}")
            destination = {'ToAddresses': [contact['email']]}
            if cc_list:
                destination['CcAddresses'] = cc_list
            if bcc_list:
                destination['BccAddresses'] = bcc_list
            response = ses_client.send_email(
                Source=from_email,
                Destination=destination,
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': body_with_hidden_pixel}}
                }
            )
            logger.info(f"[Message {msg_idx}] ✅ SES Response: {json.dumps(response, default=str)}")
            return True
        
        # Build MIME message with attachments: use multipart/mixed with multipart/related for HTML+inline images
        logger.info(f"[Message {msg_idx}] Building MIME message with {len(attachments)} attachment(s) and {len(pre_inline_parts)} pre-inlined HTML image(s)")

        # Ensure body reflects any pre-inlining replacements
        body_with_hidden_pixel = body_with_hidden_pixel

        msg = MIMEMultipart('mixed')
        msg['From'] = from_email
        msg['To'] = contact['email']
        msg['Subject'] = subject

        # Add Cc header for recipients (BCC must not appear in headers)
        if cc_list:
            msg['Cc'] = ', '.join(cc_list)

        # multipart/related container for HTML body and inline images
        related = MIMEMultipart('related')

        # HTML part (attach first to related) - use an alternative container for future extensibility
        # IMPORTANT: use a binary/base64-encoded MIME part for HTML to avoid
        # quoted-printable soft-wrapping which can introduce visible newlines
        # in some mail clients (notably Outlook). We create a MIMEBase('text','html')
        # payload and base64-encode it explicitly.
        alternative = MIMEMultipart('alternative')
        try:
            html_part = MIMEBase('text', 'html')
            html_bytes = (body_with_hidden_pixel or '').encode('utf-8')
            html_part.set_payload(html_bytes)
            encoders.encode_base64(html_part)
            # Ensure the charset is visible in the Content-Type header
            html_part.add_header('Content-Type', 'text/html; charset="utf-8"')
            # Mark as inline (it's the main HTML body)
            html_part.add_header('Content-Disposition', 'inline')
        except Exception:
            # Fallback: if anything goes wrong, use MIMEText
            html_part = MIMEText(body_with_hidden_pixel, 'html', 'utf-8')

        alternative.attach(html_part)
        related.attach(alternative)

        # Attach any pre-inlined parts (downloaded data:, http(s), s3 images from HTML scanning)
        already_inlined_s3_keys = set()
        already_inlined_filenames = set()
        for part_meta, ppart in zip(pre_inline_cids, pre_inline_parts):
            try:
                related.attach(ppart)
            except Exception as p_attach_err:
                logger.warning(f"[Message {msg_idx}] Failed to attach pre-inlined part: {str(p_attach_err)}")
            s3_k = part_meta.get('s3_key')
            fname = part_meta.get('filename')
            if s3_k:
                already_inlined_s3_keys.add(s3_k)
            if fname:
                already_inlined_filenames.add(fname)

        inline_cids = []
        other_parts = []

        # Download and classify attachments from S3
        for a_idx, attachment in enumerate(attachments, 1):
            s3_key = attachment.get('s3_key')
            filename = attachment.get('filename')
            is_inline = attachment.get('inline', False)  # Check if this is an inline image

            if not s3_key or not filename:
                logger.warning(f"[Message {msg_idx}] Attachment {a_idx}: Missing s3_key or filename, skipping")
                continue

            # Skip attachments that were already inlined via HTML scanning
            if s3_key in already_inlined_s3_keys or filename in already_inlined_filenames:
                logger.info(f"[Message {msg_idx}] Skipping attachment {filename} because it was already inlined from HTML")
                continue

            try:
                logger.info(f"[Message {msg_idx}] Downloading attachment {a_idx}/{len(attachments)}: {filename} from S3 (inline={is_inline})")
                logger.debug(f"[Message {msg_idx}] S3 bucket: {ATTACHMENTS_BUCKET}, key: {s3_key}")

                s3_response = s3_client.get_object(Bucket=ATTACHMENTS_BUCKET, Key=s3_key)
                file_data = s3_response['Body'].read()
                logger.info(f"[Message {msg_idx}] Downloaded {len(file_data)} bytes for {filename}")

                content_type = attachment.get('type') or s3_response.get('ContentType') or 'application/octet-stream'
                maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

                # Treat images as inline if flagged or detected by content type
                if maintype.lower() == 'image' or is_inline:
                    cid = f"{filename.replace(' ', '_')}-{a_idx}-{int(time.time())}@inline"
                    try:
                        img_part = MIMEImage(file_data, _subtype=subtype)
                    except Exception:
                        img_part = MIMEImage(file_data)
                    img_part.add_header('Content-ID', f'<{cid}>')
                    img_part.add_header('Content-Disposition', 'inline', filename=filename)
                    related.attach(img_part)
                    inline_cids.append({'cid': cid, 'filename': filename, 's3_key': s3_key})
                    logger.info(f"[Message {msg_idx}] Attached image {filename} as inline CID <{cid}> (from S3)")
                else:
                    part = MIMEBase(maintype, subtype)
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    other_parts.append(part)
                    logger.info(f"[Message {msg_idx}] Prepared non-image attachment {filename}")

            except Exception as attachment_error:
                logger.error(f"[Message {msg_idx}] Error downloading/processing attachment {filename}: {str(attachment_error)}")
                # Continue with other attachments even if one fails

        # Attach related (HTML + inline images) to root, then any other attachments
        msg.attach(related)
        for p in other_parts:
            msg.attach(p)

        logger.info(f"[Message {msg_idx}] Calling SES send_raw_email API with {len(attachments)} attachment(s)")
        logger.info(f"[Message {msg_idx}] Sending to: {contact['email']}, From: {from_email}")

        # Build Destinations list for envelope recipients (To + Cc + Bcc)
        destinations = [contact['email']]
        if cc_list:
            destinations.extend(cc_list)
        if bcc_list:
            destinations.extend(bcc_list)

        # Attempt to rewrite HTML body references to S3 keys or filenames to cid: references
        try:
            new_body = body_with_hidden_pixel  # Use body with hidden pixel CSS
            replacements_made = 0
            
            print(f"🖼️ [Message {msg_idx}] Attempting to replace {len(inline_cids)} image reference(s) with CID in HTML body")
            logger.info(f"[Message {msg_idx}] Attempting to replace {len(inline_cids)} image reference(s) with CID in HTML body")
            
            # Debug: Show preview of HTML body before replacement
            if inline_cids:
                body_preview = new_body[:500] if len(new_body) > 500 else new_body
                logger.debug(f"[Message {msg_idx}] HTML body preview BEFORE CID replacement: {body_preview}...")
                
                # Find all img tags in body for debugging
                import re
                img_tags = re.findall(r'<img[^>]+>', new_body, re.IGNORECASE)
                if img_tags:
                    logger.info(f"[Message {msg_idx}] Found {len(img_tags)} <img> tag(s) in HTML body:")
                    for i, tag in enumerate(img_tags[:5]):  # Show first 5
                        logger.info(f"[Message {msg_idx}]   <img> {i+1}: {tag[:100]}...")
                else:
                    logger.warning(f"[Message {msg_idx}] No <img> tags found in HTML body!")
            
            for entry in inline_cids:
                cid = entry['cid']
                filename = entry['filename']
                s3_key = entry.get('s3_key','')
                
                print(f"🔍 [Message {msg_idx}] Looking for image to replace:")
                print(f"   filename: {filename}")
                print(f"   s3_key: {s3_key}")
                print(f"   cid: {cid}")
                logger.debug(f"[Message {msg_idx}] Looking for image: filename={filename}, s3_key={s3_key}")
                
                # Try multiple replacement patterns to catch different formats
                patterns_to_try = [
                    (f'https://{ATTACHMENTS_BUCKET}.s3.amazonaws.com/{s3_key}', f'cid:{cid}'),
                    (f'https://s3.amazonaws.com/{ATTACHMENTS_BUCKET}/{s3_key}', f'cid:{cid}'),
                    (f'src="{s3_key}"', f'src="cid:{cid}"'),  # src="campaign-attachments/file.png"
                    (f"src='{s3_key}'", f"src='cid:{cid}'"),  # src='campaign-attachments/file.png'
                    (s3_key, f'cid:{cid}'),                   # Bare S3 key
                    (filename, f'cid:{cid}')                   # Bare filename
                ]
                
                print(f"   Trying {len(patterns_to_try)} replacement patterns...")
                
                pattern_found = False
                for idx, (old_pattern, new_pattern) in enumerate(patterns_to_try):
                    if old_pattern in new_body:
                        print(f"   ✅ Pattern {idx + 1} MATCHED: '{old_pattern[:60]}...'")
                        new_body = new_body.replace(old_pattern, new_pattern)
                        replacements_made += 1
                        pattern_found = True
                        print(f"✅ [Message {msg_idx}] Replaced with '{new_pattern}'")
                        logger.info(f"[Message {msg_idx}] ✅ Replaced '{old_pattern[:50]}...' with '{new_pattern}' in HTML body")
                        break  # Stop after first match
                    else:
                        print(f"   ❌ Pattern {idx + 1} not found: '{old_pattern[:60]}...'")
                
                if not pattern_found:
                    print(f"⚠️ [Message {msg_idx}] WARNING: No pattern matched for {filename}!")
                    print(f"   This image will appear as attachment, not inline!")
                    # Show what's actually in the HTML for this image
                    import re
                    
                    # Search for any img tags
                    all_img_tags = re.findall(r'<img[^>]+>', new_body, re.IGNORECASE)
                    if all_img_tags:
                        print(f"   Found {len(all_img_tags)} img tag(s) in HTML body:")
                        for i, tag in enumerate(all_img_tags):
                            print(f"     Img {i+1}: {tag[:200]}...")
                    else:
                        print(f"   No <img> tags found in HTML body at all!")
                    
                    # Check if body still has data: URIs
                    if 'data:image' in new_body:
                        print(f"   ⚠️ HTML body still contains 'data:image' URIs - frontend replacement failed!")
                        data_uri_count = new_body.count('data:image')
                        print(f"   Found {data_uri_count} data:image URI(s) in body")
                    
                    # Show a larger sample of the body
                    print(f"   HTML body sample (first 1000 chars):")
                    print(f"   {new_body[:1000]}...")

            print(f"📊 [Message {msg_idx}] Total image reference replacements made: {replacements_made}")
            logger.info(f"[Message {msg_idx}] Total image reference replacements made: {replacements_made}")
            
            # Debug: Show preview of HTML body after replacement
            if inline_cids and replacements_made > 0:
                body_preview = new_body[:500] if len(new_body) > 500 else new_body
                logger.debug(f"[Message {msg_idx}] HTML body preview AFTER CID replacement: {body_preview}...")
                
                # Find img tags after replacement
                import re
                img_tags_after = re.findall(r'<img[^>]+>', new_body, re.IGNORECASE)
                if img_tags_after:
                    logger.info(f"[Message {msg_idx}] <img> tags AFTER replacement:")
                    for i, tag in enumerate(img_tags_after[:5]):
                        logger.info(f"[Message {msg_idx}]   <img> {i+1}: {tag[:100]}...")

            if new_body != body_with_hidden_pixel:
                # Replace the HTML part inside the alternative container explicitly
                try:
                    try:
                        new_html_part = MIMEBase('text', 'html')
                        new_html_bytes = (new_body or '').encode('utf-8')
                        new_html_part.set_payload(new_html_bytes)
                        encoders.encode_base64(new_html_part)
                        new_html_part.add_header('Content-Type', 'text/html; charset="utf-8"')
                        new_html_part.add_header('Content-Disposition', 'inline')
                    except Exception:
                        new_html_part = MIMEText(new_body, 'html', 'utf-8')

                    # alternative._payload[0] is the HTML part we originally attached
                    alternative._payload[0] = new_html_part
                    print(f"✅ [Message {msg_idx}] Successfully updated HTML body with CID references ({replacements_made} replacements)")
                    logger.info(f"[Message {msg_idx}] ✅ Successfully updated HTML body with CID references ({replacements_made} replacements)")
                except Exception as replace_error:
                    logger.warning(f"[Message {msg_idx}] Could not replace alternative payload directly: {str(replace_error)}")
            else:
                print(f"⚠️ [Message {msg_idx}] No replacements made - body unchanged. Images will appear as attachments!")
                logger.warning(f"[Message {msg_idx}] ⚠️ No replacements made - body unchanged. Images may appear as attachments instead of inline!")
        except Exception as rewrite_err:
            logger.error(f"[Message {msg_idx}] Failed to rewrite body image references to cid: {str(rewrite_err)}")
            import traceback
            traceback.print_exc()

        # Diagnostic: if this is the campaign the user reported, log a trimmed version of the raw MIME
        try:
            campaign_id = campaign.get('campaign_id') if isinstance(campaign, dict) else None
            if campaign_id == 'campaign_1759948233':
                raw_bytes = msg.as_bytes()
                try:
                    raw = raw_bytes.decode('utf-8')
                except Exception:
                    raw = raw_bytes.decode('utf-8', errors='replace')
                logger.info(f"[Message {msg_idx}] DEBUG RAW MIME (len={len(raw_bytes)}). Head preview:\n{raw[:12000]}")
        except Exception as dbg_err:
            logger.warning(f"[Message {msg_idx}] Failed to produce debug raw MIME: {str(dbg_err)}")

        # Use as_bytes() to produce the raw MIME bytes for SES to avoid newline/line-ending surprises
        raw_bytes = msg.as_bytes()
        response = ses_client.send_raw_email(
            Source=from_email,
            Destinations=destinations,
            RawMessage={'Data': raw_bytes}
        )
        
        # Log complete SES response
        logger.info(f"[Message {msg_idx}] ✅ SES Response: {json.dumps(response, default=str)}")
        message_id = response.get('MessageId', 'unknown')
        response_metadata = response.get('ResponseMetadata', {})
        http_status = response_metadata.get('HTTPStatusCode', 'unknown')
        request_id = response_metadata.get('RequestId', 'unknown')
        
        logger.info(f"[Message {msg_idx}] SES send_raw_email successful!")
        logger.info(f"[Message {msg_idx}]   Message ID: {message_id}")
        logger.info(f"[Message {msg_idx}]   HTTP Status: {http_status}")
        logger.info(f"[Message {msg_idx}]   Request ID: {request_id}")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        error_type = e.response.get('Error', {}).get('Type', 'Unknown')
        http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 'Unknown')
        request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'Unknown')
        
        logger.error(f"[Message {msg_idx}] ❌ AWS SES Error:")
        logger.error(f"[Message {msg_idx}]   Error Code: {error_code}")
        logger.error(f"[Message {msg_idx}]   Error Message: {error_message}")
        logger.error(f"[Message {msg_idx}]   Error Type: {error_type}")
        logger.error(f"[Message {msg_idx}]   HTTP Status: {http_status}")
        logger.error(f"[Message {msg_idx}]   Request ID: {request_id}")
        logger.error(f"[Message {msg_idx}]   Full Error Response: {json.dumps(e.response, default=str)}")
        
        # Log specific issues
        if error_code == 'MessageRejected':
            logger.error(f"[Message {msg_idx}] ⚠️  Message was rejected by SES. Check:")
            logger.error(f"[Message {msg_idx}]     - Is the from address verified in SES?")
            logger.error(f"[Message {msg_idx}]     - Is the to address verified (if in sandbox)?")
            logger.error(f"[Message {msg_idx}]     - From: {from_email}, To: {contact.get('email', 'unknown')}")
        elif error_code == 'ConfigurationSetDoesNotExist':
            logger.error(f"[Message {msg_idx}] ⚠️  Configuration set not found")
        elif rate_control.detect_throttle_exception(e):
            logger.warning(f"[Message {msg_idx}] ⚠️  SES throttling detected - rate limiting in effect")
        
        raise e
        
    except Exception as e:
        logger.error(f"[Message {msg_idx}] ❌ Unexpected SES Error: {str(e)}")
        logger.error(f"[Message {msg_idx}]   Exception Type: {type(e).__name__}")
        logger.exception(f"[Message {msg_idx}]   Full Exception:")
        raise e

def send_smtp_email(campaign, contact, from_email, subject, body, msg_idx=0, cc_list=None, bcc_list=None):
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

        # Prefer message-level lists if provided
        if cc_list is None:
            cc_list = campaign.get('cc') or []
        if bcc_list is None:
            bcc_list = campaign.get('bcc') or []
        if cc_list:
            msg['Cc'] = ', '.join(cc_list)

        msg.attach(MIMEText(body, 'html'))

        logger.debug(f"[Message {msg_idx}] SMTP message prepared")

        # Build envelope recipients (To + Cc + Bcc)
        envelope_recipients = [contact['email']]
        envelope_recipients.extend(cc_list)
        envelope_recipients.extend(bcc_list)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logger.info(f"[Message {msg_idx}] Sending via SMTP to envelope recipients: {len(envelope_recipients)}")
            server.send_message(msg, from_addr=from_email, to_addrs=envelope_recipients)
        
        logger.info(f"[Message {msg_idx}] SMTP send successful")
        return True
        
    except Exception as e:
        logger.error(f"[Message {msg_idx}] SMTP Error: {str(e)}")
        logger.exception(f"[Message {msg_idx}] SMTP Exception details:")
        
        # Log specific throttle information for debugging
        if rate_control.detect_throttle_exception(e):
            logger.warning(f"[Message {msg_idx}] This appears to be a throttle/rate limit exception")
        
        # Re-raise the exception so it can be handled by the caller
        raise e

def clean_quill_html_for_email(html_content):
    """
    Clean Quill editor HTML content for email sending.
    Removes Quill-specific CSS classes and graphics that appear as transparent icons.
    """
    import re
    
    if not html_content:
        return html_content
    
    # Remove Quill-specific CSS classes that add graphics
    quill_classes_to_remove = [
        r'class="[^"]*ql-[^"]*"',  # Remove all ql-* classes
        r'class="[^"]*ql-editor[^"]*"',  # Remove ql-editor class
        r'class="[^"]*ql-container[^"]*"',  # Remove ql-container class
        r'class="[^"]*ql-snow[^"]*"',  # Remove ql-snow class
        r'class="[^"]*ql-bubble[^"]*"',  # Remove ql-bubble class
    ]
    
    for pattern in quill_classes_to_remove:
        html_content = re.sub(pattern, '', html_content)
    
    # Remove Quill-specific attributes
    quill_attrs_to_remove = [
        r'data-[^=]*="[^"]*"',  # Remove data-* attributes
        r'spellcheck="[^"]*"',  # Remove spellcheck
        r'autocorrect="[^"]*"',  # Remove autocorrect
        r'autocapitalize="[^"]*"',  # Remove autocapitalize
    ]
    
    for pattern in quill_attrs_to_remove:
        html_content = re.sub(pattern, '', html_content)
    
    # Clean up empty class attributes
    html_content = re.sub(r'class=""', '', html_content)
    html_content = re.sub(r'class="\s*"', '', html_content)
    
    # Remove Quill-specific div wrappers but keep content
    html_content = re.sub(r'<div[^>]*class="[^"]*ql-editor[^"]*"[^>]*>', '', html_content)
    html_content = re.sub(r'</div>\s*$', '', html_content)  # Remove trailing div
    
    # Clean up multiple spaces
    # Collapse runs of whitespace to a single space (keeps HTML compact)
    html_content = re.sub(r'\s+', ' ', html_content)
    html_content = html_content.strip()

    # --- Additional normalization to reduce visible gaps/newlines in emails ---
    try:
        # Remove empty paragraph tags often emitted by editors like Quill (e.g. <p><br></p> or <p>&nbsp;</p>)
        html_content = re.sub(r'<p(?:\s+[^>]*)?>\s*(?:&nbsp;|<br\s*/?>|\s)*\s*</p>', '', html_content, flags=re.IGNORECASE)

        # Collapse multiple consecutive <br> into a single <br/>
        html_content = re.sub(r'(<br\s*/?>\s*){2,}', '<br/>', html_content, flags=re.IGNORECASE)

        # Collapse sequences of empty or near-empty paragraphs into a single paragraph
        # Example: </p> <p> </p> <p>Some text</p>  -> </p><p>Some text</p>
        html_content = re.sub(r'</p>\s*(?:<p(?:\s+[^>]*)?>\s*</p>\s*)+', '</p>', html_content, flags=re.IGNORECASE)

        # Trim leading/trailing whitespace inside paragraph tags: <p>  text  </p> -> <p>text</p>
        html_content = re.sub(r'<p([^>]*)>\s*(.*?)\s*</p>', lambda m: f"<p{m.group(1)}>{m.group(2).strip()}</p>", html_content, flags=re.IGNORECASE)
    except Exception as _norm_err:
        # If normalization fails for any reason, keep the cleaned content unchanged
        logger.debug(f"clean_quill_html_for_email: normalization step failed: {_norm_err}")
    
    # Preserve <img> tags here — we want to inline images later in the send path.
    # Earlier versions removed all <img> tags defensively, but that prevents
    # legitimate inline images (and inlining logic) from working. Any empty
    # wrappers (e.g., <p></p>) will be harmless; further cleanup can be done
    # downstream when assembling the MIME message.

    return html_content

def personalize_content(content, contact):
    """Replace placeholders with contact data - supports all CISA fields"""
    if not content:
        return content
    
    # Clean Quill HTML first to remove graphics
    content = clean_quill_html_for_email(content)
    
    # Basic contact info
    content = content.replace('{{first_name}}', contact.get('first_name', ''))
    content = content.replace('{{last_name}}', contact.get('last_name', ''))
    content = content.replace('{{email}}', contact.get('email', ''))
    content = content.replace('{{title}}', contact.get('title', ''))
    
    # Organization info
    content = content.replace('{{entity_type}}', contact.get('entity_type', ''))
    content = content.replace('{{state}}', contact.get('state', ''))
    content = content.replace('{{agency_name}}', contact.get('agency_name', ''))
    content = content.replace('{{sector}}', contact.get('sector', ''))
    content = content.replace('{{subsection}}', contact.get('subsection', ''))
    content = content.replace('{{phone}}', contact.get('phone', ''))
    
    # CISA-specific fields
    content = content.replace('{{ms_isac_member}}', contact.get('ms_isac_member', ''))
    content = content.replace('{{soc_call}}', contact.get('soc_call', ''))
    content = content.replace('{{fusion_center}}', contact.get('fusion_center', ''))
    content = content.replace('{{k12}}', contact.get('k12', ''))
    content = content.replace('{{water_wastewater}}', contact.get('water_wastewater', ''))
    content = content.replace('{{weekly_rollup}}', contact.get('weekly_rollup', ''))
    content = content.replace('{{alternate_email}}', contact.get('alternate_email', ''))
    content = content.replace('{{region}}', contact.get('region', ''))
    content = content.replace('{{group}}', contact.get('group', ''))
    
    # Legacy support
    content = content.replace('{{company}}', contact.get('agency_name', ''))
    
    return content