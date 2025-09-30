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
secrets_client = boto3.client('secretsmanager', region_name='us-gov-west-1')
sqs_client = boto3.client('sqs', region_name='us-gov-west-1')

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
    <title>CISA Email Campaign Management System</title>
    
    
    <style>
        /* Modern CSS Variables for Consistent Theming */
        :root {{
            --primary-color: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #a5b4fc;
            --secondary-color: #f59e0b;
            --success-color: #10b981;
            --danger-color: #ef4444;
            --warning-color: #f59e0b;
            --info-color: #3b82f6;
            --dark-color: #1f2937;
            --light-color: #f8fafc;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-400: #9ca3af;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --gray-900: #111827;
            --border-radius: 12px;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }}
        
        /* Reset and Base Styles */
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            min-height: 100vh;
            color: var(--gray-800);
            line-height: 1.6;
        }}
        
        /* Container and Layout */
        .container {{ 
            max-width: 1200px; 
            margin: 20px auto; 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: var(--shadow-xl);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        /* Header Styling */
        .header {{ 
            text-align: center; 
            margin-bottom: 40px; 
            padding-bottom: 30px;
            border-bottom: 2px solid var(--gray-100);
        }}
        .header h1 {{ 
            color: var(--gray-900); 
            margin: 0; 
            font-size: 2.8rem; 
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .header .subtitle {{ 
            color: var(--gray-600); 
            font-size: 1.2rem; 
            margin-top: 15px; 
            font-weight: 500;
        }}
        
        /* Modern Tab System */
        .tabs {{ 
            display: flex; 
            margin-bottom: 40px; 
            background: var(--gray-50); 
            border-radius: var(--border-radius); 
            padding: 8px; 
            gap: 4px;
            position: relative;
            z-index: 5;
        }}
        .tab {{ 
            flex: 1; 
            padding: 16px 24px; 
            background: transparent; 
            cursor: pointer; 
            text-align: center; 
            border-radius: 8px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            font-weight: 600; 
            color: var(--gray-600);
            position: relative;
            overflow: hidden;
            z-index: 10;
            pointer-events: auto;
            user-select: none;
        }}
        .tab:hover {{ 
            background: rgba(99, 102, 241, 0.1); 
            color: var(--primary-color);
            transform: translateY(-1px);
        }}
        .tab.active {{ 
            background: linear-gradient(135deg, var(--primary-color), var(--primary-dark)); 
            color: white; 
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
        }}
        .tab.active::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1));
            border-radius: 8px;
        }}
        
        /* Tab Content */
        .tab-content {{ 
            display: none; 
            animation: fadeIn 0.3s ease-in-out;
        }}
        .tab-content.active {{ 
            display: block; 
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Form Styling */
        .form-group {{ 
            margin: 24px 0; 
        }}
        label {{ 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: var(--gray-700);
            font-size: 0.95rem;
        }}
        input, textarea, select {{ 
            width: 100%; 
            padding: 14px 16px; 
            margin-bottom: 16px; 
            border: 2px solid var(--gray-200); 
            border-radius: var(--border-radius); 
            font-size: 15px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: white;
            color: var(--gray-800);
        }}
        input:focus, textarea:focus, select:focus {{ 
            outline: none; 
            border-color: var(--primary-color); 
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            transform: translateY(-1px);
        }}
        input:hover, textarea:hover, select:hover {{
            border-color: var(--gray-300);
        }}
        small {{
            color: var(--gray-500);
            font-size: 0.875rem;
            margin-top: 4px;
            display: block;
        }}
        
        /* Modern Button System */
        button {{ 
            padding: 14px 28px; 
            background: linear-gradient(135deg, var(--primary-color), var(--primary-dark)); 
            color: white; 
            border: none; 
            border-radius: var(--border-radius); 
            cursor: pointer; 
            margin: 8px 6px; 
            font-weight: 600; 
            font-size: 15px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-md);
        }}
        button::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }}
        button:hover::before {{
            left: 100%;
        }}
        button:hover {{ 
            transform: translateY(-2px); 
            box-shadow: var(--shadow-xl);
        }}
        button:active {{
            transform: translateY(0);
        }}
        
        .btn-success {{ 
            background: linear-gradient(135deg, var(--success-color), #059669); 
        }}
        .btn-success:hover {{ 
            box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4); 
        }}
        .btn-danger {{ 
            background: linear-gradient(135deg, var(--danger-color), #dc2626); 
        }}
        .btn-danger:hover {{ 
            box-shadow: 0 10px 25px rgba(239, 68, 68, 0.4); 
        }}
        .btn-primary {{ 
            background: linear-gradient(135deg, var(--primary-color), #1d4ed8); 
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: var(--border-radius);
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            margin: 2px;
        }}
        .btn-primary:hover {{ 
            box-shadow: 0 10px 25px rgba(59, 130, 246, 0.4); 
        }}
        
        /* Table Styling */
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 30px 0; 
            border-radius: var(--border-radius); 
            overflow: hidden; 
            box-shadow: var(--shadow-lg);
            background: white;
        }}
        th, td {{ 
            padding: 16px 20px; 
            text-align: left; 
        }}
        th {{ 
            background: linear-gradient(135deg, var(--gray-800), var(--gray-900)); 
            color: white; 
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{ 
            border-bottom: 1px solid var(--gray-100); 
            color: var(--gray-700);
        }}
        tr:hover {{ 
            background: var(--gray-50); 
            transform: scale(1.01);
            transition: all 0.2s ease;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        
        /* Result and Card Styling */
        .result {{ 
            margin: 30px 0; 
            padding: 24px; 
            background: linear-gradient(135deg, var(--gray-50), white); 
            border-radius: var(--border-radius); 
            border-left: 4px solid var(--primary-color);
            box-shadow: var(--shadow-md);
        }}
        .result h3 {{
            margin-top: 0;
            color: var(--gray-800);
            font-weight: 600;
        }}
        .result pre {{
            background: var(--gray-100);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            color: var(--gray-700);
        }}
        .hidden {{
            display: none;
        }}
        
        .contact-count {{
            margin-left: 10px;
            padding: 5px 10px;
            background: var(--primary-color);
            color: white;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        
        /* Quill Editor Styling */
        .ql-editor {{
            min-height: 200px;
            font-size: 16px;
            line-height: 1.6;
        }}
        .ql-toolbar {{
            border-top: 1px solid #e5e7eb;
            border-left: 1px solid #e5e7eb;
            border-right: 1px solid #e5e7eb;
            border-radius: 8px 8px 0 0;
            background: #f9fafb;
        }}
        .ql-container {{
            border-bottom: 1px solid #e5e7eb;
            border-left: 1px solid #e5e7eb;
            border-right: 1px solid #e5e7eb;
            border-radius: 0 0 8px 8px;
            background: white;
        }}
        .ql-editor.ql-blank::before {{
            color: #9ca3af;
            font-style: normal;
        }}
        .card {{ 
            background: white; 
            border-radius: var(--border-radius); 
            padding: 30px; 
            margin: 24px 0; 
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--gray-100);
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                padding: 20px;
                border-radius: 16px;
            }}
            .header h1 {{
                font-size: 2.2rem;
            }}
            .tabs {{
                flex-direction: column;
                gap: 8px;
            }}
            .tab {{
                padding: 12px 16px;
            }}
            button {{
                width: 100%;
                margin: 8px 0;
            }}
        }}
        
        /* Loading and Animation States */
        .loading {{
            opacity: 0.7;
            pointer-events: none;
        }}
        .loading::after {{
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            margin: -10px 0 0 -10px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CISA Email Campaign Management System</h1>
            <div class="subtitle">Cybersecurity and Infrastructure Security Agency</div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('config', this)">Email Config</div>
            <div class="tab" onclick="showTab('contacts', this)">Contacts</div>
            <div class="tab" onclick="showTab('campaign', this)">Send Campaign</div>
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
                    <label>AWS Secrets Manager Secret Name (Optional):</label>
                    <input type="text" id="awsSecretName" placeholder="email-api-credentials">
                    <small style="color: #666; font-size: 0.9em;">Leave empty to use Lambda's IAM role (recommended). Only provide if using specific credentials.</small>
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
            <div class="form-group">
                <label>Filter by Group:</label>
                <select id="groupFilter" onchange="filterContactsByGroup()">
                    <option value="">All Groups</option>
                </select>
                <button onclick="loadAllContacts()">Load All Contacts</button>
            </div>
            <button onclick="loadContacts()">Load Contacts</button>
            <button class="btn-success" onclick="showAddContact()">Add Contact</button>
            <input type="file" id="csvFile" accept=".csv" style="display: none;" onchange="uploadCSV()">
            <button onclick="document.getElementById('csvFile').click()">Upload CSV</button>
            
            <div id="addContactForm" class="hidden card">
                <h3>Add Contact</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <input type="email" id="newEmail" placeholder="Email Address *" required>
                    <input type="text" id="newFirstName" placeholder="First Name *" required>
                    <input type="text" id="newLastName" placeholder="Last Name *" required>
                    <input type="text" id="newTitle" placeholder="Title">
                    <input type="text" id="newEntityType" placeholder="Entity Type">
                    <input type="text" id="newState" placeholder="State">
                    <input type="text" id="newAgencyName" placeholder="Agency Name">
                    <input type="text" id="newSector" placeholder="Sector">
                    <input type="text" id="newSubsection" placeholder="Subsection">
                    <input type="text" id="newPhone" placeholder="Phone">
                    <select id="newMsIsacMember">
                        <option value="">MS-ISAC Member</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="newSocCall">
                        <option value="">SOC Call</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="newFusionCenter">
                        <option value="">Fusion Center</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="newK12">
                        <option value="">K-12</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="newWaterWastewater">
                        <option value="">Water/Wastewater</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="newWeeklyRollup">
                        <option value="">Weekly Rollup</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <input type="email" id="newAlternateEmail" placeholder="Alternate Email">
                    <input type="text" id="newRegion" placeholder="Region">
                    <input type="text" id="newGroup" placeholder="Group">
                </div>
                <div style="margin-top: 20px;">
                    <button class="btn-success" onclick="addContact()">Add</button>
                <button onclick="hideAddContact()">Cancel</button>
                </div>
            </div>
            
            <div id="editContactForm" class="hidden card">
                <h3>Edit Contact</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <input type="email" id="editEmail" placeholder="Email Address *" required readonly>
                    <input type="text" id="editFirstName" placeholder="First Name *" required>
                    <input type="text" id="editLastName" placeholder="Last Name *" required>
                    <input type="text" id="editTitle" placeholder="Title">
                    <input type="text" id="editEntityType" placeholder="Entity Type">
                    <input type="text" id="editState" placeholder="State">
                    <input type="text" id="editAgencyName" placeholder="Agency Name">
                    <input type="text" id="editSector" placeholder="Sector">
                    <input type="text" id="editSubsection" placeholder="Subsection">
                    <input type="text" id="editPhone" placeholder="Phone">
                    <select id="editMsIsacMember">
                        <option value="">MS-ISAC Member</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="editSocCall">
                        <option value="">SOC Call</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="editFusionCenter">
                        <option value="">Fusion Center</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="editK12">
                        <option value="">K-12</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="editWaterWastewater">
                        <option value="">Water/Wastewater</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <select id="editWeeklyRollup">
                        <option value="">Weekly Rollup</option>
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                    </select>
                    <input type="email" id="editAlternateEmail" placeholder="Alternate Email">
                    <input type="text" id="editRegion" placeholder="Region">
                    <input type="text" id="editGroup" placeholder="Group">
                </div>
                <div style="margin-top: 20px;">
                    <button class="btn-success" onclick="saveContactEdit()">Save Changes</button>
                    <button onclick="hideEditContact()">Cancel</button>
                </div>
            </div>
            
            <div class="result">
                <strong>CSV Format:</strong> email,first_name,last_name,title,entity_type,state,agency_name,sector,subsection,phone,ms_isac_member,soc_call,fusion_center,k12,water_wastewater,weekly_rollup,alternate_email,region,group<br>
                <strong>Example:</strong> john@example.com,John,Doe,IT Director,State Government,CA,Dept of Tech,Government,IT,555-0100,Yes,Yes,No,No,No,Yes,john.alt@example.com,West,State CISOs
            </div>
            
            <div style="overflow-x: auto;">
            <table id="contactsTable">
                <thead>
                        <tr>
                            <th>Email</th>
                            <th>Name</th>
                            <th>Title</th>
                            <th>Entity Type</th>
                            <th>State</th>
                            <th>Agency</th>
                            <th>Actions</th>
                        </tr>
                </thead>
                <tbody id="contactsBody"></tbody>
            </table>
            </div>
        </div>
        
        <div id="campaign" class="tab-content">
            <h2>Send Campaign</h2>
            <div class="form-group">
                <label>Target Group:</label>
                <select id="targetGroup" onchange="loadContactsForCampaign()">
                    <option value="">All Groups</option>
                </select>
                <span id="contactCount" class="contact-count"></span>
            </div>
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
                <textarea id="body" rows="8" placeholder="Dear {{first_name}} {{last_name}},\\n\\nYour message here..." style="width: 100%; min-height: 200px; padding: 10px; border: 1px solid #ccc; border-radius: 4px;"></textarea>
                <small>Available placeholders: {{{{first_name}}}}, {{{{last_name}}}}, {{{{email}}}}, {{{{title}}}}, {{{{entity_type}}}}, {{{{state}}}}, {{{{agency_name}}}}, {{{{sector}}}}, {{{{subsection}}}}, {{{{phone}}}}, {{{{ms_isac_member}}}}, {{{{soc_call}}}}, {{{{fusion_center}}}}, {{{{k12}}}}, {{{{water_wastewater}}}}, {{{{weekly_rollup}}}}, {{{{alternate_email}}}}, {{{{region}}}}, {{{{group}}}}</small>
            </div>
            <div style="display: flex; gap: 15px; margin-top: 20px;">
            <button class="btn-success" onclick="sendCampaign()">Send Campaign</button>
                <button onclick="clearCampaignForm()">Clear Form</button>
            </div>
            
            <div id="campaignResult" class="result hidden"></div>
        </div>
    </div>
    
    <script>
        const API_URL = '{api_url}';
        
        // Initialize the application
        
        function showTab(tabName, clickedElement) {{
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            
            // Remove active class from all tab contents  
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab
            clickedElement.classList.add('active');
            
            // Add active class to target tab content
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
            const button = event.target;
            const originalText = button.textContent;
            
            try {{
                // Show loading state
                button.textContent = 'Saving...';
                button.classList.add('loading');
                button.disabled = true;
                
            const service = document.getElementById('emailService').value;
            const config = {{
                email_service: service,
                from_email: document.getElementById('fromEmail').value,
                emails_per_minute: parseInt(document.getElementById('emailsPerMinute').value)
            }};
            
            if (service === 'ses') {{
                config.aws_region = document.getElementById('awsRegion').value;
                    config.aws_secret_name = document.getElementById('awsSecretName').value;
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
                
                if (result.success) {{
                    button.textContent = 'Saved!';
                    button.style.background = 'linear-gradient(135deg, var(--success-color), #059669)';
                    setTimeout(() => {{
                        button.textContent = originalText;
                        button.style.background = '';
                    }}, 2000);
                }} else {{
                    throw new Error(result.error);
                }}
                
            }} catch (error) {{
                button.textContent = 'Error';
                button.style.background = 'linear-gradient(135deg, var(--danger-color), #dc2626)';
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.background = '';
                }}, 2000);
                alert('Error: ' + error.message);
            }} finally {{
                button.classList.remove('loading');
                button.disabled = false;
            }}
        }}
        
        let allContacts = [];
        
        
        function clearCampaignForm() {{
            document.getElementById('campaignName').value = '';
            document.getElementById('subject').value = '';
            document.getElementById('body').value = '';
            document.getElementById('targetGroup').value = '';
            document.getElementById('contactCount').textContent = '0';
        }};
        
        async function loadContacts() {{
            const button = event?.target || document.querySelector('button[onclick="loadContacts()"]');
            const originalText = button?.textContent || 'Load Contacts';
            
            try {{
                if (button) {{
                    button.textContent = 'Loading...';
                    button.disabled = true;
                }}
                
            const response = await fetch(`${{API_URL}}/contacts`);
            const result = await response.json();
            
                allContacts = result.contacts || [];
                populateGroupFilters();
                filterContactsByGroup();
                
                if (button) {{
                    button.textContent = 'Loaded';
                    setTimeout(() => {{
                        button.textContent = originalText;
                    }}, 1500);
                }}
                
            }} catch (error) {{
                const tbody = document.getElementById('contactsBody');
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--danger-color); padding: 40px;">Error loading contacts: ' + error.message + '</td></tr>';
                
                if (button) {{
                    button.textContent = 'Error';
                    setTimeout(() => {{
                        button.textContent = originalText;
                    }}, 2000);
                }}
            }} finally {{
                if (button) {{
                    button.disabled = false;
                }}
            }}
        }}
        
        async function loadAllContacts() {{
            await loadContacts();
            document.getElementById('groupFilter').value = '';
            filterContactsByGroup();
        }}
        
        function populateGroupFilters() {{
            const groups = [...new Set(allContacts.map(c => c.group).filter(g => g))].sort();
            const groupFilter = document.getElementById('groupFilter');
            const targetGroup = document.getElementById('targetGroup');
            
            // Clear existing options except "All Groups"
            groupFilter.innerHTML = '<option value="">All Groups</option>';
            targetGroup.innerHTML = '<option value="">All Groups</option>';
            
            groups.forEach(group => {{
                const option1 = new Option(group, group);
                const option2 = new Option(group, group);
                groupFilter.add(option1);
                targetGroup.add(option2);
            }});
        }}
        
        function filterContactsByGroup() {{
            const selectedGroup = document.getElementById('groupFilter').value;
            let filteredContacts = allContacts;
            
            if (selectedGroup) {{
                filteredContacts = allContacts.filter(contact => contact.group === selectedGroup);
            }}
            
            displayContacts(filteredContacts);
        }}
        
        function displayContacts(contacts) {{
            const tbody = document.getElementById('contactsBody');
            tbody.innerHTML = '';
            
            if (contacts && contacts.length > 0) {{
                contacts.forEach(contact => {{
                const row = tbody.insertRow();
                    const fullName = `${{contact.first_name || ''}} ${{contact.last_name || ''}}`.trim();
                row.innerHTML = `
                    <td>${{contact.email}}</td>
                        <td>${{fullName}}</td>
                        <td>${{contact.title || ''}}</td>
                        <td>${{contact.entity_type || ''}}</td>
                        <td>${{contact.state || ''}}</td>
                        <td>${{contact.agency_name || ''}}</td>
                        <td>
                            <button class="btn-danger" onclick="deleteContact('${{contact.email}}')">Delete</button>
                            <button onclick="viewContact('${{contact.email}}')">View</button>
                            <button class="btn-primary" onclick="editContact('${{contact.email}}')">Edit</button>
                        </td>
                `;
            }});
            }} else {{
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--gray-500); padding: 40px;">No contacts found. Add some contacts to get started!</td></tr>';
            }}
        }}
        
        function showAddContact() {{
            document.getElementById('addContactForm').classList.remove('hidden');
        }}
        
        function hideAddContact() {{
            document.getElementById('addContactForm').classList.add('hidden');
        }}
        
        function editContact(email) {{
            const contact = allContacts.find(c => c.email === email);
            if (!contact) {{
                alert('Contact not found');
                return;
            }}
            
            // Populate edit form with contact data
            document.getElementById('editEmail').value = contact.email || '';
            document.getElementById('editFirstName').value = contact.first_name || '';
            document.getElementById('editLastName').value = contact.last_name || '';
            document.getElementById('editTitle').value = contact.title || '';
            document.getElementById('editEntityType').value = contact.entity_type || '';
            document.getElementById('editState').value = contact.state || '';
            document.getElementById('editAgencyName').value = contact.agency_name || '';
            document.getElementById('editSector').value = contact.sector || '';
            document.getElementById('editSubsection').value = contact.subsection || '';
            document.getElementById('editPhone').value = contact.phone || '';
            document.getElementById('editMsIsacMember').value = contact.ms_isac_member || '';
            document.getElementById('editSocCall').value = contact.soc_call || '';
            document.getElementById('editFusionCenter').value = contact.fusion_center || '';
            document.getElementById('editK12').value = contact.k12 || '';
            document.getElementById('editWaterWastewater').value = contact.water_wastewater || '';
            document.getElementById('editWeeklyRollup').value = contact.weekly_rollup || '';
            document.getElementById('editAlternateEmail').value = contact.alternate_email || '';
            document.getElementById('editRegion').value = contact.region || '';
            document.getElementById('editGroup').value = contact.group || '';
            
            // Show edit form
            document.getElementById('editContactForm').classList.remove('hidden');
        }}
        
        function hideEditContact() {{
            document.getElementById('editContactForm').classList.add('hidden');
        }}
        
        async function saveContactEdit() {{
            const email = document.getElementById('editEmail').value;
            const contactData = {{
                email: email,
                first_name: document.getElementById('editFirstName').value,
                last_name: document.getElementById('editLastName').value,
                title: document.getElementById('editTitle').value,
                entity_type: document.getElementById('editEntityType').value,
                state: document.getElementById('editState').value,
                agency_name: document.getElementById('editAgencyName').value,
                sector: document.getElementById('editSector').value,
                subsection: document.getElementById('editSubsection').value,
                phone: document.getElementById('editPhone').value,
                ms_isac_member: document.getElementById('editMsIsacMember').value,
                soc_call: document.getElementById('editSocCall').value,
                fusion_center: document.getElementById('editFusionCenter').value,
                k12: document.getElementById('editK12').value,
                water_wastewater: document.getElementById('editWaterWastewater').value,
                weekly_rollup: document.getElementById('editWeeklyRollup').value,
                alternate_email: document.getElementById('editAlternateEmail').value,
                region: document.getElementById('editRegion').value,
                group: document.getElementById('editGroup').value
            }};
            
            try {{
                const response = await fetch(`${{API_URL}}/contacts`, {{
                    method: 'PUT',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(contactData)
                }});
                
                const result = await response.json();
                if (result.success) {{
                    hideEditContact();
                    loadContacts(); // Refresh the contacts list
                    alert('Contact updated successfully!');
                }} else {{
                    alert('Error updating contact: ' + (result.error || 'Unknown error'));
                }}
            }} catch (error) {{
                console.error('Error updating contact:', error);
                alert('Error updating contact: ' + error.message);
            }}
        }}
        
        async function addContact() {{
            const contact = {{
                email: document.getElementById('newEmail').value,
                first_name: document.getElementById('newFirstName').value,
                last_name: document.getElementById('newLastName').value,
                title: document.getElementById('newTitle').value,
                entity_type: document.getElementById('newEntityType').value,
                state: document.getElementById('newState').value,
                agency_name: document.getElementById('newAgencyName').value,
                sector: document.getElementById('newSector').value,
                subsection: document.getElementById('newSubsection').value,
                phone: document.getElementById('newPhone').value,
                ms_isac_member: document.getElementById('newMsIsacMember').value,
                soc_call: document.getElementById('newSocCall').value,
                fusion_center: document.getElementById('newFusionCenter').value,
                k12: document.getElementById('newK12').value,
                water_wastewater: document.getElementById('newWaterWastewater').value,
                weekly_rollup: document.getElementById('newWeeklyRollup').value,
                alternate_email: document.getElementById('newAlternateEmail').value,
                region: document.getElementById('newRegion').value,
                group: document.getElementById('newGroup').value
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
                // Clear form
                document.getElementById('newEmail').value = '';
                document.getElementById('newFirstName').value = '';
                document.getElementById('newLastName').value = '';
                document.getElementById('newTitle').value = '';
                document.getElementById('newEntityType').value = '';
                document.getElementById('newState').value = '';
                document.getElementById('newAgencyName').value = '';
                document.getElementById('newSector').value = '';
                document.getElementById('newSubsection').value = '';
                document.getElementById('newPhone').value = '';
                document.getElementById('newMsIsacMember').value = '';
                document.getElementById('newSocCall').value = '';
                document.getElementById('newFusionCenter').value = '';
                document.getElementById('newK12').value = '';
                document.getElementById('newWaterWastewater').value = '';
                document.getElementById('newWeeklyRollup').value = '';
                document.getElementById('newAlternateEmail').value = '';
                document.getElementById('newRegion').value = '';
                document.getElementById('newGroup').value = '';
            }}
        }}
        
        async function viewContact(email) {{
            const response = await fetch(`${{API_URL}}/contacts`);
            const result = await response.json();
            const contact = result.contacts.find(c => c.email === email);
            
            if (contact) {{
                alert(`Contact Details:\\n\\n` +
                    `Email: ${{contact.email}}\\n` +
                    `Name: ${{contact.first_name}} ${{contact.last_name}}\\n` +
                    `Title: ${{contact.title || 'N/A'}}\\n` +
                    `Entity Type: ${{contact.entity_type || 'N/A'}}\\n` +
                    `State: ${{contact.state || 'N/A'}}\\n` +
                    `Agency: ${{contact.agency_name || 'N/A'}}\\n` +
                    `Sector: ${{contact.sector || 'N/A'}}\\n` +
                    `Subsection: ${{contact.subsection || 'N/A'}}\\n` +
                    `Phone: ${{contact.phone || 'N/A'}}\\n` +
                    `MS-ISAC Member: ${{contact.ms_isac_member || 'N/A'}}\\n` +
                    `SOC Call: ${{contact.soc_call || 'N/A'}}\\n` +
                    `Fusion Center: ${{contact.fusion_center || 'N/A'}}\\n` +
                    `K-12: ${{contact.k12 || 'N/A'}}\\n` +
                    `Water/Wastewater: ${{contact.water_wastewater || 'N/A'}}\\n` +
                    `Weekly Rollup: ${{contact.weekly_rollup || 'N/A'}}\\n` +
                    `Alternate Email: ${{contact.alternate_email || 'N/A'}}\\n` +
                    `Region: ${{contact.region || 'N/A'}}\\n` +
                    `Group: ${{contact.group || 'N/A'}}`
                );
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
                    // Map CSV headers to contact fields
                    const fieldMap = {{
                        'email': 'email',
                        'email_address': 'email',
                        'first_name': 'first_name',
                        'firstname': 'first_name',
                        'first': 'first_name',
                        'last_name': 'last_name',
                        'lastname': 'last_name',
                        'last': 'last_name',
                        'title': 'title',
                        'entity_type': 'entity_type',
                        'entitytype': 'entity_type',
                        'state': 'state',
                        'agency_name': 'agency_name',
                        'agencyname': 'agency_name',
                        'agency': 'agency_name',
                        'sector': 'sector',
                        'subsection': 'subsection',
                        'phone': 'phone',
                        'phone_number': 'phone',
                        'ms_isac_member': 'ms_isac_member',
                        'ms-isac': 'ms_isac_member',
                        'msisac': 'ms_isac_member',
                        'soc_call': 'soc_call',
                        'soc': 'soc_call',
                        'fusion_center': 'fusion_center',
                        'fusion': 'fusion_center',
                        'k12': 'k12',
                        'k-12': 'k12',
                        'water_wastewater': 'water_wastewater',
                        'water/wastewater': 'water_wastewater',
                        'water': 'water_wastewater',
                        'weekly_rollup': 'weekly_rollup',
                        'weekly': 'weekly_rollup',
                        'rollup': 'weekly_rollup',
                        'alternate_email': 'alternate_email',
                        'alt_email': 'alternate_email',
                        'region': 'region',
                        'group': 'group'
                    }};
                    
                    const fieldName = fieldMap[header];
                    if (fieldName) {{
                        contact[fieldName] = values[index];
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
        
        function loadContactsForCampaign() {{
            const selectedGroup = document.getElementById('targetGroup').value;
            let targetContacts = allContacts;
            
            if (selectedGroup) {{
                targetContacts = allContacts.filter(contact => contact.group === selectedGroup);
            }}
            
            const contactCount = document.getElementById('contactCount');
            if (targetContacts.length > 0) {{
                contactCount.textContent = `${{targetContacts.length}} contact(s) selected`;
                contactCount.style.display = 'inline-block';
            }} else {{
                contactCount.textContent = 'No contacts selected';
                contactCount.style.display = 'inline-block';
            }}
        }}
        
        async function sendCampaign() {{
            const button = event.target;
            const originalText = button.textContent;
            
            try {{
                // Show loading state
                button.textContent = 'Sending Campaign...';
                button.classList.add('loading');
                button.disabled = true;
                
            const targetGroup = document.getElementById('targetGroup').value;
            
            // Get target contacts based on selected group
            let targetContacts = allContacts;
            if (targetGroup) {{
                targetContacts = allContacts.filter(contact => contact.group === targetGroup);
            }}
            
            if (targetContacts.length === 0) {{
                throw new Error('No contacts found for the selected group. Please add contacts or select a different group.');
            }}
            
            // Get content from textarea
            const emailBody = document.getElementById('body').value;
            
            const campaign = {{
                campaign_name: document.getElementById('campaignName').value,
                subject: document.getElementById('subject').value,
                body: emailBody,
                target_group: targetGroup || null
            }};
                
                // Validate required fields
                if (!campaign.campaign_name || !campaign.subject || !campaign.body) {{
                    throw new Error('Please fill in all required fields');
                }}
            
            const response = await fetch(`${{API_URL}}/campaign`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(campaign)
            }});
            
            const result = await response.json();
            const resultDiv = document.getElementById('campaignResult');
                
                if (result.error) {{
                    throw new Error(result.error);
                }}
                
                // Create a beautiful result display
                resultDiv.innerHTML = `
                    <h3>Campaign Queued Successfully!</h3>
                    <div style="background: var(--info-color); color: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
                        <p style="margin: 0; font-size: 1.1rem;">Your campaign has been queued and emails will be processed asynchronously.</p>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0;">
                        <div style="background: var(--success-color); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                            <h4 style="margin: 0; font-size: 2rem;">${{result.queued_count || 0}}</h4>
                            <p style="margin: 5px 0 0 0;">Queued to SQS</p>
                        </div>
                        <div style="background: var(--warning-color); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                            <h4 style="margin: 0; font-size: 2rem;">${{result.failed_to_queue || 0}}</h4>
                            <p style="margin: 5px 0 0 0;">Failed to Queue</p>
                        </div>
                        <div style="background: var(--info-color); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                            <h4 style="margin: 0; font-size: 2rem;">${{result.total_contacts || 0}}</h4>
                            <p style="margin: 5px 0 0 0;">Total Contacts</p>
                        </div>
                    </div>
                    <div style="background: var(--gray-50); padding: 16px; border-radius: 8px; margin-top: 20px;">
                        <p style="margin: 0; color: var(--gray-700);"><strong>Campaign ID:</strong> ${{result.campaign_id}}</p>
                        <p style="margin: 5px 0 0 0; color: var(--gray-700);"><strong>Target Group:</strong> ${{targetGroup || 'All Groups'}}</p>
                        <p style="margin: 5px 0 0 0; color: var(--gray-700);"><strong>Queue:</strong> ${{result.queue_name || 'bulk-email-queue'}}</p>
                        <p style="margin: 10px 0 0 0; color: var(--gray-600); font-size: 0.9rem;">Check CloudWatch Logs to monitor email processing status</p>
                    </div>
                    <details style="margin-top: 20px;">
                        <summary style="cursor: pointer; color: var(--gray-600);">View Raw Response</summary>
                        <pre style="background: var(--gray-100); padding: 16px; border-radius: 8px; margin-top: 10px; overflow-x: auto;">${{JSON.stringify(result, null, 2)}}</pre>
                    </details>
                `;
            resultDiv.classList.remove('hidden');
                
                button.textContent = 'Campaign Queued!';
                button.style.background = 'linear-gradient(135deg, var(--success-color), #059669)';
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.background = '';
                }}, 3000);
                
            }} catch (error) {{
                const resultDiv = document.getElementById('campaignResult');
                resultDiv.innerHTML = `
                    <h3 style="color: var(--danger-color);">Campaign Failed</h3>
                    <p style="color: var(--gray-600);">${{error.message}}</p>
                `;
                resultDiv.classList.remove('hidden');
                
                button.textContent = 'Error';
                button.style.background = 'linear-gradient(135deg, var(--danger-color), #dc2626)';
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.background = '';
                }}, 3000);
            }} finally {{
                button.classList.remove('loading');
                button.disabled = false;
            }}
        }}
        
        async function loadConfig() {{
            try {{
                const response = await fetch(`${{API_URL}}/config`);
                if (response.ok) {{
                    const result = await response.json();
                    const config = result.config;
                    
                    document.getElementById('emailService').value = config.email_service || 'ses';
                    document.getElementById('fromEmail').value = config.from_email || '';
                    document.getElementById('emailsPerMinute').value = config.emails_per_minute || 60;
                    
                    if (config.email_service === 'ses') {{
                        document.getElementById('awsRegion').value = config.aws_region || 'us-gov-west-1';
                        document.getElementById('awsSecretName').value = config.aws_secret_name || '';
                    }} else {{
                        document.getElementById('smtpServer').value = config.smtp_server || '192.168.1.100';
                        document.getElementById('smtpPort').value = config.smtp_port || 25;
                    }}
                    
                    toggleEmailService();
                }}
            }} catch (e) {{
                console.log('No existing config found');
            }}
        }}
        
        window.onload = () => {{
            loadContacts();
            loadConfig();
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
        print(f"Saving config: {body}")
        
        # Prepare the item with proper data types
        item = {
                'config_id': 'default',
            'email_service': str(body.get('email_service', 'ses')),
            'from_email': str(body.get('from_email', '')),
            'emails_per_minute': int(body.get('emails_per_minute', 60)),
                'updated_at': datetime.now().isoformat()
            }
        
        # Add service-specific fields
        if body.get('email_service') == 'ses':
            item.update({
                'aws_region': str(body.get('aws_region', 'us-gov-west-1')),
                'aws_secret_name': str(body.get('aws_secret_name', ''))
            })
        else:  # SMTP
            item.update({
                'smtp_server': str(body.get('smtp_server', '')),
                'smtp_port': int(body.get('smtp_port', 25))
            })
        
        # Use conditional write to handle updates properly
        email_config_table.put_item(
            Item=item,
            ConditionExpression='attribute_not_exists(config_id) OR config_id = :config_id',
            ExpressionAttributeValues={':config_id': 'default'}
        )
        
        print("Config saved successfully")
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True, 'message': 'Configuration saved successfully'})}
        
    except email_config_table.meta.client.exceptions.ConditionalCheckFailedException:
        # Item already exists, update it instead
        try:
            update_expression = "SET email_service = :service, from_email = :email, emails_per_minute = :rate, updated_at = :updated"
            expression_values = {
                ':service': str(body.get('email_service', 'ses')),
                ':email': str(body.get('from_email', '')),
                ':rate': int(body.get('emails_per_minute', 60)),
                ':updated': datetime.now().isoformat()
            }
            
            # Add service-specific fields to update
            if body.get('email_service') == 'ses':
                update_expression += ", aws_region = :region, aws_secret_name = :secret_name"
                expression_values.update({
                    ':region': str(body.get('aws_region', 'us-gov-west-1')),
                    ':secret_name': str(body.get('aws_secret_name', ''))
                })
            else:  # SMTP
                update_expression += ", smtp_server = :server, smtp_port = :port"
                expression_values.update({
                    ':server': str(body.get('smtp_server', '')),
                    ':port': int(body.get('smtp_port', 25))
                })
            
            email_config_table.update_item(
                Key={'config_id': 'default'},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            print("Config updated successfully")
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True, 'message': 'Configuration updated successfully'})}
            
        except Exception as update_error:
            print(f"Config update error: {str(update_error)}")
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': f'Failed to update config: {str(update_error)}'})}
            
    except Exception as e:
        print(f"Config save error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': f'Failed to save config: {str(e)}', 'error_type': type(e).__name__})}

def get_email_config(headers):
    """Get email configuration"""
    try:
        response = email_config_table.get_item(Key={'config_id': 'default'})
        if 'Item' in response:
            config = response['Item']
            
            # Convert Decimal types to appropriate Python types
            for key, value in config.items():
                if isinstance(value, Decimal):
                    config[key] = int(value) if value % 1 == 0 else float(value)
            
            # Don't return secret name for security (it's stored in Secrets Manager)
            if 'aws_secret_name' in config:
                config['aws_secret_name'] = '***'
                
            print(f"Retrieved config: {config}")
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'config': config})}
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Config not found'})}
    except Exception as e:
        print(f"Config retrieval error: {str(e)}")
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
    """Add new contact with all CISA-specific fields"""
    try:
        contacts_table.put_item(
            Item={
                'email': body['email'],
                'first_name': body.get('first_name', ''),
                'last_name': body.get('last_name', ''),
                'title': body.get('title', ''),
                'entity_type': body.get('entity_type', ''),
                'state': body.get('state', ''),
                'agency_name': body.get('agency_name', ''),
                'sector': body.get('sector', ''),
                'subsection': body.get('subsection', ''),
                'phone': body.get('phone', ''),
                'ms_isac_member': body.get('ms_isac_member', ''),
                'soc_call': body.get('soc_call', ''),
                'fusion_center': body.get('fusion_center', ''),
                'k12': body.get('k12', ''),
                'water_wastewater': body.get('water_wastewater', ''),
                'weekly_rollup': body.get('weekly_rollup', ''),
                'alternate_email': body.get('alternate_email', ''),
                'region': body.get('region', ''),
                'group': body.get('group', ''),
                'created_at': datetime.now().isoformat()
            }
        )
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def update_contact(body, headers):
    """Update contact with all CISA fields"""
    try:
        email = body['email']
        
        # Define all possible contact fields
        contact_fields = [
            'first_name', 'last_name', 'title', 'entity_type', 'state', 
            'agency_name', 'sector', 'subsection', 'phone', 'ms_isac_member',
            'soc_call', 'fusion_center', 'k12', 'water_wastewater', 
            'weekly_rollup', 'alternate_email', 'region', 'group'
        ]
        
        update_expr = "SET "
        expr_values = {}
        update_parts = []
        
        for field in contact_fields:
            if field in body:
                update_parts.append(f"{field} = :{field}")
                expr_values[f":{field}"] = body[field]
        
        if not update_parts:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No fields to update'})}
        
        update_expr += ", ".join(update_parts)
        
        contacts_table.update_item(
            Key={'email': email},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )
        
        print(f"Updated contact {email} with fields: {list(body.keys())}")
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        print(f"Error updating contact: {str(e)}")
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
    """Send email campaign by saving to DynamoDB and queuing contacts to SQS"""
    try:
        # Get email configuration
        config_response = email_config_table.get_item(Key={'config_id': 'default'})
        if 'Item' not in config_response:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Email configuration not found'})}
        
        config = config_response['Item']
        
        # Get contacts (filter by group if specified)
        contacts_response = contacts_table.scan()
        all_contacts = contacts_response['Items']
        
        # Filter by target group if specified
        target_group = body.get('target_group')
        if target_group:
            contacts = [c for c in all_contacts if c.get('group') == target_group]
            print(f"Filtering contacts by group: {target_group}, found {len(contacts)} contacts")
        else:
            contacts = all_contacts
            print(f"Using all contacts: {len(contacts)} contacts")
        
        if not contacts:
            group_msg = f" for group '{target_group}'" if target_group else ""
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': f'No contacts found{group_msg} to send campaign'})}
        
        campaign_id = f"campaign_{int(datetime.now().timestamp())}"
        
        # Save complete campaign data to DynamoDB
        print(f"Saving campaign {campaign_id} to DynamoDB")
        campaigns_table.put_item(
            Item={
                'campaign_id': campaign_id,
                'campaign_name': body.get('campaign_name', 'Bulk Campaign'),
                'subject': body.get('subject', ''),
                'body': body.get('body', ''),
                'from_email': config.get('from_email', ''),
                'email_service': config.get('email_service', 'ses'),
                'aws_region': config.get('aws_region', 'us-gov-west-1'),
                'aws_secret_name': config.get('aws_secret_name', ''),
                'smtp_server': config.get('smtp_server', ''),
                'smtp_port': int(config.get('smtp_port', 25)) if config.get('smtp_port') else 25,
                'status': 'queued',
                'total_contacts': len(contacts),
                'queued_count': 0,
                'sent_count': 0,
                'failed_count': 0,
                'created_at': datetime.now().isoformat()
            }
        )
        print(f"Campaign {campaign_id} saved to DynamoDB")
        
        # Get SQS queue URL
        queue_name = 'bulk-email-queue'
        try:
            queue_url_response = sqs_client.get_queue_url(QueueName=queue_name)
            queue_url = queue_url_response['QueueUrl']
        except sqs_client.exceptions.QueueDoesNotExist:
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': f'SQS queue "{queue_name}" does not exist. Please create it first.'})}
        
        queued_count = 0
        failed_to_queue = 0
        
        # Queue contact email addresses to SQS (minimal payload)
        print(f"Queuing {len(contacts)} contacts to SQS for campaign {campaign_id}")
        
        for contact in contacts:
            try:
                # Minimal message: only campaign_id and contact email
                # Worker Lambda will retrieve campaign details from DynamoDB
                message_body = {
                    'campaign_id': campaign_id,
                    'contact_email': contact.get('email')
                }
                
                # Send message to SQS
                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message_body),
                    MessageAttributes={
                        'campaign_id': {
                            'StringValue': campaign_id,
                            'DataType': 'String'
                        },
                        'contact_email': {
                            'StringValue': contact.get('email', 'unknown'),
                            'DataType': 'String'
                        }
                    }
                )
                queued_count += 1
                print(f"Queued email for {contact.get('email')}")
                
            except Exception as e:
                print(f"Failed to queue email for {contact.get('email')}: {str(e)}")
                failed_to_queue += 1
        
        # Update campaign status
        campaigns_table.update_item(
            Key={'campaign_id': campaign_id},
            UpdateExpression="SET #status = :status, queued_count = :queued",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'processing',
                ':queued': queued_count
            }
        )
        
        print(f"Campaign {campaign_id}: Queued {queued_count} emails, {failed_to_queue} failed to queue")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'campaign_id': campaign_id,
                'message': 'Campaign queued successfully',
                'target_group': target_group,
                'total_contacts': len(contacts),
                'queued_count': queued_count,
                'failed_to_queue': failed_to_queue,
                'queue_name': queue_name,
                'note': 'Emails will be processed asynchronously from the SQS queue'
            })
        }
        
    except Exception as e:
        print(f"Campaign error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

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
        
        print("Successfully retrieved AWS credentials from Secrets Manager")
        return credentials
        
    except Exception as e:
        print(f"Error retrieving credentials from Secrets Manager: {str(e)}")
        raise

def personalize_content(content, contact):
    """Replace placeholders with contact data - supports all CISA fields"""
    if not content:
        return content
        
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