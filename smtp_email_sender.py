import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import json
from datetime import datetime

class SMTPEmailSender:
    def __init__(self, smtp_config):
        self.smtp_server = smtp_config['server']
        self.smtp_port = smtp_config['port']
        self.username = smtp_config['username']
        self.password = smtp_config['password']
        self.use_tls = smtp_config.get('use_tls', True)
        
    def send_email(self, from_email, to_email, subject, body, attachments=None):
        """Send single email with optional attachments"""
        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(file_path)}'
                        )
                        msg.attach(part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def send_bulk_campaign(self, from_email, contacts, subject, body, attachments=None):
        """Send bulk email campaign"""
        results = []
        
        for contact in contacts:
            # Personalize content
            personalized_subject = self.personalize_content(subject, contact)
            personalized_body = self.personalize_content(body, contact)
            
            success, error = self.send_email(
                from_email, 
                contact['email'], 
                personalized_subject, 
                personalized_body, 
                attachments
            )
            
            results.append({
                'email': contact['email'],
                'status': 'sent' if success else 'failed',
                'error': error
            })
        
        return results
    
    def personalize_content(self, content, contact):
        """Replace placeholders with contact data"""
        content = content.replace('{{first_name}}', contact.get('first_name', ''))
        content = content.replace('{{last_name}}', contact.get('last_name', ''))
        content = content.replace('{{email}}', contact.get('email', ''))
        content = content.replace('{{company}}', contact.get('company', ''))
        return content

def lambda_handler(event, context):
    """Lambda handler for SMTP email sending"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    try:
        if event['httpMethod'] == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}
        
        body = json.loads(event['body'])
        
        # SMTP Configuration
        smtp_config = {
            'server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.environ.get('SMTP_PORT', '587')),
            'username': os.environ.get('SMTP_USERNAME'),
            'password': os.environ.get('SMTP_PASSWORD'),
            'use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
        }
        
        sender = SMTPEmailSender(smtp_config)
        
        # Get contacts (simplified - in real implementation, get from DynamoDB)
        contacts = body.get('contacts', [])
        
        # Send campaign
        results = sender.send_bulk_campaign(
            from_email=body['from_email'],
            contacts=contacts,
            subject=body['subject'],
            body=body['body'],
            attachments=body.get('attachments', [])
        )
        
        sent_count = sum(1 for r in results if r['status'] == 'sent')
        failed_count = len(results) - sent_count
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_contacts': len(contacts),
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }