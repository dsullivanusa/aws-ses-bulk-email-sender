import json
import boto3
import smtplib
import ssl
import time
import os
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
s3_client = boto3.client('s3', region_name='us-gov-west-1')

# S3 bucket for attachments
ATTACHMENTS_BUCKET = 'jcdc-ses-contact-list'

# Custom API URL configuration
# To use your own domain instead of the AWS API Gateway URL:
# 1. Set Lambda environment variable: CUSTOM_API_URL = https://yourdomain.com
# 2. If using API Gateway Custom Domain, set it to: https://api.yourdomain.com/prod
# 3. Make sure your custom domain routes to this Lambda function
# If not set, it will automatically use the API Gateway URL
CUSTOM_API_URL = os.environ.get('CUSTOM_API_URL', None)
###*** for NOW
CUSTOM_API_URL = None
### *** for NOW


# Cognito configuration (optional authentication)
def load_cognito_config():
    """Load Cognito configuration if available"""
    try:
        s3 = boto3.client('s3', region_name='us-gov-west-1')
        obj = s3.get_object(Bucket=ATTACHMENTS_BUCKET, Key='cognito_config.json')
        config = json.loads(obj['Body'].read().decode('utf-8'))
        return config if config.get('enabled', False) else None
    except:
        return None  # Cognito not configured or disabled

COGNITO_CONFIG = load_cognito_config()

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
            return get_contacts(headers, event)
        elif path == '/contacts' and method == 'POST':
            return add_contact(body, headers)
        elif path == '/contacts' and method == 'PUT':
            return update_contact(body, headers)
        elif path == '/contacts' and method == 'DELETE':
            return delete_contact(event, headers)
        elif path == '/contacts/batch' and method == 'POST':
            return batch_add_contacts(body, headers)
        elif path == '/groups' and method == 'GET':
            return get_groups(headers)
        elif path == '/contacts/search' and method == 'POST':
            return search_contacts(body, headers)
        elif path == '/upload-attachment' and method == 'POST':
            return upload_attachment(body, headers)
        elif path == '/campaign' and method == 'POST':
            return send_campaign(body, headers, event)
        elif path == '/campaign/{campaign_id}' and method == 'GET':
            campaign_id = event['pathParameters']['campaign_id']
            return get_campaign_status(campaign_id, headers)
        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}
            
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def serve_web_ui(event):
    """Serve web UI HTML"""
    # Use custom API URL if configured, otherwise use API Gateway URL
    if CUSTOM_API_URL:
        api_url = CUSTOM_API_URL
    else:
        api_id = event.get('requestContext', {}).get('apiId', 'UNKNOWN')
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CISA Email Campaign Management System</title>
    
    <!-- Quill Rich Text Editor -->
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <script src="https://cdn.quilljs.com/1.3.6/quill.js"></script>
    
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
            background: linear-gradient(135deg, #cbd5e1, #94a3b8);
            cursor: pointer; 
            text-align: center; 
            border-radius: 8px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            font-weight: 600; 
            color: #1e293b;
            position: relative;
            overflow: hidden;
            z-index: 10;
            pointer-events: auto;
            user-select: none;
            border: 2px solid #94a3b8;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .tab:hover {{ 
            background: linear-gradient(135deg, #3b82f6, #2563eb); 
            color: white;
            transform: translateY(-1px);
            border-color: #2563eb;
            box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
        }}
        .tab.active {{ 
            background: linear-gradient(135deg, #10b981, #059669); 
            color: white; 
            box-shadow: 0 6px 12px rgba(16, 185, 129, 0.4);
            transform: translateY(-2px);
            border-color: #059669;
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
        /* Checkbox styling */
        input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            cursor: pointer;
            accent-color: var(--primary-color);
        }}
        input[type="checkbox"]:checked + span {{
            font-weight: 600;
            color: var(--primary-color);
        }}
        .filterCheckbox:checked {{
            transform: scale(1.1);
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
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{ 
            box-shadow: 0 10px 25px rgba(59, 130, 246, 0.4); 
        }}
        .btn-info {{ 
            background: linear-gradient(135deg, var(--info-color), #2563eb); 
        }}
        .btn-info:hover {{ 
            box-shadow: 0 10px 25px rgba(59, 130, 246, 0.4); 
        }}
        .btn-warning {{ 
            background: linear-gradient(135deg, var(--warning-color), #d97706); 
        }}
        .btn-warning:hover {{ 
            box-shadow: 0 10px 25px rgba(245, 158, 11, 0.4); 
        }}
        
        /* Table Action Buttons - Consistent Sizing */
        table button {{
            padding: 8px 16px;
            margin: 4px 2px;
            font-size: 14px;
            min-width: 70px;
            display: inline-block;
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
        
        /* Searching Indicator */
        .searching-indicator {{
            display: inline-block;
            margin-left: 12px;
            padding: 6px 12px;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            transition: opacity 0.3s ease-in-out;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }}
        .searching-indicator.show {{
            opacity: 1 !important;
            animation: pulse 1.5s ease-in-out infinite;
        }}
        .searching-indicator.hide {{
            opacity: 0 !important;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.6; }}
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
        
        /* Editable Table Cells */
        .editable-cell {{
            cursor: text;
            padding: 8px;
            min-height: 20px;
            transition: background-color 0.2s;
            border: 1px solid transparent;
        }}
        .editable-cell:hover {{
            background: #f0f9ff !important;
            border: 1px solid #bae6fd;
        }}
        .editable-cell:focus {{
            outline: 2px solid #3b82f6;
            outline-offset: -2px;
            background: #fff3cd !important;
        }}
        .editable-cell:empty:before {{
            content: attr(placeholder);
            color: #9ca3af;
        }}
        .yes-no-cell {{
            text-align: center;
        }}
        #contactsTable {{
            border-collapse: separate;
            border-spacing: 0;
        }}
        #contactsTable th {{
            position: sticky;
            top: 0;
            background: linear-gradient(135deg, #1e40af, #1e3a8a);
            color: white;
            z-index: 10;
            font-weight: 700;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 14px 10px;
            border-bottom: 3px solid #3b82f6;
            border-right: 1px solid #1e3a8a;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        #contactsTable td {{
            border-bottom: 1px solid #e5e7eb;
            border-right: 1px solid #f3f4f6;
            padding: 8px 10px;
            background: white;
        }}
        #contactsTable tr:hover td {{
            background: #eff6ff;
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
            <div class="tab active" onclick="showTab('config', this)">⚙️ Email Config</div>
            <div class="tab" onclick="showTab('contacts', this)">👥 Contacts</div>
            <div class="tab" onclick="showTab('campaign', this)">📧 Send Campaign</div>
        </div>
        
        <div id="config" class="tab-content active">
            <h2>⚙️ Email Configuration</h2>
                <div class="form-group">
                    <label>🌍 AWS Region:</label>
                    <input type="text" id="awsRegion" value="us-gov-west-1">
            </div>
            
            <div class="form-group">
                <label>📧 From Email:</label>
                <input type="email" id="fromEmail">
            </div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button onclick="saveConfig()">💾 Save Configuration</button>
                <!-- <button onclick="loadConfig()" style="background: #007bff;">Test Load Config</button> -->
            </div>
        </div>
        
        <div id="contacts" class="tab-content">
            <h2>👥 Contact Management</h2>
            <div class="form-group">
                <label>🔍 Contact Filter:</label>
                <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px; align-items: start;">
                    <div style="position: relative; z-index: 100;">
                        <select id="filterType" onchange="loadFilterValues()" title="Select a filter type - you can change this anytime" style="width: 100%; cursor: pointer;">
                            <option value="">All Contacts</option>
                            <option value="entity_type">Entity Type</option>
                            <option value="state">State</option>
                            <option value="agency_name">Agency Name</option>
                            <option value="sector">Sector</option>
                            <option value="subsection">Subsection</option>
                            <option value="ms_isac_member">MS-ISAC Member</option>
                            <option value="soc_call">SOC Call</option>
                            <option value="fusion_center">Fusion Center</option>
                            <option value="k12">K-12</option>
                            <option value="water_wastewater">Water/Wastewater</option>
                            <option value="weekly_rollup">Weekly Rollup</option>
                            <option value="region">Region</option>
                        </select>
                    </div>
                    <div id="filterValueContainer" style="display: none;">
                        <div style="max-height: 300px; overflow-y: auto; padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <button onclick="selectAllFilterValues()" style="padding: 6px 12px; font-size: 13px; background: #10b981; margin-right: 8px;">✅ Select All</button>
                                    <button onclick="clearAllFilterValues()" style="padding: 6px 12px; font-size: 13px; background: #ef4444;">❌ Clear All</button>
            </div>
                                <small style="color: #6b7280; margin: 0;">Click checkboxes to load filtered contacts</small>
                            </div>
                            <div id="filterValueCheckboxes"></div>
                        </div>
                        <small style="display: block; margin-top: 8px; color: #6b7280;" id="filterCount"></small>
                    </div>
                </div>
            </div>
            <button onclick="loadContacts()">🔄 Load Contacts</button>
            <button class="btn-success" onclick="showAddContact()">➕ Add Contact</button>
            <input type="file" id="csvFile" accept=".csv" style="display: none;" onchange="uploadCSV()">
            <button onclick="document.getElementById('csvFile').click()">📤 Upload CSV (Batch)</button>
            
            <!-- CSV Upload Progress Bar -->
            <div id="csvUploadProgress" class="hidden" style="margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                <h4 style="margin: 0 0 10px 0;">📊 CSV Import Progress</h4>
                <div style="background: #e9ecef; border-radius: 4px; height: 30px; overflow: hidden; margin-bottom: 10px;">
                    <div id="csvProgressBar" style="background: linear-gradient(90deg, #10b981, #059669); height: 100%; width: 0%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 14px;"></div>
                </div>
                <div id="csvProgressText" style="font-size: 14px; color: #6b7280;"></div>
                <button id="csvCancelButton" onclick="cancelCSVUpload()" style="margin-top: 10px; background: #ef4444;">⛔ Cancel Import</button>
            </div>
            
            <div id="addContactForm" class="hidden card">
                <h3>➕ Add Contact</h3>
                <p style="margin: 0 0 15px 0; padding: 10px; background: #e0f2fe; border-left: 4px solid #0284c7; border-radius: 4px; color: #0c4a6e;">
                    <strong>📋 Required:</strong> Email Address is required. All other fields are optional.
                </p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <input type="email" id="newEmail" placeholder="Email Address *" required>
                    <input type="text" id="newFirstName" placeholder="First Name" required>
                    <input type="text" id="newLastName" placeholder="Last Name" required>
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
                </div>
                <div style="margin-top: 20px;">
                    <button class="btn-success" onclick="addContact()">✅ Add</button>
                <button onclick="hideAddContact()">❌ Cancel</button>
                </div>
            </div>
            
            <div id="editContactForm" class="hidden card">
                <h3>✏️ Edit Contact</h3>
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
                </div>
                <div style="margin-top: 20px;">
                    <button class="btn-success" onclick="saveContactEdit()">💾 Save Changes</button>
                    <button onclick="hideEditContact()">❌ Cancel</button>
                </div>
            </div>
            
            <!-- <div class="result">
                <strong>CSV Format:</strong> email,first_name,last_name,title,entity_type,state,agency_name,sector,subsection,phone,ms_isac_member,soc_call,fusion_center,k12,water_wastewater,weekly_rollup,alternate_email,region,group<br>
                <strong>Example:</strong> john@example.com,John,Doe,IT Director,State Government,CA,Dept of Tech,Government,IT,555-0100,Yes,Yes,No,No,No,Yes,john.alt@example.com,West,State CISOs
            </div> -->
            
            <div class="form-group" style="margin-top: 20px;">
                <label>🔎 Search by Name:</label>
                <div style="position: relative;">
                    <input type="text" id="nameSearch" placeholder="Search by first or last name..." oninput="debouncedSearch()" style="margin-bottom: 10px;">
                    <span id="searchingIndicator" class="searching-indicator" style="opacity: 0;">🔍 Searching DynamoDB...</span>
                </div>
                <small id="searchResults" style="color: #6b7280;"></small>
            </div>
            
            <!-- Pagination Controls -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;">
                <div style="display: flex; gap: 10px; align-items: center;">
                    <label style="font-weight: 600; color: #374151;">Page Size:</label>
                    <select id="pageSize" onchange="changePageSize()" style="padding: 8px 12px; border-radius: 6px; border: 1px solid #d1d5db;">
                        <option value="25" selected>25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                    </select>
                    <span id="pageInfo" style="margin-left: 15px; color: #6b7280; font-weight: 500;">Page 1</span>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="prevPageBtn" onclick="previousPage()" disabled style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">⬅️ Previous</button>
                    <button id="nextPageBtn" onclick="nextPage()" disabled style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">Next ➡️</button>
                </div>
            </div>
            
            <div style="overflow-x: auto;">
            <table id="contactsTable">
                <thead>
                        <tr>
                            <th style="min-width: 200px;">Email</th>
                            <th style="min-width: 120px;">First Name</th>
                            <th style="min-width: 120px;">Last Name</th>
                            <th style="min-width: 150px;">Title</th>
                            <th style="min-width: 150px;">Entity Type</th>
                            <th style="min-width: 80px;">State</th>
                            <th style="min-width: 150px;">Agency</th>
                            <th style="min-width: 120px;">Sector</th>
                            <th style="min-width: 120px;">Subsection</th>
                            <th style="min-width: 120px;">Phone</th>
                            <th style="min-width: 100px;">MS-ISAC</th>
                            <th style="min-width: 100px;">SOC Call</th>
                            <th style="min-width: 120px;">Fusion Center</th>
                            <th style="min-width: 80px;">K-12</th>
                            <th style="min-width: 150px;">Water/Wastewater</th>
                            <th style="min-width: 130px;">Weekly Rollup</th>
                            <th style="min-width: 200px;">Alt Email</th>
                            <th style="min-width: 100px;">Region</th>
                            <th style="min-width: 100px; position: sticky; right: 0; background: linear-gradient(135deg, #1e40af, #1e3a8a); box-shadow: -2px 0 4px rgba(0,0,0,0.2);">Actions</th>
                        </tr>
                </thead>
                <tbody id="contactsBody"></tbody>
            </table>
            </div>
            
            <div style="margin-top: 15px; padding: 10px; background: #f3f4f6; border-radius: 6px; text-align: center;">
                <span id="recordCount" style="color: #6b7280; font-size: 14px;"></span>
            </div>
        </div>
        
        <div id="campaign" class="tab-content">
            <h2>📧 Send Campaign</h2>
            <div id="formStatus" class="form-status" style="display: none; padding: 10px; margin-bottom: 15px; border-radius: 4px; background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;"></div>
            <div class="form-group">
                <label>🎯 Target Contacts:</label>
                <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px; align-items: start;">
                    <div style="position: relative; z-index: 100;">
                        <select id="campaignFilterType" onchange="loadCampaignFilterValues()" style="width: 100%; cursor: pointer;">
                            <option value="">All Contacts</option>
                            <option value="test_group">🧪 Test Group Only</option>
                            <option value="entity_type">Entity Type</option>
                            <option value="state">State</option>
                            <option value="agency_name">Agency Name</option>
                            <option value="sector">Sector</option>
                            <option value="subsection">Subsection</option>
                            <option value="ms_isac_member">MS-ISAC Member</option>
                            <option value="soc_call">SOC Call</option>
                            <option value="fusion_center">Fusion Center</option>
                            <option value="k12">K-12</option>
                            <option value="water_wastewater">Water/Wastewater</option>
                            <option value="weekly_rollup">Weekly Rollup</option>
                            <option value="region">Region</option>
                        </select>
                    </div>
                    <div id="campaignFilterValueContainer" style="display: none;">
                        <div style="max-height: 300px; overflow-y: auto; padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb;">
                                <button onclick="selectAllCampaignFilters()" style="padding: 6px 12px; font-size: 13px; background: #10b981; margin-right: 8px;">✅ Select All</button>
                                <button onclick="clearAllCampaignFilters()" style="padding: 6px 12px; font-size: 13px; background: #ef4444;">❌ Clear All</button>
                            </div>
                            <div id="campaignFilterCheckboxes"></div>
                        </div>
                        <small style="display: block; margin-top: 8px; color: #6b7280;" id="campaignFilterCount"></small>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label>👤 Your Name:</label>
                <input type="text" id="userName" placeholder="Enter your name (saved in browser)" onchange="saveUserName()">
                <small style="color: #6b7280;">This will be recorded as who launched the campaign. Your name is saved in your browser.</small>
            </div>
            <div class="form-group">
                <label>📝 Campaign Name:</label>
                <input type="text" id="campaignName">
            </div>
            <div class="form-group">
                <label>📨 Subject:</label>
                <input type="text" id="subject" placeholder="Hello {{{{first_name}}}}">
            </div>
            <div class="form-group">
                <label>📄 Email Body:</label>
                <div id="body" style="min-height: 200px; background: white;"></div>
                <small>Available placeholders: {{{{first_name}}}}, {{{{last_name}}}}, {{{{email}}}}, {{{{title}}}}, {{{{entity_type}}}}, {{{{state}}}}, {{{{agency_name}}}}, {{{{sector}}}}, {{{{subsection}}}}, {{{{phone}}}}, {{{{ms_isac_member}}}}, {{{{soc_call}}}}, {{{{fusion_center}}}}, {{{{k12}}}}, {{{{water_wastewater}}}}, {{{{weekly_rollup}}}}, {{{{alternate_email}}}}, {{{{region}}}}, {{{{group}}}}</small>
            </div>
            
            <div class="form-group">
                <label>📎 Attachments (Optional):</label>
                <div style="margin-bottom: 10px; padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                    <strong>Important:</strong> Maximum total size is <strong>40 MB per email</strong> (including all attachments). 
                    Supported formats: PDF, DOC, DOCX, XLS, XLSX, PNG, JPG, TXT, CSV
                </div>
                <input type="file" id="attachmentFiles" multiple style="display: none;" onchange="handleAttachmentUpload()">
                <button onclick="document.getElementById('attachmentFiles').click()" style="background: #6366f1;">
                    📎 Add Attachments
                </button>
                <div id="attachmentsList" style="margin-top: 15px;"></div>
                <div id="attachmentSize" style="margin-top: 10px; font-size: 14px; color: #6b7280;"></div>
            </div>
            
            <div style="display: flex; gap: 15px; margin-top: 20px;">
            <button class="btn-success" onclick="sendCampaign()">🚀 Send Campaign</button>
                <button onclick="clearCampaignForm()">🗑️ Clear Form</button>
            </div>
            
            <div id="campaignResult" class="result hidden"></div>
        </div>
    </div>
    
    <script>
        const API_URL = '{api_url}';
        
        // Initialize Quill Rich Text Editor
        let quillEditor;
        document.addEventListener('DOMContentLoaded', function() {{
            quillEditor = new Quill('#body', {{
                theme: 'snow',
                placeholder: 'Dear {{{{first_name}}}} {{{{last_name}}}},\\n\\nYour message here...',
                modules: {{
                    toolbar: [
                        [{{ 'header': [1, 2, 3, false] }}],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{{ 'color': [] }}, {{ 'background': [] }}],
                        [{{ 'list': 'ordered'}}, {{ 'list': 'bullet' }}],
                        [{{ 'align': [] }}],
                        ['link', 'image'],
                        ['clean']
                    ]
                }}
            }});
        }});
        
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
            
            // Auto-load data when switching to specific tabs
            if (tabName === 'contacts' && paginationState.displayedContacts.length === 0) {{
                // Auto-load contacts when first switching to Contacts tab
                console.log('Auto-loading contacts...');
                loadContacts();
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
                
                const config = {{
                    email_service: 'ses',
                    aws_region: document.getElementById('awsRegion').value,
                    from_email: document.getElementById('fromEmail').value
                }};
                
                console.log('Saving config:', config);
                console.log('API URL:', API_URL);
                
                const response = await fetch(`${{API_URL}}/config`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(config)
                }});
                
                console.log('Save response status:', response.status);
            
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
                console.error('Save config error:', error);
                button.textContent = 'Error';
                button.style.background = 'linear-gradient(135deg, var(--danger-color), #dc2626)';
                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.background = '';
                }}, 2000);
                
                // More specific error messages
                if (error.message.includes('Failed to fetch') || error.message.includes('fetch')) {{
                    alert('Network Error: Cannot connect to the API. Check if the Lambda function is deployed and the API Gateway URL is correct.\\n\\nAPI URL: ' + API_URL);
                }} else {{
                    alert('Error: ' + error.message);
                }}
            }} finally {{
                button.classList.remove('loading');
                button.disabled = false;
            }}
        }}
        
        let allContacts = [];
        let allGroups = [];
        let userSessionId = Math.random().toString(36).substr(2, 9);
        console.log('User session ID:', userSessionId);
        
        // Pagination state
        let paginationState = {{
            currentPage: 1,
            pageSize: 25,
            paginationKeys: [null], // Stack of LastEvaluatedKeys for each page
            hasNextPage: false,
            displayedContacts: []
        }};
        
        
        function showFormStatus(message, type = 'warning') {{
            const statusDiv = document.getElementById('formStatus');
            if (statusDiv) {{
                statusDiv.textContent = message;
                statusDiv.style.display = 'block';
                
                // Set color based on type
                if (type === 'error') {{
                    statusDiv.style.background = '#f8d7da';
                    statusDiv.style.borderColor = '#f5c6cb';
                    statusDiv.style.color = '#721c24';
                }} else if (type === 'success') {{
                    statusDiv.style.background = '#d4edda';
                    statusDiv.style.borderColor = '#c3e6cb';
                    statusDiv.style.color = '#155724';
                }}
                
                // Auto-hide after 5 seconds
                setTimeout(() => {{
                    statusDiv.style.display = 'none';
                }}, 5000);
            }}
        }}
        
        function checkFormAvailability() {{
            const campaignName = document.getElementById('campaignName');
            const subject = document.getElementById('subject');
            const body = document.getElementById('body');
            
            if (!campaignName || !subject || !body) {{
                console.error('Form elements not found');
                showFormStatus('Form elements not found. Please refresh the page.', 'error');
                return false;
            }}
            
            // Check if form is disabled or readonly
            if (campaignName.disabled || subject.disabled || body.disabled) {{
                console.warn('Form is currently disabled');
                showFormStatus('Form is currently being used by another user. Please wait and try again.', 'warning');
                return false;
            }}
            
            return true;
        }}
        
        function clearCampaignForm() {{
            if (!checkFormAvailability()) {{
                alert('Form is currently unavailable. Please refresh the page.');
                return;
            }}
            
            document.getElementById('campaignName').value = '';
            document.getElementById('subject').value = '';
            quillEditor.setContents([]);
            
            // Clear campaign filter
            document.getElementById('campaignFilterType').value = '';
            document.getElementById('campaignFilterValueContainer').style.display = 'none';
            clearAllCampaignFilters();
            
            // Clear attachments
            campaignAttachments = [];
            displayAttachments();
        }};
        
        async function loadContacts(resetPagination = true) {{
            console.log('loadContacts called, resetPagination:', resetPagination);
            const button = event?.target || document.querySelector('button[onclick="loadContacts()"]');
            const originalText = button?.textContent || '🔄 Load Contacts';
            
            if (resetPagination) {{
                // Reset pagination to first page
                paginationState = {{
                    currentPage: 1,
                    pageSize: parseInt(document.getElementById('pageSize').value) || 25,
                    paginationKeys: [null],
                    hasNextPage: false,
                    displayedContacts: []
                }};
            }}
            
            try {{
                if (button) {{
                    button.textContent = '⏳ Loading...';
                    button.disabled = true;
                }}
                
                // Get the pagination key for the current page
                const paginationKey = paginationState.paginationKeys[paginationState.currentPage - 1];
                
                // Build URL with pagination parameters
                let url = `${{API_URL}}/contacts?limit=${{paginationState.pageSize}}`;
                if (paginationKey) {{
                    url += `&lastKey=${{encodeURIComponent(JSON.stringify(paginationKey))}}`;
                }}
                
                console.log('Fetching contacts from:', url);
                const response = await fetch(url);
                console.log('Contacts response status:', response.status);
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const result = await response.json();
                console.log('Contacts result:', result);
                
                paginationState.displayedContacts = result.contacts || [];
                paginationState.hasNextPage = result.lastEvaluatedKey ? true : false;
                
                // Store the lastEvaluatedKey for the next page
                if (result.lastEvaluatedKey && paginationState.paginationKeys.length === paginationState.currentPage) {{
                    paginationState.paginationKeys.push(result.lastEvaluatedKey);
                }}
                
                console.log('Loaded contacts count:', paginationState.displayedContacts.length);
                console.log('Has next page:', paginationState.hasNextPage);
                
                displayContacts(paginationState.displayedContacts);
                updatePaginationControls();
                
                if (button) {{
                    button.textContent = '✅ Loaded';
                    setTimeout(() => {{
                        button.textContent = originalText;
                    }}, 1500);
                }}
                
            }} catch (error) {{
                console.error('Error loading contacts:', error);
                const tbody = document.getElementById('contactsBody');
                tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--danger-color); padding: 40px;">Error loading contacts: ' + error.message + '</td></tr>';
                
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
        
        function updatePaginationControls() {{
            // Update page info
            document.getElementById('pageInfo').textContent = `Page ${{paginationState.currentPage}}`;
            
            // Update prev button
            const prevBtn = document.getElementById('prevPageBtn');
            prevBtn.disabled = paginationState.currentPage === 1;
            prevBtn.style.background = paginationState.currentPage === 1 ? '#9ca3af' : '#6b7280';
            prevBtn.style.cursor = paginationState.currentPage === 1 ? 'not-allowed' : 'pointer';
            
            // Update next button
            const nextBtn = document.getElementById('nextPageBtn');
            nextBtn.disabled = !paginationState.hasNextPage;
            nextBtn.style.background = !paginationState.hasNextPage ? '#9ca3af' : '#3b82f6';
            nextBtn.style.cursor = !paginationState.hasNextPage ? 'not-allowed' : 'pointer';
        }}
        
        async function nextPage() {{
            if (!paginationState.hasNextPage) return;
            
            paginationState.currentPage++;
            await loadContacts(false);
        }}
        
        async function previousPage() {{
            if (paginationState.currentPage === 1) return;
            
            paginationState.currentPage--;
            await loadContacts(false);
        }}
        
        async function changePageSize() {{
            const newPageSize = parseInt(document.getElementById('pageSize').value);
            paginationState.pageSize = newPageSize;
            
            // Reset to first page with new page size
            await loadContacts(true);
        }}
        
        async function loadAllContacts() {{
            await loadContacts();
            document.getElementById('filterType').value = '';
            document.getElementById('filterValueContainer').style.display = 'none';
            document.getElementById('nameSearch').value = '';
            applyContactFilter();
        }}
        
        async function loadGroupsFromDB() {{
            try {{
                console.log('Loading groups from DynamoDB...');
                console.log('API URL:', `${{API_URL}}/groups`);
                const response = await fetch(`${{API_URL}}/groups`);
                
                if (response.ok) {{
                    const result = await response.json();
                    allGroups = result.groups || [];
                    console.log('Loaded groups from API:', allGroups);
                    console.log('Number of groups found:', allGroups.length);
                }} else {{
                    console.error('Error loading groups. Status:', response.status);
                    console.error('Response:', await response.text());
                    alert('Warning: Could not load groups from database. Status: ' + response.status);
                }}
            }} catch (error) {{
                console.error('Error loading groups:', error);
                alert('Error loading groups: ' + error.message + '\\n\\nMake sure the /groups endpoint is configured in API Gateway.');
            }}
        }}
        
        async function loadFilterValues() {{
            const filterType = document.getElementById('filterType').value;
            const filterValueContainer = document.getElementById('filterValueContainer');
            const filterValueCheckboxes = document.getElementById('filterValueCheckboxes');
            const filterTypeDropdown = document.getElementById('filterType');
            
            // Always keep filter type dropdown enabled
            filterTypeDropdown.disabled = false;
            
            if (!filterType) {{
                // No filter type selected - show all contacts
                filterValueContainer.style.display = 'none';
                // Clear search if switching to "All Contacts"
                document.getElementById('nameSearch').value = '';
                document.getElementById('searchResults').textContent = '';
                applyContactFilter();
                return;
            }}
            
            // Auto-load contacts if not already loaded
            if (allContacts.length === 0) {{
                console.log('Contacts not loaded yet, loading now...');
                await loadContacts();
            }}
            
            // Get distinct values for selected field from loaded contacts
            const distinctValues = [...new Set(
                allContacts
                    .map(c => c[filterType])
                    .filter(v => v && v.trim() !== '')
            )].sort();
            
            console.log(`Found ${{distinctValues.length}} distinct values for ${{filterType}}`);
            
            // Populate filter value checkboxes
            filterValueCheckboxes.innerHTML = '';
            distinctValues.forEach((value, index) => {{
                const checkboxDiv = document.createElement('div');
                checkboxDiv.style.marginBottom = '5px';
                checkboxDiv.innerHTML = `
                    <label style="display: flex; align-items: center; padding: 8px; cursor: pointer; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='#e0e7ff'" onmouseout="this.style.background='transparent'">
                        <input type="checkbox" class="filterCheckbox" value="${{value}}" onchange="onFilterCheckboxChange()" style="margin-right: 10px; width: auto;">
                        <span>${{value}}</span>
                    </label>
                `;
                filterValueCheckboxes.appendChild(checkboxDiv);
            }});
            
            filterValueContainer.style.display = 'block';
            updateFilterCount();
        }}
        
        async function onFilterCheckboxChange() {{
            const checkedBoxes = document.querySelectorAll('.filterCheckbox:checked');
            
            console.log(`Filter checkbox changed. ${{checkedBoxes.length}} selected`);
            
            // If any checkboxes are selected, load contacts from DynamoDB
            if (checkedBoxes.length > 0) {{
                console.log('Loading contacts from DynamoDB based on filter selection...');
                await loadContactsWithFilter();
            }} else {{
                // No checkboxes selected - just update count
                updateFilterCount();
                displayContacts(allContacts);
            }}
        }}
        
        async function loadContactsWithFilter() {{
            const filterType = document.getElementById('filterType').value;
            const checkedBoxes = document.querySelectorAll('.filterCheckbox:checked');
            
            if (!filterType || checkedBoxes.length === 0) {{
                // No filter active - load all contacts
                await loadContacts();
                return;
            }}
            
            const selectedValues = Array.from(checkedBoxes).map(cb => cb.value);
            
            try {{
                console.log(`Querying DynamoDB for ${{filterType}} IN [${{selectedValues.join(', ')}}]...`);
                
                // Load all contacts from DynamoDB
                const response = await fetch(`${{API_URL}}/contacts`);
                
                if (response.ok) {{
                    const result = await response.json();
                    allContacts = result.contacts || [];
                    
                    // Filter based on selection
                    const filteredContacts = allContacts.filter(contact => 
                        contact[filterType] && selectedValues.includes(contact[filterType])
                    );
                    
                    console.log(`Loaded ${{allContacts.length}} total contacts, ${{filteredContacts.length}} match filter`);
                    
                    updateFilterCount();
                    displayContacts(filteredContacts);
                }} else {{
                    console.error('Failed to load contacts:', response.status);
                }}
            }} catch (error) {{
                console.error('Error loading contacts with filter:', error);
            }}
        }}
        
        async function applyContactFilter() {{
            const searchTerm = document.getElementById('nameSearch').value.trim();
            
            // If there's a search term, always use DynamoDB search instead
            if (searchTerm && searchTerm.length >= 2) {{
                console.log('Search term detected - using DynamoDB search instead of local filter');
                await searchContactsByName();
                return;
            }}
            
            // Auto-load contacts if not already loaded
            if (allContacts.length === 0) {{
                console.log('Auto-loading contacts for filter...');
                await loadContacts();
                return; // loadContacts will call applyContactFilter when done
            }}
            
            const filterType = document.getElementById('filterType').value;
            const checkedBoxes = document.querySelectorAll('.filterCheckbox:checked');
            
            let filteredContacts = allContacts;
            
            // Apply category filter from checked checkboxes
            if (filterType && checkedBoxes.length > 0) {{
                const selectedValues = Array.from(checkedBoxes).map(cb => cb.value);
                
                filteredContacts = filteredContacts.filter(contact => 
                    contact[filterType] && selectedValues.includes(contact[filterType])
                );
                
                console.log(`Filtered by ${{filterType}} IN [${{selectedValues.join(', ')}}]: ${{filteredContacts.length}} contacts`);
            }} else if (!filterType) {{
                // Show all contacts when no filter type selected
                console.log(`Showing all contacts: ${{filteredContacts.length}}`);
            }} else {{
                // Filter type selected but no checkboxes checked - show all
                console.log('Filter type selected but no values checked - showing all');
            }}
            
            document.getElementById('searchResults').textContent = '';
            updateFilterCount();
            displayContacts(filteredContacts);
        }}
        
        async function selectAllFilterValues() {{
            const checkboxes = document.querySelectorAll('.filterCheckbox');
            checkboxes.forEach(cb => cb.checked = true);
            await onFilterCheckboxChange();
        }}
        
        async function clearAllFilterValues() {{
            const checkboxes = document.querySelectorAll('.filterCheckbox');
            checkboxes.forEach(cb => cb.checked = false);
            updateFilterCount();
            // When cleared, show all contacts or apply just category filter
            await applyContactFilter();
        }}
        
        // Debounce search to avoid too many API calls while typing
        let searchTimeout;
        function debouncedSearch() {{
            clearTimeout(searchTimeout);
            const searchTerm = document.getElementById('nameSearch').value.trim();
            const searchResults = document.getElementById('searchResults');
            
            if (!searchTerm) {{
                // If empty, clear immediately and hide indicator
                hideSearchingIndicator();
                searchContactsByName();
                return;
            }}
            
            // Show "Typing..." while user is still typing
            if (searchTerm.length >= 2) {{
                searchResults.textContent = 'Typing...';
                searchResults.style.color = '#9ca3af';
            }}
            
            // Wait 500ms after user stops typing, then search
            searchTimeout = setTimeout(() => {{
                searchContactsByName();
            }}, 500);
        }}
        
        function updateFilterCount() {{
            const checkedBoxes = document.querySelectorAll('.filterCheckbox:checked');
            const filterCount = document.getElementById('filterCount');
            
            if (checkedBoxes.length > 0) {{
                filterCount.textContent = `${{checkedBoxes.length}} filter(s) selected`;
            }} else {{
                filterCount.textContent = 'No filters selected - showing all';
            }}
        }}
        
        async function searchContactsByName() {{
            const searchTerm = document.getElementById('nameSearch').value.trim();
            const searchResults = document.getElementById('searchResults');
            const searchingIndicator = document.getElementById('searchingIndicator');
            
            if (!searchTerm) {{
                // Empty search - apply current filter or show all
                searchResults.textContent = '';
                hideSearchingIndicator();
                applyContactFilter();
                return;
            }}
            
            if (searchTerm.length < 2) {{
                searchResults.textContent = 'Enter at least 2 characters to search';
                hideSearchingIndicator();
                return;
            }}
            
            try {{
                console.log(`Searching DynamoDB for: "${{searchTerm}}"`);
                
                // Show searching indicator with fade-in
                showSearchingIndicator();
                searchResults.textContent = '';
                
                // Search DynamoDB via API
                const response = await fetch(`${{API_URL}}/contacts/search`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ search_term: searchTerm }})
                }});
                
                console.log('Search response status:', response.status);
                console.log('Search response ok:', response.ok);
                
                if (response.ok) {{
                    const result = await response.json();
                    console.log('Search result:', result);
                    const searchedContacts = result.contacts || [];
                    
                    console.log(`✅ Found ${{searchedContacts.length}} contacts matching "${{searchTerm}}"`);
                    
                    // Apply category filter on search results if active
                    const filterType = document.getElementById('filterType').value;
                    const checkedBoxes = document.querySelectorAll('.filterCheckbox:checked');
                    
                    let finalContacts = searchedContacts;
                    
                    if (filterType && checkedBoxes.length > 0) {{
                        const selectedValues = Array.from(checkedBoxes).map(cb => cb.value);
                        finalContacts = searchedContacts.filter(contact => 
                            contact[filterType] && selectedValues.includes(contact[filterType])
                        );
                        searchResults.textContent = `Found ${{finalContacts.length}} contact(s) matching "${{searchTerm}}" with selected filters`;
                    }} else {{
                        searchResults.textContent = `Found ${{finalContacts.length}} contact(s) matching "${{searchTerm}}"`;
                    }}
                    
                    searchResults.style.color = '#10b981';  // Green for success
                    displayContacts(finalContacts);
                    
                    // Hide searching indicator with fade-out
                    hideSearchingIndicator();
                }} else {{
                    const errorText = await response.text();
                    console.error('❌ Search failed:', response.status, errorText);
                    searchResults.textContent = `Search failed (HTTP ${{response.status}}). Check console for details.`;
                    searchResults.style.color = '#ef4444';  // Red for error
                    hideSearchingIndicator();
                }}
            }} catch (error) {{
                console.error('Search error:', error);
                searchResults.textContent = 'Search error: ' + error.message;
                searchResults.style.color = '#ef4444';  // Red for error
                hideSearchingIndicator();
            }}
        }}
        
        function showSearchingIndicator() {{
            const indicator = document.getElementById('searchingIndicator');
            indicator.classList.remove('hide');
            indicator.classList.add('show');
        }}
        
        function hideSearchingIndicator() {{
            const indicator = document.getElementById('searchingIndicator');
            indicator.classList.remove('show');
            indicator.classList.add('hide');
        }}
        
        function displayContacts(contacts) {{
            const tbody = document.getElementById('contactsBody');
            tbody.innerHTML = '';
            
            if (contacts && contacts.length > 0) {{
                contacts.forEach((contact, index) => {{
                const row = tbody.insertRow();
                row.setAttribute('data-email', contact.email);
                row.innerHTML = `
                    <td style="background: #dbeafe; font-weight: 600; color: #1e40af; border-right: 2px solid #60a5fa;">${{contact.email || ''}}</td>
                    <td contenteditable="true" data-field="first_name" class="editable-cell">${{contact.first_name || ''}}</td>
                    <td contenteditable="true" data-field="last_name" class="editable-cell">${{contact.last_name || ''}}</td>
                    <td contenteditable="true" data-field="title" class="editable-cell">${{contact.title || ''}}</td>
                    <td contenteditable="true" data-field="entity_type" class="editable-cell">${{contact.entity_type || ''}}</td>
                    <td contenteditable="true" data-field="state" class="editable-cell">${{contact.state || ''}}</td>
                    <td contenteditable="true" data-field="agency_name" class="editable-cell">${{contact.agency_name || ''}}</td>
                    <td contenteditable="true" data-field="sector" class="editable-cell">${{contact.sector || ''}}</td>
                    <td contenteditable="true" data-field="subsection" class="editable-cell">${{contact.subsection || ''}}</td>
                    <td contenteditable="true" data-field="phone" class="editable-cell">${{contact.phone || ''}}</td>
                    <td contenteditable="true" data-field="ms_isac_member" class="editable-cell yes-no-cell">${{contact.ms_isac_member || ''}}</td>
                    <td contenteditable="true" data-field="soc_call" class="editable-cell yes-no-cell">${{contact.soc_call || ''}}</td>
                    <td contenteditable="true" data-field="fusion_center" class="editable-cell yes-no-cell">${{contact.fusion_center || ''}}</td>
                    <td contenteditable="true" data-field="k12" class="editable-cell yes-no-cell">${{contact.k12 || ''}}</td>
                    <td contenteditable="true" data-field="water_wastewater" class="editable-cell yes-no-cell">${{contact.water_wastewater || ''}}</td>
                    <td contenteditable="true" data-field="weekly_rollup" class="editable-cell yes-no-cell">${{contact.weekly_rollup || ''}}</td>
                    <td contenteditable="true" data-field="alternate_email" class="editable-cell">${{contact.alternate_email || ''}}</td>
                    <td contenteditable="true" data-field="region" class="editable-cell">${{contact.region || ''}}</td>
                    <td style="position: sticky; right: 0; background: #f8fafc; border-left: 2px solid #cbd5e1; box-shadow: -2px 0 4px rgba(0,0,0,0.05);">
                        <button onclick="saveContactRow('${{contact.email}}')" class="btn-success" style="padding: 6px 12px; font-size: 12px; font-weight: 600;">💾 Save</button>
                    </td>
                `;
                
                // Add blur event to cells to detect changes
                const editableCells = row.querySelectorAll('.editable-cell');
                editableCells.forEach(cell => {{
                    cell.addEventListener('focus', function() {{
                        this.setAttribute('data-original', this.textContent);
                        this.style.background = '#fff3cd';
                    }});
                    cell.addEventListener('blur', function() {{
                        if (this.textContent !== this.getAttribute('data-original')) {{
                            this.style.background = '#fef3c7'; // Changed indicator
                            row.style.background = '#fffbeb';
                        }} else {{
                            this.style.background = '';
                        }}
                    }});
                }});
            }});
            }} else {{
                tbody.innerHTML = '<tr><td colspan="19" style="text-align: center; color: var(--gray-500); padding: 40px;">No contacts found. Add some contacts to get started!</td></tr>';
            }}
            
            // Update record count
            const recordCount = document.getElementById('recordCount');
            const startRecord = ((paginationState.currentPage - 1) * paginationState.pageSize) + 1;
            const endRecord = startRecord + contacts.length - 1;
            recordCount.textContent = `Showing records ${{startRecord}} - ${{endRecord}}`;
        }}
        
        async function saveContactRow(email) {{
            try {{
                // Find the row with this email
                const row = document.querySelector(`tr[data-email="${{email}}"]`);
                if (!row) {{
                    alert('Row not found');
                    return;
                }}
                
                // Get all editable cells in this row
                const cells = row.querySelectorAll('.editable-cell');
                
                // Build updated contact object
                const contactData = {{
                    email: email,
                    contact_id: email  // Use email as contact_id for lookup
                }};
                
                cells.forEach(cell => {{
                    const field = cell.getAttribute('data-field');
                    const value = cell.textContent.trim();
                    contactData[field] = value;
                }});
                
                console.log('Saving contact:', contactData);
                
                // Show saving state
                const button = row.querySelector('button');
                const originalText = button.textContent;
                button.textContent = '⏳ Saving...';
                button.disabled = true;
                
                // Send PUT request to update contact
                const response = await fetch(`${{API_URL}}/contacts`, {{
                    method: 'PUT',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(contactData)
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    button.textContent = '✅ Saved';
                    row.style.background = '#d1fae5'; // Success green
                    
                    // Reset cell backgrounds
                    cells.forEach(cell => {{
                        cell.style.background = '';
                    }});
                    
                    setTimeout(() => {{
                        button.textContent = originalText;
                        row.style.background = '';
                    }}, 2000);
                    
                    console.log('Contact saved successfully');
                }} else {{
                    throw new Error(result.error || 'Save failed');
                }}
                
            }} catch (error) {{
                console.error('Error saving contact:', error);
                alert('Error saving contact: ' + error.message);
                
                const row = document.querySelector(`tr[data-email="${{email}}"]`);
                if (row) {{
                    const button = row.querySelector('button');
                    button.textContent = '❌ Error';
                    setTimeout(() => {{
                        button.textContent = '💾 Save';
                    }}, 2000);
                }}
            }} finally {{
                const row = document.querySelector(`tr[data-email="${{email}}"]`);
                if (row) {{
                    const button = row.querySelector('button');
                    button.disabled = false;
                }}
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
                region: document.getElementById('editRegion').value
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
                    // loadGroupsFromDB(); // Disabled - groups feature removed
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
                region: document.getElementById('newRegion').value
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
                // loadGroupsFromDB(); // Disabled - groups feature removed
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
        
        // Global variable to track CSV upload cancellation
        let csvUploadCancelled = false;
        
        async function uploadCSV() {{
            const file = document.getElementById('csvFile').files[0];
            if (!file) return;
            
            csvUploadCancelled = false;
            
            console.log('Starting batch CSV upload...', file.name);
            
            // Show progress bar
            document.getElementById('csvUploadProgress').classList.remove('hidden');
            
            try {{
            const text = await file.text();
            const lines = text.split('\\n').filter(line => line.trim());
                
                console.log('Total lines in CSV:', lines.length);
            
            if (lines.length < 2) {{
                alert('CSV file must have at least a header row and one data row');
                    hideCSVProgress();
                return;
            }}
            
                // Better CSV parsing - handle quoted fields
                function parseCSVLine(line) {{
                    const result = [];
                    let current = '';
                    let inQuotes = false;
                    
                    for (let i = 0; i < line.length; i++) {{
                        const char = line[i];
                        
                        if (char === '"') {{
                            inQuotes = !inQuotes;
                        }} else if (char === ',' && !inQuotes) {{
                            result.push(current.trim());
                            current = '';
                        }} else {{
                            current += char;
                        }}
                    }}
                    result.push(current.trim());
                    return result;
                }}
                
                const headers = parseCSVLine(lines[0]).map(h => h.trim().toLowerCase());
                console.log('CSV Headers:', headers);
                
                // Parse all contacts first
                const allContacts = [];
            for (let i = 1; i < lines.length; i++) {{
                    const values = parseCSVLine(lines[i]);
                
                    if (values.length !== headers.length) {{
                        console.warn(`Row ${{i}}: Column count mismatch. Got ${{values.length}}, expected ${{headers.length}}`);
                        continue;
                    }}
                
                const contact = {{}};
                headers.forEach((header, index) => {{
                    // Map CSV headers to contact fields
                    const fieldMap = {{
                        'email': 'email',
                        'email_address': 'email',
                            'email address': 'email',
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
                        allContacts.push(contact);
                    }}
                }}
                
                console.log(`Parsed ${{allContacts.length}} valid contacts from CSV`);
                
                if (allContacts.length === 0) {{
                    alert('No valid contacts found in CSV file');
                    hideCSVProgress();
                    return;
                }}
                
                // Process in batches of 25 (DynamoDB batch limit)
                const BATCH_SIZE = 25;
                let imported = 0;
                let errors = 0;
                const totalBatches = Math.ceil(allContacts.length / BATCH_SIZE);
                const failedBatches = [];  // Track failed batches
                
                updateCSVProgress(0, allContacts.length, 'Starting import...');
                
                for (let batchNum = 0; batchNum < totalBatches; batchNum++) {{
                    // Check if cancelled
                    if (csvUploadCancelled) {{
                        console.log('CSV upload cancelled by user');
                        alert(`Import cancelled.\\nImported: ${{imported}} contacts\\nRemaining: ${{allContacts.length - imported}}`);
                        hideCSVProgress();
                        return;
                    }}
                    
                    const start = batchNum * BATCH_SIZE;
                    const end = Math.min(start + BATCH_SIZE, allContacts.length);
                    const batch = allContacts.slice(start, end);
                    
                    console.log(`Processing batch ${{batchNum + 1}}/${{totalBatches}}: contacts ${{start + 1}}-${{end}}`);
                    
                    try {{
                        const response = await fetch(`${{API_URL}}/contacts/batch`, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{ contacts: batch }})
                        }});
                        
                        if (response.ok) {{
                            const result = await response.json();
                            imported += result.imported || 0;
                            errors += result.unprocessed || 0;
                            
                            const percentage = Math.round((imported / allContacts.length) * 100);
                            updateCSVProgress(imported, allContacts.length, 
                                `Batch ${{batchNum + 1}}/${{totalBatches}} - Imported: ${{imported}}, Errors: ${{errors}}`);
                            
                            console.log(`✓ Batch ${{batchNum + 1}} complete: +${{result.imported}} imported, ${{result.unprocessed}} failed`);
                        }} else {{
                            const errorText = await response.text();
                            console.error(`Batch ${{batchNum + 1}} failed:`, response.status, errorText);
                            errors += batch.length;
                            
                            // Track failed batch details
                            failedBatches.push({{
                                batchNum: batchNum + 1,
                                rowStart: start + 1,
                                rowEnd: end,
                                contacts: batch,
                                error: `HTTP ${{response.status}}: ${{errorText}}`
                            }});
                            
                            updateCSVProgress(imported, allContacts.length, 
                                `Batch ${{batchNum + 1}}/${{totalBatches}} FAILED - Imported: ${{imported}}, Errors: ${{errors}}`);
                        }}
                    }} catch (e) {{
                        console.error(`Batch ${{batchNum + 1}} exception:`, e);
                        errors += batch.length;
                        
                        // Track failed batch details
                        failedBatches.push({{
                            batchNum: batchNum + 1,
                            rowStart: start + 1,
                            rowEnd: end,
                            contacts: batch,
                            error: e.message
                        }});
                        
                        updateCSVProgress(imported, allContacts.length, 
                            `Batch ${{batchNum + 1}}/${{totalBatches}} ERROR - Imported: ${{imported}}, Errors: ${{errors}}`);
                    }}
                    
                    // Small delay to avoid overwhelming the API
                    await new Promise(resolve => setTimeout(resolve, 100));
                }}
                
                console.log('Batch CSV Upload Complete. Imported:', imported, 'Errors:', errors);
                
                // Log failed batches details
                if (failedBatches.length > 0) {{
                    console.log('\\n=== FAILED BATCHES DETAILS ===');
                    failedBatches.forEach(fb => {{
                        console.log(`\\nBatch ${{fb.batchNum}} (Rows ${{fb.rowStart}}-${{fb.rowEnd}}):`);
                        console.log(`  Error: ${{fb.error}}`);
                        console.log(`  Failed contacts:`, fb.contacts);
                    }});
                    console.log('\\n=== END FAILED BATCHES ===\\n');
                    
                    // Create downloadable CSV of failed rows
                    window.failedContacts = failedBatches.flatMap(fb => fb.contacts);
                    console.log('To download failed contacts, run: downloadFailedContacts()');
                }}
                
                hideCSVProgress();
                
                let message = `CSV Import Complete!\\n\\nImported: ${{imported}} contacts\\nErrors: ${{errors}}\\n\\nProcessed ${{totalBatches}} batches of up to 25 contacts each.`;
                
                if (failedBatches.length > 0) {{
                    message += `\\n\\n⚠️ ${{failedBatches.length}} batches failed (${{errors}} contacts).`;
                    message += `\\n\\nTo see failed rows:\\n1. Open Console (F12)\\n2. Look for "FAILED BATCHES DETAILS"\\n3. Run: downloadFailedContacts()`;
                }}
                
                alert(message);
                
            loadContacts();
                // loadGroupsFromDB(); // Disabled - groups feature removed
                
            }} catch (error) {{
                console.error('CSV upload error:', error);
                hideCSVProgress();
                alert('Error during CSV import: ' + error.message);
            }}
        }}
        
        function updateCSVProgress(current, total, message) {{
            const percentage = Math.round((current / total) * 100);
            const progressBar = document.getElementById('csvProgressBar');
            const progressText = document.getElementById('csvProgressText');
            
            progressBar.style.width = percentage + '%';
            progressBar.textContent = percentage + '%';
            progressText.textContent = message + ` (${{current}} / ${{total}})`;
        }}
        
        function hideCSVProgress() {{
            document.getElementById('csvUploadProgress').classList.add('hidden');
            document.getElementById('csvProgressBar').style.width = '0%';
            document.getElementById('csvProgressBar').textContent = '';
            document.getElementById('csvProgressText').textContent = '';
        }}
        
        function cancelCSVUpload() {{
            if (confirm('Are you sure you want to cancel the import? Progress will be saved up to this point.')) {{
                csvUploadCancelled = true;
            }}
        }}
        
        function downloadFailedContacts() {{
            if (!window.failedContacts || window.failedContacts.length === 0) {{
                console.log('No failed contacts to download. Import completed successfully or no errors were tracked.');
                return;
            }}
            
            // Create CSV content
            const headers = ['email', 'first_name', 'last_name', 'title', 'entity_type', 'state', 'agency_name', 
                           'sector', 'subsection', 'phone', 'ms_isac_member', 'soc_call', 'fusion_center', 
                           'k12', 'water_wastewater', 'weekly_rollup', 'alternate_email', 'region', 'group'];
            
            let csvContent = headers.join(',') + '\\n';
            
            window.failedContacts.forEach(contact => {{
                const row = headers.map(header => {{
                    const value = contact[header] || '';
                    // Escape values that contain commas or quotes
                    if (value.includes(',') || value.includes('"')) {{
                        return '"' + value.replace(/"/g, '""') + '"';
                    }}
                    return value;
                }});
                csvContent += row.join(',') + '\\n';
            }});
            
            // Create download link
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            
            link.setAttribute('href', url);
            link.setAttribute('download', 'failed_contacts_' + new Date().toISOString().slice(0,10) + '.csv');
            link.style.visibility = 'hidden';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            console.log(`Downloaded ${{window.failedContacts.length}} failed contacts to CSV file`);
        }}
        
        async function loadCampaignFilterValues() {{
            const filterType = document.getElementById('campaignFilterType').value;
            const filterValueContainer = document.getElementById('campaignFilterValueContainer');
            const filterValueCheckboxes = document.getElementById('campaignFilterCheckboxes');
            
            if (!filterType) {{
                // No filter type selected - will use all contacts
                filterValueContainer.style.display = 'none';
                updateCampaignContactCount();
                return;
            }}
            
            // Handle Test Group as a special preset filter
            if (filterType === 'test_group') {{
                filterValueContainer.style.display = 'none';
                updateCampaignContactCount();
                return;
            }}
            
            // Auto-load contacts if not already loaded
            if (allContacts.length === 0) {{
                console.log('Contacts not loaded yet, loading now...');
                await loadContacts();
            }}
            
            // Get distinct values for selected field from loaded contacts
            const distinctValues = [...new Set(
                allContacts
                    .map(c => c[filterType])
                    .filter(v => v && v.trim() !== '')
            )].sort();
            
            console.log(`Campaign filter: Found ${{distinctValues.length}} distinct values for ${{filterType}}`);
            
            // Populate filter value checkboxes
            filterValueCheckboxes.innerHTML = '';
            distinctValues.forEach((value, index) => {{
                const checkboxDiv = document.createElement('div');
                checkboxDiv.style.marginBottom = '5px';
                checkboxDiv.innerHTML = `
                    <label style="display: flex; align-items: center; padding: 8px; cursor: pointer; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='#e0e7ff'" onmouseout="this.style.background='transparent'">
                        <input type="checkbox" class="campaignFilterCheckbox" value="${{value}}" onchange="updateCampaignContactCount()" style="margin-right: 10px; width: auto;">
                        <span>${{value}}</span>
                    </label>
                `;
                filterValueCheckboxes.appendChild(checkboxDiv);
            }});
            
            filterValueContainer.style.display = 'block';
            updateCampaignContactCount();
        }}
        
        function updateCampaignContactCount() {{
            const filterType = document.getElementById('campaignFilterType').value;
            const checkedBoxes = document.querySelectorAll('.campaignFilterCheckbox:checked');
            const filterCount = document.getElementById('campaignFilterCount');
            
            let targetContacts = allContacts;
            
            // Handle Test Group special filter
            if (filterType === 'test_group') {{
                targetContacts = allContacts.filter(contact => 
                    contact.group && contact.group.toLowerCase() === 'test'
                );
                filterCount.textContent = `${{targetContacts.length}} contact(s) in Test Group will receive this campaign`;
                filterCount.style.color = '#f59e0b';
                filterCount.style.fontWeight = '600';
                return;
            }}
            
            // Apply filter if selected
            if (filterType && checkedBoxes.length > 0) {{
                const selectedValues = Array.from(checkedBoxes).map(cb => cb.value);
                targetContacts = allContacts.filter(contact => 
                    contact[filterType] && selectedValues.includes(contact[filterType])
                );
                filterCount.textContent = `${{targetContacts.length}} contact(s) will receive this campaign (${{checkedBoxes.length}} filter(s) selected)`;
                filterCount.style.color = '#6b7280';
                filterCount.style.fontWeight = 'normal';
            }} else {{
                filterCount.textContent = `${{allContacts.length}} contact(s) will receive this campaign (All Contacts)`;
                filterCount.style.color = '#6b7280';
                filterCount.style.fontWeight = 'normal';
            }}
        }}
        
        function selectAllCampaignFilters() {{
            const checkboxes = document.querySelectorAll('.campaignFilterCheckbox');
            checkboxes.forEach(cb => cb.checked = true);
            updateCampaignContactCount();
        }}
        
        function clearAllCampaignFilters() {{
            const checkboxes = document.querySelectorAll('.campaignFilterCheckbox');
            checkboxes.forEach(cb => cb.checked = false);
            updateCampaignContactCount();
        }}
        
        // Attachment handling
        let campaignAttachments = [];
        const MAX_ATTACHMENT_SIZE = 40 * 1024 * 1024; // 40 MB in bytes (AWS SES v2 limit)
        
        async function handleAttachmentUpload() {{
            const fileInput = document.getElementById('attachmentFiles');
            const files = Array.from(fileInput.files);
            
            if (files.length === 0) return;
            
            // Calculate total size
            let totalSize = campaignAttachments.reduce((sum, att) => sum + att.size, 0);
            for (const file of files) {{
                totalSize += file.size;
            }}
            
            if (totalSize > MAX_ATTACHMENT_SIZE) {{
                alert(`Total attachment size exceeds 40 MB limit.\\nCurrent total: ${{(totalSize / 1024 / 1024).toFixed(2)}} MB\\nPlease remove some files.`);
                fileInput.value = ''; // Clear selection
                return;
            }}
            
            // Upload files to S3
            for (const file of files) {{
                try {{
                    console.log(`Uploading attachment: ${{file.name}} (${{(file.size / 1024).toFixed(1)}} KB)`);
                    const s3Key = await uploadAttachmentToS3(file);
                    
                    campaignAttachments.push({{
                        filename: file.name,
                        size: file.size,
                        type: file.type,
                        s3_key: s3Key
                    }});
                    
                    console.log(`✓ Uploaded: ${{file.name}} to S3 as ${{s3Key}}`);
                }} catch (error) {{
                    console.error(`Error uploading ${{file.name}}:`, error);
                    let errorMsg = `Failed to upload ${{file.name}}: ${{error.message}}`;
                    
                    if (error.message.includes('404')) {{
                        errorMsg += '\\n\\nThe /upload-attachment endpoint is not configured.\\nPlease run: python add_attachment_endpoint.py';
                    }} else if (error.message.includes('403')) {{
                        errorMsg += '\\n\\nLambda function does not have S3 permissions.\\nCheck IAM role permissions for S3 bucket access.';
                    }} else if (error.message.includes('500')) {{
                        errorMsg += '\\n\\nServer error. Check Lambda CloudWatch logs for details.';
                    }}
                    
                    alert(errorMsg);
                    fileInput.value = ''; // Clear input on error
                    return; // Stop processing more files
                }}
            }}
            
            displayAttachments();
            fileInput.value = ''; // Clear input
        }}
        
        async function uploadAttachmentToS3(file) {{
            const timestamp = Date.now();
            const randomStr = Math.random().toString(36).substring(7);
            const s3Key = `campaign-attachments/${{timestamp}}-${{randomStr}}-${{file.name}}`;
            
            // Convert file to base64
            const base64Data = await fileToBase64(file);
            
            // Upload to S3 via Lambda
            const response = await fetch(`${{API_URL}}/upload-attachment`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    filename: file.name,
                    content_type: file.type,
                    s3_key: s3Key,
                    data: base64Data
                }})
            }});
            
            if (!response.ok) {{
                throw new Error(`Upload failed: ${{response.status}}`);
            }}
            
            const result = await response.json();
            return result.s3_key;
        }}
        
        function fileToBase64(file) {{
            return new Promise((resolve, reject) => {{
                const reader = new FileReader();
                reader.onload = () => {{
                    const base64 = reader.result.split(',')[1];
                    resolve(base64);
                }};
                reader.onerror = reject;
                reader.readAsDataURL(file);
            }});
        }}
        
        function displayAttachments() {{
            const container = document.getElementById('attachmentsList');
            const sizeDiv = document.getElementById('attachmentSize');
            
            if (campaignAttachments.length === 0) {{
                container.innerHTML = '';
                sizeDiv.textContent = '';
                return;
            }}
            
            const totalSize = campaignAttachments.reduce((sum, att) => sum + att.size, 0);
            const totalSizeMB = (totalSize / 1024 / 1024).toFixed(2);
            
            container.innerHTML = campaignAttachments.map((att, index) => `
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px; background: #f3f4f6; border-radius: 4px; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div>
                            <div style="font-weight: 500;">📎 ${{att.filename}}</div>
                            <div style="font-size: 12px; color: #6b7280;">💾 ${{(att.size / 1024).toFixed(1)}} KB</div>
                        </div>
                    </div>
                    <button onclick="removeAttachment(${{index}})" style="background: #ef4444; padding: 6px 12px; font-size: 14px;">🗑️ Remove</button>
                </div>
            `).join('');
            
            sizeDiv.innerHTML = `<strong>📊 Total size:</strong> ${{totalSizeMB}} MB / 40 MB ${{totalSize > MAX_ATTACHMENT_SIZE ? '<span style="color: #ef4444;">❌ Exceeds limit!</span>' : '<span style="color: #10b981;">✅ OK</span>'}}`;
        }}
        
        function removeAttachment(index) {{
            campaignAttachments.splice(index, 1);
            displayAttachments();
        }}
        
        async function sendCampaign() {{
            // Check form availability first
            if (!checkFormAvailability()) {{
                alert('Form is currently unavailable. Please refresh the page and try again.');
                return;
            }}
            
            const button = event.target;
            const originalText = button.textContent;
            
            try {{
                // Show loading state
                button.textContent = 'Sending Campaign...';
                button.classList.add('loading');
                button.disabled = true;
                
            // Get target contacts based on selected filter
            const campaignFilterType = document.getElementById('campaignFilterType').value;
            const campaignCheckedBoxes = document.querySelectorAll('.campaignFilterCheckbox:checked');
            
            let targetContacts = allContacts;
            let filterDescription = 'All Contacts';
            
            // Auto-load contacts if not already loaded
            if (allContacts.length === 0) {{
                throw new Error('Please load contacts first by going to the Contacts tab.');
            }}
            
            // Handle Test Group special filter
            if (campaignFilterType === 'test_group') {{
                targetContacts = allContacts.filter(contact => 
                    contact.group && contact.group.toLowerCase() === 'test'
                );
                filterDescription = 'Test Group (group = Test)';
            }}
            // Apply filter if checkboxes are selected
            else if (campaignFilterType && campaignCheckedBoxes.length > 0) {{
                const selectedValues = Array.from(campaignCheckedBoxes).map(cb => cb.value);
                targetContacts = allContacts.filter(contact => 
                    contact[campaignFilterType] && selectedValues.includes(contact[campaignFilterType])
                );
                filterDescription = `${{campaignFilterType}}: ${{selectedValues.join(', ')}}`;
            }}
            
            if (targetContacts.length === 0) {{
                throw new Error('No contacts match the selected filters. Please adjust your filter or select "All Contacts".');
            }}
            
            console.log(`Campaign will be sent to ${{targetContacts.length}} contacts (${{filterDescription}})`);
            
            // Get content from Quill editor
            const emailBody = quillEditor.root.innerHTML;
            
            // Get user name from form
            const userName = document.getElementById('userName').value.trim() || 'Web User';
            
            const campaign = {{
                campaign_name: document.getElementById('campaignName').value,
                subject: document.getElementById('subject').value,
                body: emailBody,
                launched_by: userName,  // Send user identity to backend
                filter_type: campaignFilterType || null,
                filter_values: campaignFilterType && campaignCheckedBoxes.length > 0 
                    ? Array.from(campaignCheckedBoxes).map(cb => cb.value)
                    : null,
                filter_description: filterDescription,
                target_contacts: targetContacts.map(c => c.email),  // Send email list to backend
                attachments: campaignAttachments  // Include attachments
            }};
                
                // Validate required fields
                if (!campaign.campaign_name || !campaign.subject || !campaign.body) {{
                    throw new Error('Please fill in all required fields');
                }}
                
                // Validate attachment size
                const totalAttachmentSize = campaignAttachments.reduce((sum, att) => sum + att.size, 0);
                if (totalAttachmentSize > MAX_ATTACHMENT_SIZE) {{
                    throw new Error(`Attachments exceed 40 MB limit (${{(totalAttachmentSize / 1024 / 1024).toFixed(2)}} MB)`);
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
                        <p style="margin: 5px 0 0 0; color: var(--gray-700);"><strong>Target Contacts:</strong> ${{filterDescription}}</p>
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
                console.log('Loading config from:', `${{API_URL}}/config`);
                const response = await fetch(`${{API_URL}}/config`);
                console.log('Config response status:', response.status);
                
                if (response.ok) {{
                    const result = await response.json();
                    console.log('Config result:', result);
                    const config = result.config;
                    console.log('Config data:', config);
                    
                    if (config && config.aws_region) {{
                        document.getElementById('awsRegion').value = config.aws_region;
                        console.log('✅ AWS Region loaded from DynamoDB:', config.aws_region);
                    }}
                    
                    if (config && config.from_email) {{
                        document.getElementById('fromEmail').value = config.from_email;
                        console.log('✅ From Email loaded from DynamoDB:', config.from_email);
                    }} else {{
                        console.log('⚠️ No from_email found in config - using defaults');
                    }}
                    
                    // emails_per_minute field removed
                }} else if (response.status === 404) {{
                    console.log('ℹ️ No email configuration found in DynamoDB - using defaults');
                    console.log('You can save configuration in the Email Config tab');
                }} else {{
                    console.log('⚠️ Config response not OK:', response.status);
                    // alert('Config API error: ' + response.status);
                }}
            }} catch (e) {{
                console.error('Error loading config:', e);
            }}
        }}
        
        // User identity management (browser localStorage)
        function saveUserName() {{
            const userName = document.getElementById('userName').value.trim();
            if (userName) {{
                localStorage.setItem('emailCampaignUserName', userName);
                console.log('User name saved:', userName);
            }}
        }}
        
        function loadUserName() {{
            const savedName = localStorage.getItem('emailCampaignUserName');
            if (savedName) {{
                document.getElementById('userName').value = savedName;
                console.log('User name loaded from browser:', savedName);
            }}
        }}
        
        window.onload = () => {{
            // Initialize UI and load configuration
            loadConfig();
            // loadGroupsFromDB();  // Disabled - groups feature removed
            loadUserName();  // Load saved user name from browser
            console.log('Web UI loaded successfully');
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
                'updated_at': datetime.now().isoformat()
            }
        
        # Add service-specific fields
        if body.get('email_service') == 'ses':
            item.update({
                'aws_region': str(body.get('aws_region', 'us-gov-west-1'))
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
            update_expression = "SET email_service = :service, from_email = :email, updated_at = :updated"
            expression_values = {
                ':service': str(body.get('email_service', 'ses')),
                ':email': str(body.get('from_email', '')),
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

def get_contacts(headers, event=None):
    """Get contacts with pagination support"""
    try:
        # Get pagination parameters from query string
        query_params = None
        if event:
            query_params = event.get('queryStringParameters')
        
        # Handle None query params
        if query_params is None:
            query_params = {}
            
        limit = int(query_params.get('limit', 25)) if query_params.get('limit') else 25
        last_key_str = query_params.get('lastKey') if query_params.get('lastKey') else None
        
        # Build scan parameters
        scan_params = {'Limit': limit}
        
        # Add ExclusiveStartKey if provided
        if last_key_str:
            try:
                import json as json_lib
                last_key = json_lib.loads(last_key_str)
                scan_params['ExclusiveStartKey'] = last_key
            except:
                pass  # Invalid lastKey, ignore
        
        # Scan contacts table with pagination
        response = contacts_table.scan(**scan_params)
        
        contacts = []
        for item in response.get('Items', []):
            contact = {}
            for key, value in item.items():
                if isinstance(value, Decimal):
                    contact[key] = int(value)
                else:
                    contact[key] = value
            contacts.append(contact)
        
        # Build response with pagination info
        result = {
            'contacts': contacts,
            'count': len(contacts)
        }
        
        # Include lastEvaluatedKey if there are more items
        if 'LastEvaluatedKey' in response:
            # Convert Decimal types in lastEvaluatedKey
            last_key = {}
            for key, value in response['LastEvaluatedKey'].items():
                if isinstance(value, Decimal):
                    last_key[key] = int(value) if value % 1 == 0 else float(value)
                else:
                    last_key[key] = value
            result['lastEvaluatedKey'] = last_key
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
    
    except Exception as e:
        print(f"Error in get_contacts: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def search_contacts(body, headers):
    """Search contacts by name in DynamoDB"""
    try:
        search_term = body.get('search_term', '').lower()
        
        if not search_term:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Search term required'})}
        
        # Scan contacts table (DynamoDB doesn't support LIKE, so we need to scan and filter)
        response = contacts_table.scan()
        all_contacts = response.get('Items', [])
        
        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            response = contacts_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_contacts.extend(response.get('Items', []))
        
        # Filter contacts by name
        matched_contacts = []
        for contact in all_contacts:
            first_name = (contact.get('first_name') or '').lower()
            last_name = (contact.get('last_name') or '').lower()
            full_name = f"{first_name} {last_name}".strip()
            
            if (search_term in first_name or 
                search_term in last_name or 
                search_term in full_name):
                # Convert Decimal types to appropriate Python types
                clean_contact = {}
                for key, value in contact.items():
                    if isinstance(value, Decimal):
                        clean_contact[key] = int(value) if value % 1 == 0 else float(value)
                    else:
                        clean_contact[key] = value
                matched_contacts.append(clean_contact)
        
        print(f"Name search '{search_term}': found {len(matched_contacts)} contacts")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'contacts': matched_contacts,
                'count': len(matched_contacts),
                'search_term': search_term
            })
        }
    except Exception as e:
        print(f"Error in search_contacts: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_groups(headers):
    """Get distinct groups from contacts - optimized for large datasets"""
    try:
        groups = set()
        
        # Scan with ProjectionExpression to only get the 'group' field
        response = contacts_table.scan(
            ProjectionExpression='#grp',
            ExpressionAttributeNames={'#grp': 'group'}
        )
        
        # Add groups from first batch
        for item in response.get('Items', []):
            if 'group' in item and item['group']:
                groups.add(item['group'])
        
        # Handle pagination for large datasets
        while 'LastEvaluatedKey' in response:
            response = contacts_table.scan(
                ProjectionExpression='#grp',
                ExpressionAttributeNames={'#grp': 'group'},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            for item in response.get('Items', []):
                if 'group' in item and item['group']:
                    groups.add(item['group'])
        
        # Convert to sorted list
        groups_list = sorted(list(groups))
        
        return {
            'statusCode': 200, 
            'headers': headers, 
            'body': json.dumps({'groups': groups_list})
        }
    except Exception as e:
        return {
            'statusCode': 500, 
            'headers': headers, 
            'body': json.dumps({'error': str(e)})
        }

def upload_attachment(body, headers):
    """Upload attachment to S3 bucket"""
    try:
        print(f"Upload attachment request received")
        
        filename = body.get('filename')
        content_type = body.get('content_type', 'application/octet-stream')
        s3_key = body.get('s3_key')
        data = body.get('data')  # Base64 encoded file data
        
        print(f"Filename: {filename}, ContentType: {content_type}, S3Key: {s3_key}")
        print(f"Data length: {len(data) if data else 0} characters")
        
        if not all([filename, s3_key, data]):
            missing = []
            if not filename: missing.append('filename')
            if not s3_key: missing.append('s3_key')
            if not data: missing.append('data')
            error_msg = f'Missing required fields: {", ".join(missing)}'
            print(f"ERROR: {error_msg}")
            return {
                'statusCode': 400, 
                'headers': headers, 
                'body': json.dumps({'error': error_msg})
            }
        
        # Decode base64 data
        print(f"Decoding base64 data...")
        try:
            file_data = base64.b64decode(data)
            print(f"Decoded file size: {len(file_data)} bytes")
        except Exception as decode_error:
            error_msg = f"Base64 decode error: {str(decode_error)}"
            print(f"ERROR: {error_msg}")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': error_msg})
            }
        
        # Upload to S3
        print(f"Uploading to S3 bucket: {ATTACHMENTS_BUCKET}, key: {s3_key}")
        try:
            s3_client.put_object(
                Bucket=ATTACHMENTS_BUCKET,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata={
                    'original_filename': filename
                }
            )
            print(f"✓ Successfully uploaded: {filename} to s3://{ATTACHMENTS_BUCKET}/{s3_key}")
        except Exception as s3_error:
            error_msg = f"S3 upload error: {str(s3_error)}"
            print(f"ERROR: {error_msg}")
            # Check for specific S3 errors
            if 'AccessDenied' in str(s3_error):
                error_msg = f"S3 Access Denied: Lambda role does not have permission to write to bucket '{ATTACHMENTS_BUCKET}'. Add s3:PutObject permission."
            elif 'NoSuchBucket' in str(s3_error):
                error_msg = f"S3 bucket '{ATTACHMENTS_BUCKET}' does not exist or is not accessible."
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': error_msg})
            }
        
        return {
            'statusCode': 200, 
            'headers': headers, 
            'body': json.dumps({
                'success': True,
                's3_key': s3_key,
                'bucket': ATTACHMENTS_BUCKET,
                'size': len(file_data)
            })
        }
    except Exception as e:
        error_msg = f"Unexpected error uploading attachment: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500, 
            'headers': headers, 
            'body': json.dumps({'error': error_msg})
        }

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

def batch_add_contacts(body, headers):
    """Batch add contacts - up to 25 at a time (DynamoDB limit)"""
    try:
        contacts = body.get('contacts', [])
        
        if not contacts:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No contacts provided'})}
        
        if len(contacts) > 25:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Maximum 25 contacts per batch'})}
        
        # Prepare batch write requests
        dynamodb_client = boto3.client('dynamodb', region_name='us-gov-west-1')
        
        request_items = []
        for contact in contacts:
            if not contact.get('email'):
                continue
                
            item = {
                'email': {'S': contact['email']},
                'first_name': {'S': contact.get('first_name', '')},
                'last_name': {'S': contact.get('last_name', '')},
                'title': {'S': contact.get('title', '')},
                'entity_type': {'S': contact.get('entity_type', '')},
                'state': {'S': contact.get('state', '')},
                'agency_name': {'S': contact.get('agency_name', '')},
                'sector': {'S': contact.get('sector', '')},
                'subsection': {'S': contact.get('subsection', '')},
                'phone': {'S': contact.get('phone', '')},
                'ms_isac_member': {'S': contact.get('ms_isac_member', '')},
                'soc_call': {'S': contact.get('soc_call', '')},
                'fusion_center': {'S': contact.get('fusion_center', '')},
                'k12': {'S': contact.get('k12', '')},
                'water_wastewater': {'S': contact.get('water_wastewater', '')},
                'weekly_rollup': {'S': contact.get('weekly_rollup', '')},
                'alternate_email': {'S': contact.get('alternate_email', '')},
                'region': {'S': contact.get('region', '')},
                'group': {'S': contact.get('group', '')},
                'created_at': {'S': datetime.now().isoformat()}
            }
            
            request_items.append({'PutRequest': {'Item': item}})
        
        if not request_items:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No valid contacts with email addresses'})}
        
        # Execute batch write
        response = dynamodb_client.batch_write_item(
            RequestItems={
                'EmailContacts': request_items
            }
        )
        
        # Check for unprocessed items
        unprocessed = response.get('UnprocessedItems', {})
        unprocessed_count = len(unprocessed.get('EmailContacts', []))
        
        return {
            'statusCode': 200, 
            'headers': headers, 
            'body': json.dumps({
                'success': True, 
                'imported': len(request_items) - unprocessed_count,
                'unprocessed': unprocessed_count
            })
        }
    except Exception as e:
        print(f"Batch import error: {str(e)}")
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
        expr_names = {}
        update_parts = []
        
        for field in contact_fields:
            if field in body:
                # Use ExpressionAttributeNames to avoid reserved keyword issues
                field_placeholder = f"#{field}"
                value_placeholder = f":{field}"
                update_parts.append(f"{field_placeholder} = {value_placeholder}")
                expr_names[field_placeholder] = field
                expr_values[value_placeholder] = body[field]
        
        if not update_parts:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No fields to update'})}
        
        update_expr += ", ".join(update_parts)
        
        contacts_table.update_item(
            Key={'email': email},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
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

def send_campaign(body, headers, event=None):
    """Send email campaign by saving to DynamoDB and queuing contacts to SQS"""
    try:
        # Get email configuration
        config_response = email_config_table.get_item(Key={'config_id': 'default'})
        if 'Item' not in config_response:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Email configuration not found'})}
        
        config = config_response['Item']
        
        # Get target contacts from frontend filter
        target_contact_emails = body.get('target_contacts', [])
        filter_description = body.get('filter_description', 'All Contacts')
        
        if not target_contact_emails:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No target contacts specified'})}
        
        # Retrieve full contact records for the target emails
        contacts = []
        for email in target_contact_emails:
            try:
                contact_response = contacts_table.get_item(Key={'email': email})
                if 'Item' in contact_response:
                    contacts.append(contact_response['Item'])
            except Exception as e:
                print(f"Error retrieving contact {email}: {str(e)}")
        
        print(f"Campaign targeting {len(contacts)} contacts ({filter_description})")
        
        if not contacts:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No valid contacts found'})}
        
        campaign_id = f"campaign_{int(datetime.now().timestamp())}"
        
        # Get attachments
        attachments = body.get('attachments', [])
        
        # Get user info from request context or body
        launched_by = body.get('launched_by', 'Web User')
        if 'requestContext' in event:
            # Try to get user from API Gateway context
            identity = event['requestContext'].get('identity', {})
            source_ip = identity.get('sourceIp', 'Unknown')
            user_agent = identity.get('userAgent', 'Unknown')
            launched_by = f"{launched_by} (IP: {source_ip})"
        
        # Save complete campaign data to DynamoDB
        print(f"Saving campaign {campaign_id} to DynamoDB with {len(attachments)} attachments")
        campaign_item = {
                'campaign_id': campaign_id,
                'campaign_name': body.get('campaign_name', 'Bulk Campaign'),
                'subject': body.get('subject', ''),
                'body': body.get('body', ''),
                'from_email': config.get('from_email', ''),
                'status': 'queued',
                'total_contacts': len(contacts),
                'queued_count': 0,
                'sent_count': 0,
                'failed_count': 0,
            'created_at': datetime.now().isoformat(),
            'sent_at': None,  # Will be updated when emails are actually sent
            'launched_by': launched_by
        }
        
        # Add filter values if present (keep for tracking which contacts were targeted)
        if body.get('filter_values'):
            campaign_item['filter_values'] = body.get('filter_values', [])
        
        # Add attachments if present
        if attachments:
            campaign_item['attachments'] = attachments
        
        # Store recipient email list for tracking
        campaign_item['target_contacts'] = target_contact_emails
        
        campaigns_table.put_item(Item=campaign_item)
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
                'filter_description': filter_description,
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
    return content