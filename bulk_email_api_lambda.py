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

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
contacts_table = dynamodb.Table('EmailContacts')
campaigns_table = dynamodb.Table('EmailCampaigns')
email_config_table = dynamodb.Table('EmailConfig')

def lambda_handler(event, context):
    """Bulk Email API with Web UI"""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        if event['httpMethod'] == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}
        
        path = event.get('resource', event.get('path', '/'))
        method = event['httpMethod']
        
        # Serve web UI for GET requests to root
        if method == 'GET' and path == '/':
            return serve_web_ui(event)
        
        # Parse request body
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        
        # API endpoints
        if path == '/config' and method == 'POST':
            return save_email_config(body, headers)
        elif path == '/config' and method == 'GET':
            return get_email_config(headers)
        elif path == '/contacts' and method == 'GET':
            return get_contacts(headers)
        elif path == '/contacts' and method == 'POST':
            return add_contact(body, headers)
        elif path == '/contacts' and method == 'PUT':
            return update_contact(body, headers)
        elif path == '/contacts' and method == 'DELETE':
            return delete_contact(event, headers)
        elif path == '/campaign' and method == 'POST':
            return send_campaign(body, headers)
        elif path == '/campaign/{campaign_id}' and method == 'GET':
            campaign_id = event['pathParameters']['campaign_id']
            return get_campaign_status(campaign_id, headers)
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}
            
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def serve_web_ui(event):
    """Serve web UI HTML"""
    api_id = event.get('requestContext', {}).get('apiId', 'UNKNOWN')
    api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Bulk Email Sender</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
        .tabs {{ display: flex; margin-bottom: 20px; }}
        .tab {{ padding: 10px 20px; background: #ddd; cursor: pointer; margin-right: 5px; }}
        .tab.active {{ background: #007cba; color: white; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .form-group {{ margin: 15px 0; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input, textarea, select {{ width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ddd; }}
        button {{ padding: 10px 20px; background: #007cba; color: white; border: none; cursor: pointer; margin: 5px; }}
        .btn-success {{ background: #28a745; }}
        .btn-danger {{ background: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
        .result {{ margin: 20px 0; padding: 15px; background: #f0f0f0; border-radius: 4px; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📧 Bulk Email Sender</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('config')">Email Config</div>
            <div class="tab" onclick="showTab('contacts')">Contacts</div>
            <div class="tab" onclick="showTab('campaign')">Send Campaign</div>
        </div>
        
        <div id="config" class="tab-content active">
            <h2>Email Configuration</h2>
            <div class="form-group">
                <label>Email Service:</label>
                <select id="emailService" onchange="toggleEmailService()">
                    <option value="ses">AWS SES</option>
                    <option value="smtp">SMTP</option>
                </select>
            </div>
            
            <div id="sesConfig">
                <div class="form-group">
                    <label>AWS Region:</label>
                    <input type="text" id="awsRegion" value="us-gov-west-1">
                </div>
                <div class="form-group">
                    <label>AWS Access Key:</label>
                    <input type="text" id="awsAccessKey">
                </div>
                <div class="form-group">
                    <label>AWS Secret Key:</label>
                    <input type="password" id="awsSecretKey">
                </div>
            </div>
            
            <div id="smtpConfig" class="hidden">
                <div class="form-group">
                    <label>SMTP Server:</label>
                    <input type="text" id="smtpServer" value="192.168.1.100">
                </div>
                <div class="form-group">
                    <label>SMTP Port:</label>
                    <input type="number" id="smtpPort" value="25">
                </div>
            </div>
            
            <div class="form-group">
                <label>From Email:</label>
                <input type="email" id="fromEmail">
            </div>
            <div class="form-group">
                <label>Emails per minute:</label>
                <input type="number" id="emailsPerMinute" value="60">
            </div>
            <button onclick="saveConfig()">Save Configuration</button>
        </div>
        
        <div id="contacts" class="tab-content">
            <h2>Contact Management</h2>
            <button onclick="loadContacts()">Load Contacts</button>
            <button class="btn-success" onclick="showAddContact()">Add Contact</button>
            <input type="file" id="csvFile" accept=".csv" style="display: none;" onchange="uploadCSV()">
            <button onclick="document.getElementById('csvFile').click()">Upload CSV</button>
            
            <div id="addContactForm" class="hidden">
                <h3>Add Contact</h3>
                <input type="email" id="newEmail" placeholder="Email">
                <input type="text" id="newFirstName" placeholder="First Name">
                <input type="text" id="newLastName" placeholder="Last Name">
                <input type="text" id="newCompany" placeholder="Company">
                <button onclick="addContact()">Add</button>
                <button onclick="hideAddContact()">Cancel</button>
            </div>
            
            <div class="result">
                <strong>CSV Format:</strong> email,first_name,last_name,company<br>
                <strong>Example:</strong> john@example.com,John,Doe,Tech Corp
            </div>
            
            <table id="contactsTable">
                <thead>
                    <tr><th>Email</th><th>First Name</th><th>Last Name</th><th>Company</th><th>Actions</th></tr>
                </thead>
                <tbody id="contactsBody"></tbody>
            </table>
        </div>
        
        <div id="campaign" class="tab-content">
            <h2>Send Campaign</h2>
            <div class="form-group">
                <label>Campaign Name:</label>
                <input type="text" id="campaignName">
            </div>
            <div class="form-group">
                <label>Subject:</label>
                <input type="text" id="subject" placeholder="Hello {{{{first_name}}}}">
            </div>
            <div class="form-group">
                <label>Email Body:</label>
                <textarea id="body" rows="8" placeholder="Dear {{{{first_name}}}} {{{{last_name}}}},\\n\\nYour message here..."></textarea>
            </div>
            <button class="btn-success" onclick="sendCampaign()">Send Campaign</button>
            
            <div id="campaignResult" class="result hidden"></div>
        </div>
    </div>
    
    <script>
        const API_URL = '{api_url}';
        
        function showTab(tabName) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }}
        
        function toggleEmailService() {{
            const service = document.getElementById('emailService').value;
            const sesConfig = document.getElementById('sesConfig');
            const smtpConfig = document.getElementById('smtpConfig');
            
            if (service === 'ses') {{
                sesConfig.classList.remove('hidden');
                smtpConfig.classList.add('hidden');
            }} else {{
                sesConfig.classList.add('hidden');
                smtpConfig.classList.remove('hidden');
            }}
        }}
        
        async function saveConfig() {{
            const service = document.getElementById('emailService').value;
            const config = {{
                email_service: service,
                from_email: document.getElementById('fromEmail').value,
                emails_per_minute: parseInt(document.getElementById('emailsPerMinute').value)
            }};
            
            if (service === 'ses') {{
                config.aws_region = document.getElementById('awsRegion').value;
                config.aws_access_key = document.getElementById('awsAccessKey').value;
                config.aws_secret_key = document.getElementById('awsSecretKey').value;
            }} else {{
                config.smtp_server = document.getElementById('smtpServer').value;
                config.smtp_port = parseInt(document.getElementById('smtpPort').value);
            }}
            
            const response = await fetch(`${{API_URL}}/config`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(config)
            }});
            
            const result = await response.json();
            alert(result.success ? 'Configuration saved!' : 'Error: ' + result.error);
        }}
        
        async function loadContacts() {{
            const response = await fetch(`${{API_URL}}/contacts`);
            const result = await response.json();
            
            const tbody = document.getElementById('contactsBody');
            tbody.innerHTML = '';
            
            result.contacts.forEach(contact => {{
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${{contact.email}}</td>
                    <td>${{contact.first_name || ''}}</td>
                    <td>${{contact.last_name || ''}}</td>
                    <td>${{contact.company || ''}}</td>
                    <td><button class="btn-danger" onclick="deleteContact('${{contact.email}}')">Delete</button></td>
                `;
            }});
        }}
        
        function showAddContact() {{
            document.getElementById('addContactForm').classList.remove('hidden');
        }}
        
        function hideAddContact() {{
            document.getElementById('addContactForm').classList.add('hidden');
        }}
        
        async function addContact() {{
            const contact = {{
                email: document.getElementById('newEmail').value,
                first_name: document.getElementById('newFirstName').value,
                last_name: document.getElementById('newLastName').value,
                company: document.getElementById('newCompany').value
            }};
            
            const response = await fetch(`${{API_URL}}/contacts`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(contact)
            }});
            
            const result = await response.json();
            if (result.success) {{
                hideAddContact();
                loadContacts();
            }}
        }}
        
        async function deleteContact(email) {{
            if (confirm('Delete contact?')) {{
                await fetch(`${{API_URL}}/contacts?email=${{encodeURIComponent(email)}}`, {{method: 'DELETE'}});
                loadContacts();
            }}
        }}
        
        async function uploadCSV() {{
            const file = document.getElementById('csvFile').files[0];
            if (!file) return;
            
            const text = await file.text();
            const lines = text.split('\\n').filter(line => line.trim());
            
            if (lines.length < 2) {{
                alert('CSV file must have at least a header row and one data row');
                return;
            }}
            
            const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
            let imported = 0;
            let errors = 0;
            
            for (let i = 1; i < lines.length; i++) {{
                const values = lines[i].split(',').map(v => v.trim());
                
                if (values.length !== headers.length) continue;
                
                const contact = {{}};
                headers.forEach((header, index) => {{
                    // Map common CSV headers to our fields
                    if (header === 'email' || header === 'email_address') {{
                        contact.email = values[index];
                    }} else if (header === 'first_name' || header === 'firstname' || header === 'first') {{
                        contact.first_name = values[index];
                    }} else if (header === 'last_name' || header === 'lastname' || header === 'last') {{
                        contact.last_name = values[index];
                    }} else if (header === 'company' || header === 'organization') {{
                        contact.company = values[index];
                    }}
                }});
                
                if (contact.email) {{
                    try {{
                        const response = await fetch(`${{API_URL}}/contacts`, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(contact)
                        }});
                        
                        if (response.ok) {{
                            imported++;
                        }} else {{
                            errors++;
                        }}
                    }} catch (e) {{
                        errors++;
                    }}
                }}
            }}
            
            alert(`CSV Upload Complete!\\nImported: ${{imported}} contacts\\nErrors: ${{errors}}`);
            loadContacts();
        }}
        
        async function sendCampaign() {{
            const campaign = {{
                campaign_name: document.getElementById('campaignName').value,
                subject: document.getElementById('subject').value,
                body: document.getElementById('body').value
            }};
            
            const response = await fetch(`${{API_URL}}/campaign`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(campaign)
            }});
            
            const result = await response.json();
            const resultDiv = document.getElementById('campaignResult');
            resultDiv.innerHTML = `<h3>Campaign Result</h3><pre>${{JSON.stringify(result, null, 2)}}</pre>`;
            resultDiv.classList.remove('hidden');
        }}
        
        window.onload = () => {{
            loadContacts();
        }};
    </script>
</body>
</html>"""
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': html_content
    }

def save_email_config(body, headers):
    """Save email configuration"""
    try:
        email_config_table.put_item(
            Item={
                'config_id': 'default',
                'email_service': body.get('email_service', 'ses'),
                'from_email': body.get('from_email', ''),
                'emails_per_minute': body.get('emails_per_minute', 60),
                'aws_region': body.get('aws_region', 'us-gov-west-1'),
                'aws_access_key': body.get('aws_access_key', ''),
                'aws_secret_key': body.get('aws_secret_key', ''),
                'smtp_server': body.get('smtp_server', ''),
                'smtp_port': body.get('smtp_port', 25),
                'updated_at': datetime.now().isoformat()
            }
        )
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def get_email_config(headers):
    """Get email configuration"""
    try:
        response = email_config_table.get_item(Key={'config_id': 'default'})
        if 'Item' in response:
            config = response['Item']
            # Don't return secret key
            if 'aws_secret_key' in config:
                config['aws_secret_key'] = '***'
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'config': config})}
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Config not found'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def get_contacts(headers):
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
    
    return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'contacts': contacts})}

def add_contact(body, headers):
    """Add new contact"""
    try:
        contacts_table.put_item(
            Item={
                'email': body['email'],
                'first_name': body.get('first_name', ''),
                'last_name': body.get('last_name', ''),
                'company': body.get('company', ''),
                'created_at': datetime.now().isoformat()
            }
        )
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def update_contact(body, headers):
    """Update contact"""
    try:
        email = body['email']
        update_expr = "SET "
        expr_values = {}
        
        for field in ['first_name', 'last_name', 'company']:
            if field in body:
                update_expr += f"{field} = :{field[0]}, "
                expr_values[f":{field[0]}"] = body[field]
        
        update_expr = update_expr.rstrip(', ')
        
        contacts_table.update_item(
            Key={'email': email},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def delete_contact(event, headers):
    """Delete contact"""
    try:
        email = event['queryStringParameters']['email']
        contacts_table.delete_item(Key={'email': email})
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def send_campaign(body, headers):
    """Send email campaign"""
    try:
        # Get email configuration
        config_response = email_config_table.get_item(Key={'config_id': 'default'})
        if 'Item' not in config_response:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Email configuration not found'})}
        
        config = config_response['Item']
        
        # Get contacts
        contacts_response = contacts_table.scan()
        contacts = contacts_response['Items']
        
        campaign_id = f"campaign_{int(datetime.now().timestamp())}"
        
        # Initialize campaign
        campaigns_table.put_item(
            Item={
                'campaign_id': campaign_id,
                'campaign_name': body.get('campaign_name', 'Bulk Campaign'),
                'status': 'in_progress',
                'total_contacts': len(contacts),
                'sent_count': 0,
                'failed_count': 0,
                'created_at': datetime.now().isoformat()
            }
        )
        
        sent_count = 0
        failed_count = 0
        
        # Send emails
        for contact in contacts:
            try:
                if config['email_service'] == 'ses':
                    success = send_ses_email(config, contact, body['subject'], body['body'])
                else:
                    success = send_smtp_email(config, contact, body['subject'], body['body'])
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                
                # Rate limiting
                time.sleep(60 / config.get('emails_per_minute', 60))
                
            except Exception as e:
                failed_count += 1
        
        # Update campaign
        campaigns_table.update_item(
            Key={'campaign_id': campaign_id},
            UpdateExpression="SET #status = :status, sent_count = :sent, failed_count = :failed",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'completed',
                ':sent': sent_count,
                ':failed': failed_count
            }
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'campaign_id': campaign_id,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_contacts': len(contacts)
            })
        }
        
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def send_ses_email(config, contact, subject, body):
    """Send email via AWS SES"""
    try:
        ses_client = boto3.client(
            'ses',
            region_name=config.get('aws_region', 'us-gov-west-1'),
            aws_access_key_id=config.get('aws_access_key'),
            aws_secret_access_key=config.get('aws_secret_key')
        )
        
        personalized_subject = personalize_content(subject, contact)
        personalized_body = personalize_content(body, contact)
        
        ses_client.send_email(
            Source=config['from_email'],
            Destination={'ToAddresses': [contact['email']]},
            Message={
                'Subject': {'Data': personalized_subject},
                'Body': {'Html': {'Data': personalized_body}}
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
        msg['Subject'] = personalize_content(subject, contact)
        
        msg.attach(MIMEText(personalize_content(body, contact), 'html'))
        
        with smtplib.SMTP(config['smtp_server'], int(config['smtp_port'])) as server:
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        return False

def get_campaign_status(campaign_id, headers):
    """Get campaign status"""
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

def personalize_content(content, contact):
    """Replace placeholders with contact data"""
    content = content.replace('{{first_name}}', contact.get('first_name', ''))
    content = content.replace('{{last_name}}', contact.get('last_name', ''))
    content = content.replace('{{email}}', contact.get('email', ''))
    content = content.replace('{{company}}', contact.get('company', ''))
    return content