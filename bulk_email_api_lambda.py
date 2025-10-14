import json
import boto3
from botocore.config import Config
import smtplib
import ssl
import time
import os
import traceback
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

# S3 client with Signature Version 4 (required for KMS-encrypted buckets)
s3_config = Config(signature_version='s3v4', region_name='us-gov-west-1')
s3_client = boto3.client('s3', region_name='us-gov-west-1', config=s3_config)

# S3 bucket for attachments
ATTACHMENTS_BUCKET = 'jcdc-ses-contact-list'

# Custom API URL configuration
# To use your own domain instead of the AWS API Gateway URL:
# 1. Set Lambda environment variable: CUSTOM_API_URL = https://yourdomain.com
# 2. If using API Gateway Custom Domain, set it to: https://api.yourdomain.com/prod
# 3. Make sure your custom domain routes to this Lambda function
# If not set, it will automatically use the API Gateway URL
CUSTOM_API_URL = os.environ.get('CUSTOM_API_URL', None)


# Helper function to convert DynamoDB Decimal types to JSON-serializable types
def convert_decimals(obj):
    """
    Recursively convert Decimal objects to int or float for JSON serialization.
    This handles nested dictionaries, lists, and sets.
    """
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, set):
        # JSON doesn't support sets; convert to list
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, tuple):
        # Tuples are converted to lists for JSON compatibility
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def _json_default(o):
    """Fallback JSON serializer for unsupported types like Decimal and set."""
    if isinstance(o, Decimal):
        return int(o) if o % 1 == 0 else float(o)
    if isinstance(o, set):
        return list(o)
    return str(o)


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

##COGNITO_CONFIG = load_cognito_config()

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
        
        # DEBUG: Log incoming request details
        print(f"📨 Incoming request: {method} {path}")
        print(f"   resource: {event.get('resource')}")
        print(f"   path: {event.get('path')}")
        print(f"   httpMethod: {event.get('httpMethod')}")
        if event.get('body'):
            body_preview = event.get('body', '')[:200]
            print(f"   body preview: {body_preview}...")
        
        # Serve web UI for GET requests to root
        if method == 'GET' and path == '/':
            print("   → Serving Web UI")
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
        elif path == '/contacts/distinct' and method == 'GET':
            return get_distinct_values(headers, event)
        elif path == '/contacts/filter' and method == 'POST':
            return filter_contacts(body, headers)
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
            print("   → Calling upload_attachment()")
            return upload_attachment(body, headers)
        elif path == '/campaign' and method == 'POST':
            print("   → Calling send_campaign()")
            return send_campaign(body, headers, event)
        elif path == '/campaign/{campaign_id}' and method == 'GET':
            campaign_id = event['pathParameters']['campaign_id']
            return get_campaign_status(campaign_id, headers)
        elif path == '/attachment-url' and method == 'GET':
            print("   → Calling get_attachment_url()")
            return get_attachment_url(event, headers)
        elif path == '/campaigns' and method == 'GET':
            print("   → Calling get_campaigns()")
            return get_campaigns(headers, event)
        elif path == '/campaign-viewed' and method == 'POST':
            print("   → Calling mark_campaign_viewed()")
            return mark_campaign_viewed(body, headers)
        else:
            print(f"   → Route not found: {method} {path}")
            print("   Available routes: /config, /contacts, /campaign, /upload-attachment, /campaigns, etc.")
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': f'Route not found: {method} {path}'})}
            
    except Exception as e:
        print(f"❌ Lambda handler exception: {str(e)}")
        import traceback
        traceback.print_exc()
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
    
    <!-- Favicon to prevent 403 error -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📧</text></svg>">
    
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Google Fonts for Outlook-optimized selection -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Open+Sans:wght@300;400;600;700&family=Lato:wght@300;400;700&family=Montserrat:wght@300;400;500;600;700&family=Poppins:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=Source+Sans+Pro:wght@300;400;600;700&family=Nunito:wght@300;400;600;700&family=Raleway:wght@300;400;500;600;700&family=Ubuntu:wght@300;400;500;700&family=Playfair+Display:wght@400;500;600;700&family=Merriweather:wght@300;400;700&family=Oswald:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Quill Rich Text Editor -->
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <script src="https://cdn.quilljs.com/1.3.6/quill.js"></script>
    
    <!-- Quill Image Resize Module -->
    <script src="https://cdn.jsdelivr.net/npm/quill-image-resize-module@3.0.0/image-resize.min.js"></script>
    
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
        
        function performHistorySearch() {{
            loadCampaignHistory(null);
        }}

        /* Campaign History Table Styles */
        #historyTable tbody tr:nth-child(odd) {{
            background: #ffffff;
        }}
        #historyTable tbody tr:nth-child(even) {{
            background: #f9fafb;
        }}
        #historyTable tbody tr:hover {{
            background: #f3f4f6;
        }}
        #historyTable td {{
            color: #1f2937;
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
            background: white;
            cursor: pointer; 
            text-align: center; 
            border-radius: 8px; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
            font-weight: 600; 
            color: #1e40af;
            position: relative;
            overflow: hidden;
            z-index: 10;
            pointer-events: auto;
            user-select: none;
            border: 2px solid #3b82f6;
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
        }}
        .tab:hover {{ 
            background: linear-gradient(135deg, #dbeafe, #bfdbfe); 
            color: #1e40af;
            transform: translateY(-1px);
            border-color: #2563eb;
            box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
        }}
        .tab.active {{ 
            background: linear-gradient(135deg, #1e40af, #1e3a8a); 
            color: white; 
            box-shadow: 0 6px 12px rgba(30, 64, 175, 0.4);
            transform: translateY(-2px);
            border-color: #1e3a8a;
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
        
        /* Outlook-Optimized Font Definitions */
        /* Core Outlook-safe system fonts */
        .ql-font-arial {{ font-family: Arial, sans-serif; }}
        .ql-font-calibri {{ font-family: Calibri, Arial, sans-serif; }}
        .ql-font-cambria {{ font-family: Cambria, Georgia, serif; }}
        .ql-font-georgia {{ font-family: Georgia, serif; }}
        .ql-font-times-new-roman {{ font-family: "Times New Roman", serif; }}
        .ql-font-courier-new {{ font-family: "Courier New", monospace; }}
        .ql-font-verdana {{ font-family: Verdana, Arial, sans-serif; }}
        .ql-font-tahoma {{ font-family: Tahoma, Arial, sans-serif; }}
        .ql-font-trebuchet-ms {{ font-family: "Trebuchet MS", Arial, sans-serif; }}
        .ql-font-helvetica {{ font-family: Helvetica, Arial, sans-serif; }}
        
        /* Limited web fonts with strong Outlook fallbacks */
        .ql-font-segoe-ui {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; }}
        .ql-font-open-sans {{ font-family: "Open Sans", Arial, sans-serif; }}
        .ql-font-roboto {{ font-family: "Roboto", Arial, sans-serif; }}
        
        /* Outlook-Optimized Font Dropdown Styling */
        .ql-picker.ql-font .ql-picker-label::before,
        .ql-picker.ql-font .ql-picker-item::before {{
            content: 'Font Family';
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=arial]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=arial]::before {{
            content: 'Arial';
            font-family: Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=calibri]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=calibri]::before {{
            content: 'Calibri';
            font-family: Calibri, Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=cambria]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=cambria]::before {{
            content: 'Cambria';
            font-family: Cambria, Georgia, serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=georgia]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=georgia]::before {{
            content: 'Georgia';
            font-family: Georgia, serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=times-new-roman]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=times-new-roman]::before {{
            content: 'Times New Roman';
            font-family: "Times New Roman", serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=courier-new]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=courier-new]::before {{
            content: 'Courier New';
            font-family: "Courier New", monospace;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=verdana]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=verdana]::before {{
            content: 'Verdana';
            font-family: Verdana, Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=tahoma]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=tahoma]::before {{
            content: 'Tahoma';
            font-family: Tahoma, Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=trebuchet-ms]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=trebuchet-ms]::before {{
            content: 'Trebuchet MS';
            font-family: "Trebuchet MS", Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=helvetica]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=helvetica]::before {{
            content: 'Helvetica';
            font-family: Helvetica, Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=segoe-ui]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=segoe-ui]::before {{
            content: 'Segoe UI';
            font-family: "Segoe UI", Tahoma, Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=open-sans]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=open-sans]::before {{
            content: 'Open Sans';
            font-family: "Open Sans", Arial, sans-serif;
        }}
        .ql-picker.ql-font .ql-picker-label[data-value=roboto]::before,
        .ql-picker.ql-font .ql-picker-item[data-value=roboto]::before {{
            content: 'Roboto';
            font-family: "Roboto", Arial, sans-serif;
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
        
        /* Image Resize Module Styling */
        .ql-editor img {{
            cursor: pointer;
            max-width: 100%;
            height: auto !important;  /* Allow height changes */
            max-height: none !important;  /* Remove max-height restriction */
        }}
        .ql-editor img:hover {{
            outline: 2px solid #3b82f6;
        }}
        /* Resize handle styles */
        .image-resize-handle {{
            background: white !important;
            border: 2px solid #3b82f6 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
            width: 12px !important;
            height: 12px !important;
            cursor: nwse-resize !important;
        }}
        .image-resize-overlay {{
            border: 2px dashed #3b82f6 !important;
        }}
        /* Ensure image container doesn't restrict height */
        .ql-editor .image-resizing {{
            max-height: none !important;
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
        
        /* Filter Type Button Styling */
        .filter-type-btn {{
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }}
        .filter-type-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .filter-type-btn:active {{
            transform: translateY(0);
        }}
        
        /* Available Value Button Styling */
        .available-value-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(99, 102, 241, 0.2);
        }}
        
        /* Filter Tags Animation */
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateX(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}
        
        #selectedValuesTags > div {{
            animation: slideIn 0.3s ease;
        }}
        
        /* ============================================
           TOAST NOTIFICATION SYSTEM
           ============================================ */
        #toastContainer {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 400px;
        }}
        
        .toast {{
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15), 0 0 1px rgba(0, 0, 0, 0.05);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: toastSlideIn 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
            backdrop-filter: blur(10px);
            color: white;
            font-size: 14px;
            font-weight: 500;
            min-width: 300px;
            position: relative;
            overflow: hidden;
        }}
        
        .toast::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: currentColor;
        }}
        
        .toast-success {{
            background: linear-gradient(135deg, #10b981, #059669);
        }}
        
        .toast-error {{
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }}
        
        .toast-warning {{
            background: linear-gradient(135deg, #f59e0b, #d97706);
        }}
        
        .toast-info {{
            background: linear-gradient(135deg, #3b82f6, #2563eb);
        }}
        
        .toast i {{
            font-size: 20px;
            flex-shrink: 0;
        }}
        
        .toast-message {{
            flex: 1;
        }}
        
        .toast-close {{
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 16px;
            transition: background 0.2s;
            flex-shrink: 0;
        }}
        
        .toast-close:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        
        @keyframes toastSlideIn {{
            from {{
                transform: translateX(400px);
                opacity: 0;
            }}
            to {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        .toast.removing {{
            animation: toastSlideOut 0.3s ease forwards;
        }}
        
        @keyframes toastSlideOut {{
            to {{
                transform: translateX(400px);
                opacity: 0;
            }}
        }}
        /* ============================================
           SKELETON LOADING STATES
           ============================================ */
        .skeleton {{
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: skeletonLoading 1.5s ease-in-out infinite;
            border-radius: 4px;
        }}
        
        @keyframes skeletonLoading {{
            0% {{
                background-position: 200% 0;
            }}
            100% {{
                background-position: -200% 0;
            }}
        }}
        
        .skeleton-text {{
            height: 16px;
            margin-bottom: 8px;
            border-radius: 4px;
        }}
        
        .skeleton-button {{
            height: 40px;
            width: 120px;
            border-radius: 8px;
        }}
        
        .skeleton-row {{
            height: 48px;
            margin-bottom: 4px;
            border-radius: 6px;
        }}
        
        /* ============================================
           ENHANCED BUTTON ANIMATIONS
           ============================================ */
        button {{
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        button::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }}
        
        button:active::before {{
            width: 300px;
            height: 300px;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
        }}
        
        button:active {{
            transform: translateY(0);
        }}
        
        /* Loading spinner for buttons */
        .btn-loading {{
            pointer-events: none;
            position: relative;
        }}
        
        .btn-loading::after {{
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            top: 50%;
            left: 50%;
            margin-left: -8px;
            margin-top: -8px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }}
        
        @keyframes spin {{
            to {{
                transform: rotate(360deg);
            }}
        }}
        
        /* ============================================
           SMOOTH TRANSITIONS
           ============================================ */
        * {{
            transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
        }}
        
        .fade-in {{
            animation: fadeIn 0.4s ease;
        }}
        
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        /* Enhanced table row hover */
        table tbody tr {{
            transition: all 0.2s ease;
        }}
        
        table tbody tr:hover {{
            transform: scale(1.01);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }}
        
        /* Smooth scroll */
        html {{
            scroll-behavior: smooth;
        }}
        
        /* Focus states for accessibility */
        button:focus,
        input:focus,
        select:focus,
        textarea:focus {{
            outline: 2px solid var(--primary-color);
            outline-offset: 2px;
        }}
        
        /* Progress bar animation */
        .progress-bar {{
            position: relative;
            overflow: hidden;
        }}
        
        .progress-bar::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(255, 255, 255, 0.3), 
                transparent
            );
            animation: shimmer 2s infinite;
        }}
        
        @keyframes shimmer {{
            0% {{
                transform: translateX(-100%);
            }}
            100% {{
                transform: translateX(100%);
            }}
        }}
        
        /* ============================================
           MODAL STYLES
           ============================================ */
        .modal {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: modalFadeIn 0.3s ease;
        }}
        
        @keyframes modalFadeIn {{
            from {{
                opacity: 0;
            }}
            to {{
                opacity: 1;
            }}
        }}
        
        .modal-content {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-height: 90vh;
            overflow-y: auto;
            animation: modalSlideUp 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }}
        
        @keyframes modalSlideUp {{
            from {{
                transform: translateY(50px);
                opacity: 0;
            }}
            to {{
                transform: translateY(0);
                opacity: 1;
            }}
        }}
        
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 24px 30px;
            border-bottom: 2px solid #e5e7eb;
            background: linear-gradient(135deg, #f9fafb, #f3f4f6);
        }}
        
        .modal-header h2 {{
            margin: 0;
            color: #1f2937;
            font-size: 24px;
            font-weight: 700;
        }}
        
        .modal-close {{
            background: none;
            border: none;
            font-size: 32px;
            color: #6b7280;
            cursor: pointer;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.2s;
            line-height: 1;
            padding: 0;
        }}
        
        .modal-close:hover {{
            background: #f3f4f6;
            color: #1f2937;
            transform: rotate(90deg);
        }}
        
        .modal-body {{
            padding: 30px;
        }}
        
        /* Modal table styles */
        .modal-content table tbody tr {{
            border-bottom: 1px solid #f3f4f6;
        }}
        
        .modal-content table tbody tr:hover {{
            background: #f9fafb;
            transform: none;
            box-shadow: none;
        }}
        
        .modal-content table tbody td {{
            padding: 12px;
            font-size: 13px;
            color: #374151;
        }}
        
        .modal-content table tbody tr:nth-child(even) {{
            background: #fafafa;
        }}
        
        /* Quill Font Families */
        .ql-font-arial {{
            font-family: Arial, sans-serif;
        }}
        .ql-font-times-new-roman {{
            font-family: 'Times New Roman', Times, serif;
        }}
        .ql-font-courier-new {{
            font-family: 'Courier New', Courier, monospace;
        }}
        .ql-font-georgia {{
            font-family: Georgia, serif;
        }}
        .ql-font-verdana {{
            font-family: Verdana, sans-serif;
        }}
        .ql-font-comic-sans {{
            font-family: 'Comic Sans MS', cursive;
        }}
        .ql-font-trebuchet {{
            font-family: 'Trebuchet MS', sans-serif;
        }}
        .ql-font-impact {{
            font-family: Impact, sans-serif;
        }}
        
        /* Quill Font Sizes with Proportional Line Spacing */
        .ql-size-small {{
            font-size: 0.75em;
            line-height: 0.9;  /* Tighter spacing for small text */
        }}
        .ql-size-large {{
            font-size: 1.5em;
            line-height: 1.2;  /* Slightly more spacing for large text */
        }}
        .ql-size-huge {{
            font-size: 2.5em;
            line-height: 1.3;  /* More spacing for huge text */
        }}
        
        /* Apply same line-height to Quill editor so it shows in real-time */
        .ql-editor .ql-size-small {{
            font-size: 0.75em;
            line-height: 0.9 !important;
        }}
        .ql-editor .ql-size-large {{
            font-size: 1.5em;
            line-height: 1.2 !important;
        }}
        .ql-editor .ql-size-huge {{
            font-size: 2.5em;
            line-height: 1.3 !important;
        }}
        .ql-editor p {{
            line-height: 1.2;
            margin: 0;
        }}
    </style>
</head>
<body>
    <!-- Toast Notification Container -->
    <div id="toastContainer"></div>
    
    <div class="container">
        <div class="header">
            <h1>CISA Email Campaign Management System</h1>
            <div class="subtitle">Cybersecurity and Infrastructure Security Agency</div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('config', this)">⚙️ Email Config</div>
            <div class="tab" onclick="showTab('contacts', this)">👥 Contacts</div>
            <div class="tab" onclick="showTab('campaign', this)">📧 Send Campaign</div>
            <div class="tab" onclick="showTab('history', this)">📜 Campaign History</div>
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
                <label style="font-size: 16px; font-weight: 700; color: #1f2937; margin-bottom: 12px; display: block;">🔍 Contact Filter</label>
                
                <!-- Filter Type Selection (Buttons/Checkboxes) -->
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #374151;">Select Filter Category:</label>
                    <div id="filterTypeButtons" style="display: flex; flex-wrap: wrap; gap: 8px;">
                        <button class="filter-type-btn" data-filter="" onclick="selectFilterType('')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            All
                        </button>
                        <button class="filter-type-btn" data-filter="entity_type" onclick="selectFilterType('entity_type')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Entity Type
                        </button>
                        <button class="filter-type-btn" data-filter="state" onclick="selectFilterType('state')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            State
                        </button>
                        <button class="filter-type-btn" data-filter="agency_name" onclick="selectFilterType('agency_name')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Agency
                        </button>
                        <button class="filter-type-btn" data-filter="sector" onclick="selectFilterType('sector')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Sector
                        </button>
                        <button class="filter-type-btn" data-filter="subsection" onclick="selectFilterType('subsection')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Sub-section
                        </button>
                        <button class="filter-type-btn" data-filter="ms_isac_member" onclick="selectFilterType('ms_isac_member')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            MS-ISAC Member
                        </button>
                        <button class="filter-type-btn" data-filter="soc_call" onclick="selectFilterType('soc_call')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            SOC Call
                        </button>
                        <button class="filter-type-btn" data-filter="fusion_center" onclick="selectFilterType('fusion_center')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Fusion Center
                        </button>
                        <button class="filter-type-btn" data-filter="k12" onclick="selectFilterType('k12')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            K-12
                        </button>
                        <button class="filter-type-btn" data-filter="water_wastewater" onclick="selectFilterType('water_wastewater')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Water/Wastewater
                        </button>
                        <button class="filter-type-btn" data-filter="weekly_rollup" onclick="selectFilterType('weekly_rollup')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Weekly Rollup
                        </button>
                        <button class="filter-type-btn" data-filter="region" onclick="selectFilterType('region')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Region
                        </button>
                    </div>
                </div>
                
                <!-- Available Values Area (shown when a filter type is selected) -->
                <div id="availableValuesArea" style="display: none; margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #374151;">Available Values (click to add):</label>
                    <div id="availableValuesList" style="max-height: 200px; overflow-y: auto; padding: 12px; background: #f9fafb; border: 2px solid #e5e7eb; border-radius: 8px; display: flex; flex-wrap: wrap; gap: 6px;">
                        <!-- Dynamic value buttons will appear here -->
                    </div>
                    <small id="availableCount" style="display: block; margin-top: 6px; color: #6b7280;"></small>
                </div>
                
                <!-- Selected Filter Values (tags with remove buttons) -->
                <div id="selectedValuesArea" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #374151;">Filter Values:</label>
                    <div id="selectedValuesTags" style="min-height: 44px; padding: 10px; background: white; border: 2px solid #e5e7eb; border-radius: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
                        <small style="color: #9ca3af; font-style: italic;">No filters selected - showing all contacts</small>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px;">
                    <button onclick="applyContactFilter()" class="btn-primary" style="padding: 10px 20px; font-weight: 600; font-size: 14px;">🔍 Apply Filter</button>
                    <button onclick="clearAllFilters()" class="btn-secondary" style="padding: 10px 20px; font-weight: 600; font-size: 14px; background: #6b7280;">🔄 Clear All</button>
                </div>
            </div>
            <button onclick="loadContacts()">🔄 Load Contacts</button>
            <button class="btn-success" onclick="addEmptyRow()">➕ Add Row (Inline)</button>
            <button onclick="showAddContact()">📝 Add Contact (Form)</button>
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
            
            <!-- Contacts List Title -->
            <h2 style="margin: 30px 0 20px 0; color: #1f2937; font-size: 1.8rem; font-weight: 700; border-bottom: 3px solid #6366f1; padding-bottom: 10px;">
                📋 Contacts List
            </h2>
            
            <!-- Pagination Controls -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;">
                <div style="display: flex; gap: 10px; align-items: center;">
                    <span id="pageInfo" style="color: #6b7280; font-weight: 500;">Page 1</span>
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
            
            <div class="form-group" style="border: 2px solid #cbd5e1; border-radius: 12px; padding: 20px; background: #f8fafc;">
                <label style="font-size: 16px; font-weight: 700; color: #1f2937; margin-bottom: 12px; display: block;">🎯 Target Group Filter</label>
                
                <!-- Filter Type Selection (Buttons) -->
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #374151;">Select Filter Category:</label>
                    <div id="campaignFilterTypeButtons" style="display: flex; flex-wrap: wrap; gap: 8px;">
                        <button class="campaign-filter-type-btn" data-filter="" onclick="selectCampaignFilterType('')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            All
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="entity_type" onclick="selectCampaignFilterType('entity_type')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Entity Type
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="state" onclick="selectCampaignFilterType('state')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            State
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="agency_name" onclick="selectCampaignFilterType('agency_name')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Agency
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="sector" onclick="selectCampaignFilterType('sector')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Sector
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="subsection" onclick="selectCampaignFilterType('subsection')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Sub-section
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="ms_isac_member" onclick="selectCampaignFilterType('ms_isac_member')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            MS-ISAC Member
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="soc_call" onclick="selectCampaignFilterType('soc_call')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            SOC Call
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="fusion_center" onclick="selectCampaignFilterType('fusion_center')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Fusion Center
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="k12" onclick="selectCampaignFilterType('k12')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            K-12
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="water_wastewater" onclick="selectCampaignFilterType('water_wastewater')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Water/Wastewater
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="weekly_rollup" onclick="selectCampaignFilterType('weekly_rollup')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Weekly Rollup
                        </button>
                        <button class="campaign-filter-type-btn" data-filter="region" onclick="selectCampaignFilterType('region')" style="padding: 8px 16px; border: 2px solid #e5e7eb; background: white; color: #374151; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                            Region
                        </button>
                    </div>
                </div>
                
                <!-- Available Values Area (shown when a filter type is selected) -->
                <div id="campaignAvailableValuesArea" style="display: none; margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #374151;">Available Values (click to add):</label>
                    <div id="campaignAvailableValuesList" style="max-height: 200px; overflow-y: auto; padding: 12px; background: #f9fafb; border: 2px solid #e5e7eb; border-radius: 8px; display: flex; flex-wrap: wrap; gap: 6px;">
                        <!-- Dynamic value buttons will appear here -->
                    </div>
                    <small id="campaignAvailableCount" style="display: block; margin-top: 6px; color: #6b7280;"></small>
                </div>
                
                <!-- Selected Filter Values (tags with remove buttons) -->
                <div id="campaignSelectedValuesArea" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #374151;">Filter Values:</label>
                    <div id="campaignSelectedValuesTags" style="min-height: 44px; padding: 10px; background: white; border: 2px solid #e5e7eb; border-radius: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
                        <small style="color: #9ca3af; font-style: italic;">No filters selected - will send to all contacts</small>
                    </div>
                </div>
                
                <!-- Apply Filter Button -->
                <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                    <button onclick="applyCampaignFilter()" class="btn-primary" style="padding: 10px 20px; font-weight: 600; font-size: 14px;">🔍 Apply Filter</button>
                    <button onclick="clearAllCampaignFilters()" class="btn-secondary" style="padding: 10px 20px; font-weight: 600; font-size: 14px; background: #6b7280;">🔄 Clear All</button>
                </div>
                
                <!-- Contact Count Display -->
                <div id="campaignContactCount" style="padding: 12px; background: #f0f9ff; border: 2px solid #3b82f6; border-radius: 8px; margin-bottom: 15px; display: none;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <strong style="color: #1e40af; font-size: 14px;">📊 Target Contacts:</strong>
                            <span id="campaignContactCountNumber" style="color: #1e40af; font-size: 14px; font-weight: 700; margin-left: 8px;">0</span>
                        </div>
                        <button onclick="openTargetContactsModal()" style="padding: 8px 16px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;">
                            <i class="fas fa-eye"></i> View Target Contacts
                        </button>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label>👤 Your Name:</label>
                <input type="text" id="userName" placeholder="Enter your name (saved in browser)" onchange="saveUserName()">
                <small style="color: #6b7280;">This will be recorded as who launched the campaign. Your name is saved in your browser.</small>
            </div>

            <div style="display:flex; gap:12px; margin-top:8px;">
                <div style="flex:1;">
                    <label for="campaignTo" style="font-size:12px; color:var(--gray-600)">To (comma-separated)</label>
                    <input type="text" id="campaignTo" placeholder="recipient1@example.com, recipient2@example.com" style="width:100%; padding:8px; border-radius:6px; border:1px solid #e5e7eb;">
                </div>
                <div style="flex:1;">
                    <label for="campaignCc" style="font-size:12px; color:var(--gray-600)">CC (comma-separated)</label>
                    <input type="text" id="campaignCc" placeholder="alice@example.com, bob@example.com" style="width:100%; padding:8px; border-radius:6px; border:1px solid #e5e7eb;">
                </div>
                <div style="flex:1;">
                    <label for="campaignBcc" style="font-size:12px; color:var(--gray-600)">BCC (comma-separated)</label>
                    <input type="text" id="campaignBcc" placeholder="hidden@example.com" style="width:100%; padding:8px; border-radius:6px; border:1px solid #e5e7eb;">
                </div>
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
                <div style="background: #eff6ff; padding: 10px; border-radius: 6px; border-left: 4px solid #3b82f6; margin-bottom: 8px; font-size: 12px;">
                    <strong>✨ Editor Features:</strong><br>
                    • <strong>Copy/Paste HTML:</strong> Paste formatted HTML directly (Ctrl+V) or use 📋 Paste HTML button<br>
                    • <strong>Inline Images:</strong> Paste/embed images - they're auto-converted to work in emails<br>
                    • <strong>Resize Images:</strong> Click any image to see resize handles - drag to resize<br>
                    • <strong>Formatting:</strong> Use toolbar for bold, colors, lists, alignment, etc.<br>
                    • <strong>Placeholders:</strong> Use {{{{first_name}}}}, {{{{email}}}}, etc. for personalization
                </div>
                <div id="body" style="min-height: 200px; background: white;"></div>
                <div style="display: flex; gap: 10px; margin-top: 8px;">
                    <small style="flex: 1; color: #6b7280;">💡 Tip: You can paste HTML directly (Ctrl+V) or click "📋 Paste HTML" for a dialog</small>
                    <button onclick="pasteRawHTML()" type="button" style="font-size: 11px; padding: 4px 8px; background: #6366f1; color: white; border: none; border-radius: 4px; cursor: pointer;" title="Paste HTML from clipboard or dialog">
                        📋 Paste HTML
                    </button>
                </div>
            </div>
            
            <div class="form-group">
                <label>📎 Attachments (Optional):</label>
                <div style="margin-bottom: 10px; padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                    <strong>Important:</strong> Maximum total size is <strong>40 MB per email</strong> (including all attachments). 
                    Supported formats: PDF, DOC, DOCX, XLS, XLSX, PNG, JPG, TXT, CSV, ICS, MSG
                </div>
                <input type="file" id="attachmentFiles" multiple style="display: none;" onchange="handleAttachmentUpload()" accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt,.csv,.ics,.msg">
                <button onclick="document.getElementById('attachmentFiles').click()" style="background: #6366f1;">
                    📎 Add Attachments
                </button>
                <div id="attachmentsList" style="margin-top: 15px;"></div>
                <div id="attachmentSize" style="margin-top: 10px; font-size: 14px; color: #6b7280;"></div>
            </div>
            
            <div style="display: flex; gap: 15px; margin-top: 20px;">
                <button class="btn-success" onclick="sendCampaign(event)">🚀 Send Campaign</button>
                <button onclick="clearCampaignForm()">🗑️ Clear Form</button>
            </div>
            <!-- <small style="color: #6b7280; display: block; margin-top: 8px;">
                💡 Use Preview to see exactly what recipients will receive before sending
            </small> -->
            
            <div id="campaignResult" class="result hidden"></div>
        </div>
        <div id="history" class="tab-content">
            <h2>📜 Campaign History</h2>
            <p style="color: #6b7280; margin-bottom: 20px;">View and manage past email campaigns</p>
            
            <div style="display: flex; gap: 10px; margin-bottom: 20px; align-items: center;">
                <button onclick="loadCampaignHistory()" class="btn-primary">🔄 Refresh History</button>
                <button onclick="exportAllCampaigns()" class="btn-success">📥 Export All to CSV</button>
                <input id="historySearch" type="text" placeholder="Search campaign name or subject" 
                    style="flex: 1; min-width: 240px; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px;" 
                    onkeydown="if (event.key === 'Enter') performHistorySearch()" />
                <button onclick="performHistorySearch()" class="btn-secondary">🔎 Search</button>
            </div>
            
            <div id="historyLoading" style="display: none; text-align: center; padding: 40px;">
                <div style="font-size: 24px;">⏳</div>
                <p>Loading campaign history...</p>
            </div>
            
            <div id="historyContent" style="overflow-x: auto;">
                <table id="historyTable" style="width: 100%; border-collapse: collapse; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-radius: 8px; overflow: hidden;">
                    <thead>
                        <tr>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Campaign Name</th>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Subject</th>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Date</th>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Recipients</th>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Status</th>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Launched By</th>
                            <th style="padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="historyBody">
                        <tr>
                            <td colspan="7" style="padding: 40px; text-align: center; color: #9ca3af;">
                                Click "Refresh History" to load campaigns
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div id="historyPager" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0;">
                    <button id="historyPrevBtn" onclick="paginateHistory('prev')" class="btn-secondary" disabled>◀ Previous</button>
                    <span id="historyPageInfo" style="color: #6b7280;">Showing up to 50 campaigns</span>
                    <button id="historyNextBtn" onclick="paginateHistory('next')" class="btn-secondary" disabled>Next ▶</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Target Contacts Modal -->
    <div id="targetContactsModal" class="modal" style="display: none;">
        <div class="modal-content" style="max-width: 1200px; width: 90%;">
            <div class="modal-header">
                <h2><i class="fas fa-users"></i> Target Contacts Preview</h2>
                <button class="modal-close" onclick="closeTargetContactsModal()">×</button>
            </div>
            <div class="modal-body">
                <div id="targetContactsInfo" style="margin-bottom: 15px; padding: 12px; background: #f0f9ff; border-left: 4px solid #3b82f6; border-radius: 4px;">
                    <strong>Total Target Contacts:</strong> <span id="modalTotalCount">0</span>
                </div>
                
                <!-- Contacts Table -->
                <div style="overflow-x: auto; max-height: 500px; border: 1px solid #e5e7eb; border-radius: 8px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead style="background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">#</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">First Name</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">Last Name</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">Email</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">Agency</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">State</th>
                                <th style="padding: 12px; text-align: left; font-weight: 600; font-size: 13px; border-bottom: 2px solid #1e3a8a;">Entity Type</th>
                            </tr>
                        </thead>
                        <tbody id="targetContactsTableBody">
                            <!-- Dynamic rows will be inserted here -->
                        </tbody>
                    </table>
                </div>
                
                <!-- Pagination Controls -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding: 15px; background: #f9fafb; border-radius: 8px;">
                    <button id="modalPrevBtn" onclick="loadTargetContactsPage('prev')" style="padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;" disabled>
                        <i class="fas fa-chevron-left"></i> Previous
                    </button>
                    <div style="font-weight: 600; color: #374151;">
                        Page <span id="modalCurrentPage">1</span> of <span id="modalTotalPages">1</span>
                        <span style="margin-left: 15px; color: #6b7280; font-weight: normal;">(Showing <span id="modalShowingCount">0</span> contacts)</span>
                    </div>
                    <button id="modalNextBtn" onclick="loadTargetContactsPage('next')" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;">
                        Next <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Campaign Details Modal -->
    <div id="campaignDetailsModal" class="modal" style="display: none;">
        <div class="modal-content" style="max-width: 1200px; width: 90%;">
            <div class="modal-header">
                <h2>📧 Campaign Details</h2>
                <button class="modal-close" onclick="closeCampaignDetailsModal()">×</button>
            </div>
            <div class="modal-body">
                <div id="campaignDetailsContent">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div>
                            <strong>Campaign Name:</strong>
                            <div id="detailCampaignName" style="padding: 8px; background: #f3f4f6; border-radius: 4px; margin-top: 4px;"></div>
                        </div>
                        <div>
                            <strong>Subject:</strong>
                            <div id="detailSubject" style="padding: 8px; background: #f3f4f6; border-radius: 4px; margin-top: 4px;"></div>
                        </div>
                        <div>
                            <strong>Date Sent:</strong>
                            <div id="detailDate" style="padding: 8px; background: #f3f4f6; border-radius: 4px; margin-top: 4px;"></div>
                        </div>
                        <div>
                            <strong>Launched By:</strong>
                            <div id="detailLaunchedBy" style="padding: 8px; background: #f3f4f6; border-radius: 4px; margin-top: 4px;"></div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>To Recipients:</strong>
                        <div id="detailToRecipients" style="padding: 8px; background: #f0f9ff; border-radius: 4px; margin-top: 4px; min-height: 30px;"></div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>CC Recipients:</strong>
                        <div id="detailCcRecipients" style="padding: 8px; background: #f0fdf4; border-radius: 4px; margin-top: 4px; min-height: 30px;"></div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>BCC Recipients:</strong>
                        <div id="detailBccRecipients" style="padding: 8px; background: #fef3c7; border-radius: 4px; margin-top: 4px; min-height: 30px;"></div>
                    </div>
                    
                    <div id="detailAttachments" style="margin-bottom: 20px;"></div>
                    
                    <div style="margin-bottom: 20px;">
                        <strong>Email Body:</strong>
                        <div id="detailBody" style="padding: 15px; background: white; border: 1px solid #e5e7eb; border-radius: 4px; margin-top: 4px; max-height: 400px; overflow-y: auto;"></div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 20px;">
                        <button onclick="exportCampaignTargets()" class="btn-success">📥 Export Targets to CSV</button>
                        <button onclick="closeCampaignDetailsModal()" class="btn-secondary">Close</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = '{api_url}';
        
        // ============================================
        // TOAST NOTIFICATION SYSTEM
        // ============================================
        const Toast = {{
            show: function(message, type = 'info', duration = 4000) {{
                const container = document.getElementById('toastContainer');
                const toast = document.createElement('div');
                toast.className = `toast toast-${{type}}`;
                
                const icons = {{
                    success: '<i class="fas fa-check-circle"></i>',
                    error: '<i class="fas fa-exclamation-circle"></i>',
                    warning: '<i class="fas fa-exclamation-triangle"></i>',
                    info: '<i class="fas fa-info-circle"></i>'
                }};
                
                toast.innerHTML = `
                    ${{icons[type] || icons.info}}
                    <div class="toast-message">${{message}}</div>
                    <button class="toast-close" onclick="Toast.close(this.parentElement)">×</button>
                `;
                
                container.appendChild(toast);
                
                // Auto remove after duration
                if (duration > 0) {{
                    setTimeout(() => {{
                        Toast.close(toast);
                    }}, duration);
                }}
                
                return toast;
            }},
            
            success: function(message, duration = 4000) {{
                return this.show(message, 'success', duration);
            }},
            
            error: function(message, duration = 5000) {{
                return this.show(message, 'error', duration);
            }},
            
            warning: function(message, duration = 4500) {{
                return this.show(message, 'warning', duration);
            }},
            
            info: function(message, duration = 4000) {{
                return this.show(message, 'info', duration);
            }},
            
            close: function(toast) {{
                toast.classList.add('removing');
                setTimeout(() => {{
                    toast.remove();
                }}, 300);
            }}
        }};
        
        // ============================================
        // LOADING SKELETON HELPER
        // ============================================
        function showSkeleton(containerId, count = 5) {{
            const container = document.getElementById(containerId);
            if (!container) return;
            
            container.innerHTML = '';
            for (let i = 0; i < count; i++) {{
                const skeleton = document.createElement('div');
                skeleton.className = 'skeleton skeleton-row';
                container.appendChild(skeleton);
            }}
        }}
        
        // Initialize Quill Rich Text Editor
        let quillEditor;
        document.addEventListener('DOMContentLoaded', function() {{
            // Register Image Resize module if available
            if (typeof ImageResize !== 'undefined') {{
                Quill.register('modules/imageResize', ImageResize.default);
                console.log('✅ Quill Image Resize module registered');
            }}
            
            // Old font configuration removed - using Outlook-optimized version below
            
            // Configure font sizes
            const Size = Quill.import('formats/size');
            Size.whitelist = ['small', 'large', 'huge'];
            Quill.register(Size, true);
            console.log('✅ Quill Size module registered:', Size.whitelist);
            
            // Register Outlook-optimized fonts for Quill
            const Font = Quill.import('formats/font');
            Font.whitelist = [
                // Outlook-safe system fonts (100% compatible)
                'arial', 'calibri', 'cambria', 'georgia', 'times-new-roman', 
                'courier-new', 'verdana', 'tahoma', 'trebuchet-ms', 'helvetica',
                // Limited web fonts that work in Outlook with strong fallbacks
                'segoe-ui', 'open-sans', 'roboto'
            ];
            Quill.register(Font, true);
            console.log('✅ Outlook-optimized fonts registered:', Font.whitelist);
            
            quillEditor = new Quill('#body', {{
                theme: 'snow',
                placeholder: 'Dear {{{{first_name}}}} {{{{last_name}}}},\\n\\nYour message here...',
                modules: {{
                    toolbar: [
                        [{{ 'header': [1, 2, 3, false] }}],
                        [{{ 'font': [
                            // Outlook-safe system fonts (100% compatible)
                            'arial', 'calibri', 'cambria', 'georgia', 'times-new-roman', 
                            'courier-new', 'verdana', 'tahoma', 'trebuchet-ms', 'helvetica',
                            // Limited web fonts with strong Outlook fallbacks
                            'segoe-ui', 'open-sans', 'roboto'
                        ] }}],  // Outlook-optimized font family selector
                        [{{ 'size': ['small', false, 'large', 'huge'] }}],  // Font size selector
                        ['bold', 'italic', 'underline', 'strike'],
                        [{{ 'color': [] }}, {{ 'background': [] }}],
                        [{{ 'list': 'ordered'}}, {{ 'list': 'bullet' }}],
                        [{{ 'align': [] }}],
                        [{{ 'indent': '-1' }}, {{ 'indent': '+1' }}],  // Indent controls
                        ['link', 'image'],
                        ['clean']
                    ],
                    imageResize: {{
                        displayStyles: {{
                            backgroundColor: 'black',
                            border: 'none',
                            color: 'white'
                        }},
                        modules: ['Resize', 'DisplaySize', 'Toolbar'],
                        handleStyles: {{
                            backgroundColor: 'white',
                            border: '2px solid #3b82f6',
                            width: '10px',
                            height: '10px'
                        }},
                        overlayStyles: {{
                            border: '2px dashed #3b82f6'
                        }}
                    }}
                }}
            }});
            
            console.log('✅ Quill editor initialized with image resize support');
            
            // Add font change event listeners for detailed logging
            quillEditor.on('selection-change', function(range, oldRange, source) {{
                if (range && range.length === 0) {{
                    // Cursor position changed - log current font at cursor
                    const format = quillEditor.getFormat(range.index, 1);
                    if (format.font) {{
                        console.log(`🎨 FONT SELECTION: Cursor at position ${{range.index}} has font: ${{format.font}}`);
                        console.log(`   📍 Font Details: ${{JSON.stringify(format)}}`);
                    }}
                }}
            }});
            
            quillEditor.on('text-change', function(delta, oldDelta, source) {{
                if (source === 'user') {{
                    // User made a change - check if font formatting was applied
                    const selection = quillEditor.getSelection();
                    if (selection) {{
                        const format = quillEditor.getFormat(selection.index, selection.length || 1);
                        if (format.font) {{
                            console.log(`🎨 FONT APPLIED: User applied font "${{format.font}}" at position ${{selection.index}}`);
                            console.log(`   📝 Selection length: ${{selection.length || 1}} characters`);
                            console.log(`   🎯 Full format: ${{JSON.stringify(format)}}`);
                            
                            // Log to server as well
                            fetch('/dev/null', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                body: JSON.stringify({{
                                    action: 'font_change',
                                    font: format.font,
                                    position: selection.index,
                                    length: selection.length || 1,
                                    timestamp: new Date().toISOString()
                                }})
                            }}).catch(() => {{}}); // Silent fail for logging
                        }}
                    }}
                }}
            }});
            
            // Monitor font dropdown clicks directly
            setTimeout(() => {{
                const fontPicker = document.querySelector('.ql-font');
                if (fontPicker) {{
                    fontPicker.addEventListener('click', function() {{
                        console.log('🖱️ FONT DROPDOWN: User clicked font dropdown');
                        
                        // Monitor for font selection
                        setTimeout(() => {{
                            const fontItems = document.querySelectorAll('.ql-font .ql-picker-item');
                            fontItems.forEach(item => {{
                                item.addEventListener('click', function() {{
                                    const fontValue = this.getAttribute('data-value') || 'default';
                                    console.log(`🎨 FONT SELECTED: User selected font "${{fontValue}}"`);
                                    console.log(`   📋 Font display name: ${{this.textContent || 'Default'}}`);
                                    console.log(`   ⏰ Timestamp: ${{new Date().toLocaleString()}}`);
                                    
                                    // Show user-friendly notification
                                    if (typeof Toast !== 'undefined') {{
                                        Toast.info(`Font changed to: ${{fontValue === 'default' ? 'Default' : fontValue}}`, 2000);
                                    }}
                                }});
                            }});
                        }}, 100);
                    }});
                    
                    console.log('✅ Font dropdown click monitoring enabled');
            
            // Start continuous font monitoring
            startFontMonitoring();
                }} else {{
                    console.warn('⚠️ Font dropdown not found for monitoring');
                }}
            }}, 500);
            
            // Add tooltips to Quill toolbar buttons
            setTimeout(() => {{
                const toolbar = document.querySelector('.ql-toolbar');
                if (toolbar) {{
                    // Header dropdown
                    const headerSelect = toolbar.querySelector('.ql-header');
                    if (headerSelect) headerSelect.setAttribute('title', 'Heading level (H1, H2, H3, Normal)');
                    
                    // Font dropdown
                    const fontSelect = toolbar.querySelector('.ql-font');
                    if (fontSelect) fontSelect.setAttribute('title', 'Font family (Arial, Georgia, etc.)');
                    
                    // Size dropdown
                    const sizeSelect = toolbar.querySelector('.ql-size');
                    if (sizeSelect) sizeSelect.setAttribute('title', 'Font size (Small, Normal, Large, Huge)');
                    
                    // Formatting buttons
                    const boldBtn = toolbar.querySelector('.ql-bold');
                    if (boldBtn) boldBtn.setAttribute('title', 'Bold (Ctrl+B)');
                    
                    const italicBtn = toolbar.querySelector('.ql-italic');
                    if (italicBtn) italicBtn.setAttribute('title', 'Italic (Ctrl+I)');
                    
                    const underlineBtn = toolbar.querySelector('.ql-underline');
                    if (underlineBtn) underlineBtn.setAttribute('title', 'Underline (Ctrl+U)');
                    
                    const strikeBtn = toolbar.querySelector('.ql-strike');
                    if (strikeBtn) strikeBtn.setAttribute('title', 'Strikethrough');
                    
                    // Color pickers
                    const colorBtn = toolbar.querySelector('.ql-color');
                    if (colorBtn) colorBtn.setAttribute('title', 'Text color');
                    
                    const backgroundBtn = toolbar.querySelector('.ql-background');
                    if (backgroundBtn) backgroundBtn.setAttribute('title', 'Background color / Highlight');
                    
                    // Lists
                    const orderedBtn = toolbar.querySelector('.ql-list[value="ordered"]');
                    if (orderedBtn) orderedBtn.setAttribute('title', 'Numbered list');
                    
                    const bulletBtn = toolbar.querySelector('.ql-list[value="bullet"]');
                    if (bulletBtn) bulletBtn.setAttribute('title', 'Bullet list');
                    
                    // Alignment
                    const alignSelect = toolbar.querySelector('.ql-align');
                    if (alignSelect) alignSelect.setAttribute('title', 'Text alignment (Left, Center, Right, Justify)');
                    
                    // Indent
                    const indentMinus = toolbar.querySelector('.ql-indent[value="-1"]');
                    if (indentMinus) indentMinus.setAttribute('title', 'Decrease indent');
                    
                    const indentPlus = toolbar.querySelector('.ql-indent[value="+1"]');
                    if (indentPlus) indentPlus.setAttribute('title', 'Increase indent');
                    
                    // Link and Image
                    const linkBtn = toolbar.querySelector('.ql-link');
                    if (linkBtn) linkBtn.setAttribute('title', 'Insert link');
                    
                    const imageBtn = toolbar.querySelector('.ql-image');
                    if (imageBtn) imageBtn.setAttribute('title', 'Insert image (or paste with Ctrl+V)');
                    
                    // Clean
                    const cleanBtn = toolbar.querySelector('.ql-clean');
                    if (cleanBtn) cleanBtn.setAttribute('title', 'Remove formatting');
                    
                    console.log('✅ Added tooltips to Quill toolbar buttons');
                }}
            }}, 100);  // Small delay to ensure toolbar is rendered
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
            
            if (tabName === 'history' && allCampaigns.length === 0) {{
                // Auto-load campaign history when first switching to History tab
                console.log('Auto-loading campaign history...');
                loadCampaignHistory();
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
                    Toast.success('Configuration saved successfully!');
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
                Toast.error(`Failed to save configuration: ${{error.message}}`);
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
            
            // Clear form fields (with null checks)
            const campaignName = document.getElementById('campaignName');
            if (campaignName) campaignName.value = '';
            
            const subject = document.getElementById('subject');
            if (subject) subject.value = '';
            
            // Clear Quill editor
            if (quillEditor) {{
                quillEditor.setContents([]);
            }}
            
            // Clear campaign filters
            clearAllCampaignFilters();
            
            // Clear attachments
            campaignAttachments = [];
            displayAttachments();
            
            // Clear user name field if it exists
            const userName = document.getElementById('userName');
            if (userName) userName.value = '';

            // Clear CC and BCC fields if they exist
            const campaignCc = document.getElementById('campaignCc');
            if (campaignCc) campaignCc.value = '';
            const campaignBcc = document.getElementById('campaignBcc');
            if (campaignBcc) campaignBcc.value = '';
            // Clear To field
            const campaignTo = document.getElementById('campaignTo');
            if (campaignTo) campaignTo.value = '';
            
            console.log('Campaign form cleared');
        }};
        
        // Helper to parse comma-separated email lists into arrays
        function parseEmails(input) {{
            if (!input) return [];
            return input.split(',').map(s => s.trim()).filter(s => s.length > 0);
        }}
        
        // Paste raw HTML into Quill editor
        function pasteRawHTML() {{
            const htmlContent = prompt(
                'Paste your HTML content below:\\n\\n' +
                '✅ Supports: HTML formatting, styles, tables, links\\n' +
                '✅ Images: Copy/paste images work (auto-converted to inline)\\n' +
                '✅ Placeholders: Use {{{{first_name}}}}, {{{{email}}}}, etc.\\n\\n' +
                'Your HTML:'
            );
            
            if (htmlContent === null) {{
                // User cancelled
                return;
            }}
            
            if (!htmlContent.trim()) {{
                alert('No HTML content provided');
                return;
            }}
            
            try {{
                console.log('Pasting raw HTML into Quill editor');
                console.log('HTML length:', htmlContent.length);
                
                // Quill's clipboard API to paste HTML
                const delta = quillEditor.clipboard.convert(htmlContent);
                quillEditor.setContents(delta, 'user');
                
                console.log('✅ HTML pasted successfully');
                
                // Show success message
                setTimeout(() => {{
                    alert(
                        '✅ HTML Content Pasted Successfully!\\n\\n' +
                        'Your HTML has been imported into the editor.\\n\\n' +
                        'Note: Quill preserves formatting but may simplify some complex styles.\\n\\n' +
                        'You can now edit the content or send the campaign.'
                    );
                }}, 100);
                
            }} catch (error) {{
                console.error('Error pasting HTML:', error);
                alert('Failed to paste HTML: ' + error.message);
            }}
        }}
        
        async function loadContacts(resetPagination = true) {{
            console.log('loadContacts called, resetPagination:', resetPagination);
            const button = event?.target || document.querySelector('button[onclick="loadContacts()"]');
            const originalText = button?.textContent || '🔄 Load Contacts';
            
            if (resetPagination) {{
                // Reset pagination to first page
                paginationState = {{
                    currentPage: 1,
                    pageSize: 25,  // Fixed page size (page size dropdown removed)
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
                
                // Show skeleton loading state
                const tbody = document.querySelector('#contactsTable tbody');
                if (tbody) {{
                    tbody.innerHTML = '';
                    for (let i = 0; i < paginationState.pageSize; i++) {{
                        tbody.innerHTML += '<tr><td colspan="20" class="skeleton skeleton-row"></td></tr>';
                    }}
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
        
        // changePageSize function removed - page size dropdown removed from UI (fixed at 25 contacts per page)
        
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
        
        async function loadContactsWithFilter() {{
            // Legacy function - now just loads all contacts and applies filter
            await loadContacts();
            await applyContactFilter();
        }}
        
        async function applyContactFilter() {{
            console.log('Applying contact filter from DynamoDB...', selectedFilterValues);
            
            // Clear the contacts table
            allContacts = [];
            displayContacts([]);
            
            // Show loading message
            const tbody = document.querySelector('#contactsTable tbody');
            tbody.innerHTML = '<tr><td colspan="20" style="text-align: center; padding: 40px; color: #6b7280; font-size: 14px;">⏳ Querying DynamoDB with filters...</td></tr>';
            
            // Check if any filters are selected
            const hasFilters = Object.keys(selectedFilterValues).length > 0;
            
            if (hasFilters) {{
                try {{
                    // Build query parameters for backend
                    const filters = Object.entries(selectedFilterValues)
                        .filter(([key, values]) => values && values.length > 0)
                        .map(([field, values]) => ({{
                            field: field,
                            values: values
                        }}));
                    
                    console.log('Querying DynamoDB with filters:', filters);
                    
                    // Call backend API with filters
                    const response = await fetch(`${{API_URL}}/contacts/filter`, {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ filters: filters }})
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                    }}
                    
                    const result = await response.json();
                    const filteredContacts = result.contacts || [];
                    
                    console.log(`Received ${{filteredContacts.length}} contacts from DynamoDB query`);
                    
                    // Update allContacts with filtered results
                    allContacts = filteredContacts;
                    
                    // Display the filtered results
                    displayContacts(filteredContacts);
                    
                    // Update status message
                    const filterCount = Object.values(selectedFilterValues).reduce((sum, vals) => sum + vals.length, 0);
                    const statusMsg = document.createElement('small');
                    statusMsg.style.cssText = 'color: #059669; font-weight: 600;';
                    statusMsg.textContent = `Showing ${{filteredContacts.length}} contact(s) from DynamoDB (${{filterCount}} filter(s) applied)`;
                    
                    const tagsContainer = document.getElementById('selectedValuesTags');
                    const existingStatus = tagsContainer.querySelector('.filter-status');
                    if (existingStatus) existingStatus.remove();
                    
                    statusMsg.className = 'filter-status';
                    tagsContainer.appendChild(statusMsg);
                    
                }} catch (error) {{
                    console.error('Error querying DynamoDB with filters:', error);
                    tbody.innerHTML = '<tr><td colspan="20" style="text-align: center; padding: 40px; color: #ef4444; font-size: 14px;">❌ Error loading filtered contacts: ' + error.message + '</td></tr>';
                }}
            }} else {{
                // No filters selected - load all contacts
                console.log('No filters selected - loading all contacts from DynamoDB');
                await loadContacts();
            }}
            
            // Reset pagination
            if (typeof paginationState !== 'undefined') {{
                paginationState.currentPage = 1;
                paginationState.lastKeys = [null];
            }}
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
            // Legacy function - filter count is now displayed in the tags area
            // This is kept for compatibility with old code
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
                        finalContacts = searchedContacts.filter(contact => {{
                            const contactValue = getFieldValue(contact, filterType);
                            return contactValue && selectedValues.includes(contactValue);
                        }});
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
                row.setAttribute('data-contact-id', contact.contact_id || contact.email);
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
                        <button onclick="saveContactRow('${{contact.email}}')" class="btn-success" style="padding: 6px 12px; font-size: 12px; font-weight: 600; margin-right: 5px;">💾 Save</button>
                        <button onclick="deleteContactRow('${{contact.contact_id || contact.email}}')" class="btn-danger" style="padding: 6px 12px; font-size: 12px; font-weight: 600; background: #ef4444;">🗑️ Delete</button>
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
        
        function addEmptyRow() {{
            const tbody = document.getElementById('contactsBody');
            
            // Check if there's already a new row being added
            if (document.querySelector('tr.new-contact-row')) {{
                alert('Please complete or cancel the current new contact before adding another');
                return;
            }}
            
            // Insert new row at the top
            const row = tbody.insertRow(0);
            row.classList.add('new-contact-row');
            row.style.background = '#f0fdf4'; // Light green background
            
            row.innerHTML = `
                <td contenteditable="true" data-field="email" class="editable-cell" placeholder="email@example.com" style="background: #dcfce7; font-weight: 600; border-right: 2px solid #86efac;">
                    <span style="color: #9ca3af; font-style: italic;">email@example.com</span>
                </td>
                <td contenteditable="true" data-field="first_name" class="editable-cell" placeholder="First Name"></td>
                <td contenteditable="true" data-field="last_name" class="editable-cell" placeholder="Last Name"></td>
                <td contenteditable="true" data-field="title" class="editable-cell" placeholder="Title"></td>
                <td contenteditable="true" data-field="entity_type" class="editable-cell" placeholder="Entity Type"></td>
                <td contenteditable="true" data-field="state" class="editable-cell" placeholder="State"></td>
                <td contenteditable="true" data-field="agency_name" class="editable-cell" placeholder="Agency"></td>
                <td contenteditable="true" data-field="sector" class="editable-cell" placeholder="Sector"></td>
                <td contenteditable="true" data-field="subsection" class="editable-cell" placeholder="Subsection"></td>
                <td contenteditable="true" data-field="phone" class="editable-cell" placeholder="Phone"></td>
                <td contenteditable="true" data-field="ms_isac_member" class="editable-cell yes-no-cell" placeholder="Yes/No"></td>
                <td contenteditable="true" data-field="soc_call" class="editable-cell yes-no-cell" placeholder="Yes/No"></td>
                <td contenteditable="true" data-field="fusion_center" class="editable-cell yes-no-cell" placeholder="Yes/No"></td>
                <td contenteditable="true" data-field="k12" class="editable-cell yes-no-cell" placeholder="Yes/No"></td>
                <td contenteditable="true" data-field="water_wastewater" class="editable-cell yes-no-cell" placeholder="Yes/No"></td>
                <td contenteditable="true" data-field="weekly_rollup" class="editable-cell yes-no-cell" placeholder="Yes/No"></td>
                <td contenteditable="true" data-field="alternate_email" class="editable-cell" placeholder="Alt Email"></td>
                <td contenteditable="true" data-field="region" class="editable-cell" placeholder="Region"></td>
                <td style="position: sticky; right: 0; background: #f0fdf4; border-left: 2px solid #cbd5e1; box-shadow: -2px 0 4px rgba(0,0,0,0.05);">
                    <button onclick="saveNewContact()" class="btn-success" style="padding: 6px 12px; font-size: 12px; font-weight: 600; margin-right: 5px;">💾 Save</button>
                    <button onclick="cancelNewContact()" class="btn-danger" style="padding: 6px 12px; font-size: 12px; font-weight: 600; background: #ef4444;">❌ Cancel</button>
                </td>
            `;
            
            // Clear placeholder text on focus
            const emailCell = row.querySelector('td[data-field="email"]');
            emailCell.addEventListener('focus', function() {{
                if (this.textContent.trim() === 'email@example.com' || this.querySelector('span')) {{
                    this.textContent = '';
                    this.style.color = '#1e40af';
                }}
            }});
            
            // Focus on email field
            setTimeout(() => emailCell.focus(), 100);
            
            console.log('✅ New empty row added');
        }}
        
        function cancelNewContact() {{
            const newRow = document.querySelector('tr.new-contact-row');
            if (newRow) {{
                newRow.remove();
                console.log('❌ New contact cancelled');
            }}
        }}
        
        async function saveNewContact() {{
            try {{
                const row = document.querySelector('tr.new-contact-row');
                if (!row) {{
                    alert('New contact row not found');
                    return;
                }}
                
                // Get all cells
                const cells = row.querySelectorAll('.editable-cell');
                
                // Build contact object
                const contactData = {{}};
                let emailFound = false;
                
                cells.forEach(cell => {{
                    const field = cell.getAttribute('data-field');
                    let value = cell.textContent.trim();
                    
                    // Skip placeholder text
                    if (field === 'email' && (value === 'email@example.com' || !value)) {{
                        value = '';
                    }}
                    
                    if (field === 'email' && value) {{
                        emailFound = true;
                    }}
                    
                    contactData[field] = value;
                }});
                
                // Validate email
                if (!emailFound || !contactData.email) {{
                    alert('Email is required!');
                    return;
                }}
                
                console.log('Creating new contact:', contactData);
                
                // Show saving state
                const saveBtn = row.querySelector('.btn-success');
                const originalText = saveBtn.textContent;
                saveBtn.textContent = '⏳ Saving...';
                saveBtn.disabled = true;
                
                // Send POST request to create contact
                const response = await fetch(`${{API_URL}}/contacts`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(contactData)
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    console.log('✅ New contact created');
                    
                    // Remove the new row
                    row.remove();
                    
                    // Show success message
                    alert('Contact added successfully!');
                    
                    // Reload contacts to show the new one
                    await loadContacts(false);
                }} else {{
                    throw new Error(result.error || 'Save failed');
                }}
                
            }} catch (error) {{
                console.error('❌ Error creating contact:', error);
                alert('Error creating contact: ' + error.message);
                
                const row = document.querySelector('tr.new-contact-row');
                if (row) {{
                    const saveBtn = row.querySelector('.btn-success');
                    saveBtn.textContent = '💾 Save';
                    saveBtn.disabled = false;
                }}
            }}
        }}
        
        function showDeleteConfirmation() {{
            return new Promise((resolve) => {{
                // Create modal overlay
                const overlay = document.createElement('div');
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 10000;
                    animation: fadeIn 0.2s ease-in-out;
                `;
                
                // Create confirmation dialog
                const dialog = document.createElement('div');
                dialog.style.cssText = `
                    background: white;
                    border-radius: 12px;
                    padding: 30px;
                    max-width: 450px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                    animation: slideIn 0.3s ease-out;
                `;
                
                dialog.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                        <h3 style="margin: 0 0 10px 0; color: #1f2937; font-size: 18px; font-weight: 600;">
                            JCDC Bulk Email asks
                        </h3>
                        <p style="margin: 0 0 25px 0; color: #6b7280; font-size: 15px; line-height: 1.5;">
                            Are you sure you want to delete this contact?<br>
                            <strong>This action cannot be undone.</strong>
                        </p>
                        <div style="display: flex; gap: 12px; justify-content: center;">
                            <button id="cancelDelete" style="
                                padding: 12px 28px;
                                background: #f3f4f6;
                                color: #374151;
                                border: none;
                                border-radius: 8px;
                                font-size: 15px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.2s;
                            ">Cancel</button>
                            <button id="confirmDelete" style="
                                padding: 12px 28px;
                                background: #ef4444;
                                color: white;
                                border: none;
                                border-radius: 8px;
                                font-size: 15px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.2s;
                            ">Delete</button>
                        </div>
                    </div>
                `;
                
                overlay.appendChild(dialog);
                document.body.appendChild(overlay);
                
                // Add hover effects
                const cancelBtn = dialog.querySelector('#cancelDelete');
                const confirmBtn = dialog.querySelector('#confirmDelete');
                
                cancelBtn.onmouseover = () => cancelBtn.style.background = '#e5e7eb';
                cancelBtn.onmouseout = () => cancelBtn.style.background = '#f3f4f6';
                confirmBtn.onmouseover = () => confirmBtn.style.background = '#dc2626';
                confirmBtn.onmouseout = () => confirmBtn.style.background = '#ef4444';
                
                // Handle button clicks
                cancelBtn.onclick = () => {{
                    overlay.style.animation = 'fadeOut 0.2s ease-in-out';
                    setTimeout(() => {{
                        document.body.removeChild(overlay);
                        resolve(false);
                    }}, 200);
                }};
                
                confirmBtn.onclick = () => {{
                    overlay.style.animation = 'fadeOut 0.2s ease-in-out';
                    setTimeout(() => {{
                        document.body.removeChild(overlay);
                        resolve(true);
                    }}, 200);
                }};
                
                // Add animations
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes fadeIn {{
                        from {{ opacity: 0; }}
                        to {{ opacity: 1; }}
                    }}
                    @keyframes fadeOut {{
                        from {{ opacity: 1; }}
                        to {{ opacity: 0; }}
                    }}
                    @keyframes slideIn {{
                        from {{ transform: translateY(-20px); opacity: 0; }}
                        to {{ transform: translateY(0); opacity: 1; }}
                    }}
                `;
                document.head.appendChild(style);
            }});
        }}
        
        async function deleteContactRow(contactId) {{
            try {{
                // Custom confirmation using modal
                const confirmed = await showDeleteConfirmation();
                if (!confirmed) {{
                    return;
                }}
                
                console.log('Deleting contact:', contactId);
                
                const response = await fetch(`${{API_URL}}/contacts?contact_id=${{encodeURIComponent(contactId)}}`, {{
                    method: 'DELETE',
                    headers: {{
                        'Content-Type': 'application/json'
                    }}
                }});
                
                console.log('Delete response status:', response.status);
                
                if (response.ok) {{
                    // Show success toast that auto-fades (no OK button needed)
                    Toast.success('✅ Contact deleted successfully', 3000);
                    
                    // Remove the row from the table
                    const row = document.querySelector(`tr[data-contact-id="${{contactId}}"]`);
                    if (row) {{
                        row.remove();
                    }}
                    
                    // Update the record count
                    const recordCount = document.getElementById('recordCount');
                    if (recordCount) {{
                        const currentCount = parseInt(recordCount.textContent.match(/\\d+/)[0] || 0);
                        recordCount.textContent = `${{currentCount - 1}} records`;
                    }}
                }} else {{
                    const errorData = await response.json();
                    Toast.error(`Failed to delete contact: ${{errorData.error || 'Unknown error'}}`);
                }}
            }} catch (error) {{
                console.error('Error deleting contact:', error);
                Toast.error('Failed to delete contact. Please try again.');
            }}
        }}
        async function saveContactRow(email) {{
            try {{
                // Find the row with this email
                const row = document.querySelector(`tr[data-email="${{email}}"]`);
                if (!row) {{
                    Toast.error('Row not found');
                    return;
                }}
                
                // Get contact_id from row attribute
                const contactId = row.getAttribute('data-contact-id');
                
                // Get all editable cells in this row
                const cells = row.querySelectorAll('.editable-cell');
                
                // Build updated contact object
                const contactData = {{
                    email: email,
                    contact_id: contactId  // Use actual contact_id from DynamoDB
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
                    Toast.success('Contact updated successfully!', 3000);
                    
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
        
        // Campaign Filter State
        let currentCampaignFilterType = null;
        let selectedCampaignFilterValues = {{}};  // {{filterType: [values]}}
        let campaignFilteredContacts = null;  // null = no filter applied, [] = filter applied but no results, [...] = filtered contacts
        
        async function selectCampaignFilterType(filterType) {{
            console.log('Campaign filter type selected:', filterType, 'Current type:', currentCampaignFilterType);
            
            const countDisplay = document.getElementById('campaignContactCount');
            const countNumber = document.getElementById('campaignContactCountNumber');
            
            // Allow toggling off by clicking the same button (including "All")
            if (currentCampaignFilterType === filterType) {{
                console.log('Toggling off current campaign filter type');
                currentCampaignFilterType = null;
                document.getElementById('campaignAvailableValuesArea').style.display = 'none';
                countDisplay.style.display = 'none';
                updateCampaignButtonStyles();
                return;
            }}
            
            currentCampaignFilterType = filterType;
            console.log('New current campaign filter type:', currentCampaignFilterType);
            updateCampaignButtonStyles();
            
            // If "All" is selected, get count from DynamoDB and display
            if (filterType === '') {{
                document.getElementById('campaignAvailableValuesArea').style.display = 'none';
                
                // Fetch all contacts count from DynamoDB
                try {{
                    console.log('Fetching all contacts count from DynamoDB...');
                    const response = await fetch(`${{API_URL}}/contacts?limit=1`);
                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                    }}
                    const data = await response.json();
                    
                    // Use the scan to get actual count
                    const countResponse = await fetch(`${{API_URL}}/contacts?limit=10000`);
                    if (!countResponse.ok) {{
                        throw new Error(`HTTP ${{countResponse.status}}: ${{countResponse.statusText}}`);
                    }}
                    const countData = await countResponse.json();
                    const totalContacts = (countData.contacts || []).length;
                    
                    // Display the count
                    countNumber.textContent = totalContacts;
                    countDisplay.style.display = 'block';
                    console.log(`Total contacts in DynamoDB: ${{totalContacts}}`);
                }} catch (error) {{
                    console.error('Error fetching contacts count:', error);
                    countDisplay.style.display = 'none';
                }}
                return;
            }}
            
            // Show loading state
            const availableValuesList = document.getElementById('campaignAvailableValuesList');
            const availableCount = document.getElementById('campaignAvailableCount');
            availableValuesList.innerHTML = '<small style="color: #6b7280;">Loading values...</small>';
            document.getElementById('campaignAvailableValuesArea').style.display = 'block';
            
            try {{
                // Call the backend /contacts/distinct endpoint
                console.log(`Fetching distinct values for campaign: ${{filterType}}`);
                const response = await fetch(`${{API_URL}}/contacts/distinct?field=${{encodeURIComponent(filterType)}}`);
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const data = await response.json();
                console.log('Distinct values received for campaign:', data);
                
                const distinctValues = data.values || [];
                
                // Populate available values as clickable buttons
                availableValuesList.innerHTML = '';
                if (distinctValues.length === 0) {{
                    availableValuesList.innerHTML = '<small style="color: #ef4444;">No values found for this field</small>';
                    availableCount.textContent = '0 values available';
                }} else {{
                    distinctValues.forEach(value => {{
                        const btn = document.createElement('button');
                        btn.textContent = value;
                        btn.onclick = () => addCampaignFilterValue(filterType, value);
                        btn.style.cssText = 'padding: 6px 12px; background: #3b82f6; color: white; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s;';
                        btn.onmouseover = () => {{ btn.style.background = '#2563eb'; }};
                        btn.onmouseout = () => {{ btn.style.background = '#3b82f6'; }};
                        availableValuesList.appendChild(btn);
                    }});
                    availableCount.textContent = `${{distinctValues.length}} value(s) available`;
                }}
            }} catch (error) {{
                console.error('Error loading campaign distinct values:', error);
                availableValuesList.innerHTML = `<small style="color: #ef4444;">Error: ${{error.message}}</small>`;
                availableCount.textContent = '';
            }}
        }}
        
        function addCampaignFilterValue(filterType, value) {{
            if (!selectedCampaignFilterValues[filterType]) {{
                selectedCampaignFilterValues[filterType] = [];
            }}
            
            if (!selectedCampaignFilterValues[filterType].includes(value)) {{
                selectedCampaignFilterValues[filterType].push(value);
                console.log('Added campaign filter value:', filterType, value);
                updateCampaignSelectedValuesTags();
            }}
        }}
        
        function removeCampaignFilterValue(filterType, value) {{
            if (selectedCampaignFilterValues[filterType]) {{
                selectedCampaignFilterValues[filterType] = selectedCampaignFilterValues[filterType].filter(v => v !== value);
                if (selectedCampaignFilterValues[filterType].length === 0) {{
                    delete selectedCampaignFilterValues[filterType];
                }}
                console.log('Removed campaign filter value:', filterType, value);
                updateCampaignSelectedValuesTags();
            }}
        }}
        
        function updateCampaignSelectedValuesTags() {{
            const tagsContainer = document.getElementById('campaignSelectedValuesTags');
            tagsContainer.innerHTML = '';
            
            const hasFilters = Object.keys(selectedCampaignFilterValues).length > 0;
            
            if (!hasFilters) {{
                tagsContainer.innerHTML = '<small style="color: #9ca3af; font-style: italic;">No filters selected - will send to all contacts</small>';
                return;
            }}
            
            // Display all selected filters as tags
            for (const [filterType, values] of Object.entries(selectedCampaignFilterValues)) {{
                values.forEach(value => {{
                    const tag = document.createElement('div');
                    tag.style.cssText = 'display: inline-flex; align-items: center; padding: 6px 10px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border-radius: 6px; font-size: 12px; font-weight: 600;';
                    tag.innerHTML = `
                        <span style="margin-right: 8px;">${{filterType}}: ${{value}}</span>
                        <button onclick="removeCampaignFilterValue('${{filterType}}', '${{value}}')" style="background: rgba(255,255,255,0.3); border: none; border-radius: 50%; width: 18px; height: 18px; min-width: 18px; max-width: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; line-height: 1; color: white; font-weight: bold; padding: 0; flex-shrink: 0;">×</button>
                    `;
                    tagsContainer.appendChild(tag);
                }});
            }}
        }}
        
        async function applyCampaignFilter() {{
            console.log('Applying campaign filter...', selectedCampaignFilterValues);
            
            const countDisplay = document.getElementById('campaignContactCount');
            const countNumber = document.getElementById('campaignContactCountNumber');
            
            // If no filters selected, reset to null (means fetch all contacts when sending)
            if (Object.keys(selectedCampaignFilterValues).length === 0) {{
                campaignFilteredContacts = null;  // null means no filter, will fetch all contacts
                countDisplay.style.display = 'none';
                console.log('No filters selected. Campaign will send to all contacts in database.');
                return;
            }}
            
            // Build filters array for API
            const filters = Object.entries(selectedCampaignFilterValues)
                .map(([field, values]) => ({{
                    field: field,
                    values: values
                }}));
            
            console.log('Campaign filter request:', filters);
            
            try {{
                // Call the backend /contacts/filter endpoint
                const response = await fetch(`${{API_URL}}/contacts/filter`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ filters: filters }})
                }});
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const data = await response.json();
                console.log('Campaign filtered contacts received:', data);
                
                campaignFilteredContacts = data.contacts || [];
                
                // Display the count
                countNumber.textContent = campaignFilteredContacts.length;
                countDisplay.style.display = 'block';
                
                if (campaignFilteredContacts.length === 0) {{
                    console.warn('No contacts match the selected filters.');
                }}
            }} catch (error) {{
                console.error('Error applying campaign filter:', error);
                alert(`Error loading filtered contacts: ${{error.message}}`);
            }}
        }}
        
        function clearAllCampaignFilters() {{
            selectedCampaignFilterValues = {{}};
            currentCampaignFilterType = null;
            campaignFilteredContacts = null;  // null means no filter applied
            document.getElementById('campaignAvailableValuesArea').style.display = 'none';
            document.getElementById('campaignContactCount').style.display = 'none';
            updateCampaignSelectedValuesTags();
            updateCampaignButtonStyles();
        }}
        
        function updateCampaignButtonStyles() {{
            const buttons = document.querySelectorAll('.campaign-filter-type-btn');
            buttons.forEach(btn => {{
                const filterValue = btn.getAttribute('data-filter');
                if (filterValue === currentCampaignFilterType) {{
                    btn.style.background = 'linear-gradient(135deg, #3b82f6, #2563eb)';
                    btn.style.color = 'white';
                    btn.style.borderColor = '#2563eb';
                    btn.style.boxShadow = '0 2px 8px rgba(59, 130, 246, 0.3)';
                }} else {{
                    btn.style.background = 'white';
                    btn.style.color = '#374151';
                    btn.style.borderColor = '#e5e7eb';
                    btn.style.boxShadow = 'none';
                }}
            }});
        }}
        
        // ============================================
        // TARGET CONTACTS MODAL
        // ============================================
        let targetContactsModalState = {{
            currentPage: 1,
            pageSize: 25,
            totalContacts: [],
            totalPages: 1
        }};
        
        async function openTargetContactsModal() {{
            const modal = document.getElementById('targetContactsModal');
            
            // Determine which contacts to show
            let contacts = [];
            
            if (campaignFilteredContacts && Array.isArray(campaignFilteredContacts) && campaignFilteredContacts.length > 0) {{
                // Use filtered contacts (already loaded)
                contacts = campaignFilteredContacts;
                console.log(`Using ${{contacts.length}} filtered contacts for modal`);
            }} else if (Object.keys(selectedCampaignFilterValues || {{}}).length > 0) {{
                // User selected filters but didn't apply them
                Toast.warning('Please click "Apply Filter" first to see target contacts.');
                return;
            }} else {{
                // No filters - load all contacts using pagination (handles 20k+ contacts)
                Toast.info('Loading all contacts with pagination...', 2000);
                try {{
                    contacts = await fetchAllContactsPaginated();
                    console.log(`Loaded ${{contacts.length}} contacts for modal using pagination`);
                }} catch (error) {{
                    Toast.error(`Failed to load contacts: ${{error.message}}`);
                    return;
                }}
            }}
            
            if (contacts.length === 0) {{
                Toast.warning('No target contacts found.');
                return;
            }}
            
            // Initialize modal state
            targetContactsModalState.totalContacts = contacts;
            targetContactsModalState.currentPage = 1;
            targetContactsModalState.totalPages = Math.ceil(contacts.length / targetContactsModalState.pageSize);
            
            // Update total count
            document.getElementById('modalTotalCount').textContent = contacts.length;
            
            // Load first page
            displayTargetContactsPage();
            
            // Show modal
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Prevent background scrolling
        }}
        
        function closeTargetContactsModal() {{
            const modal = document.getElementById('targetContactsModal');
            modal.style.display = 'none';
            document.body.style.overflow = ''; // Restore scrolling
        }}
        
        function loadTargetContactsPage(direction) {{
            if (direction === 'next' && targetContactsModalState.currentPage < targetContactsModalState.totalPages) {{
                targetContactsModalState.currentPage++;
            }} else if (direction === 'prev' && targetContactsModalState.currentPage > 1) {{
                targetContactsModalState.currentPage--;
            }}
            
            displayTargetContactsPage();
        }}
        
        function displayTargetContactsPage() {{
            const {{ currentPage, pageSize, totalContacts, totalPages }} = targetContactsModalState;
            
            // Calculate start and end indices
            const startIdx = (currentPage - 1) * pageSize;
            const endIdx = Math.min(startIdx + pageSize, totalContacts.length);
            const pageContacts = totalContacts.slice(startIdx, endIdx);
            
            // Populate table
            const tbody = document.getElementById('targetContactsTableBody');
            tbody.innerHTML = '';
            
            if (pageContacts.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: #6b7280;">No contacts to display</td></tr>';
                return;
            }}
            
            pageContacts.forEach((contact, index) => {{
                const globalIndex = startIdx + index + 1;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td style="font-weight: 600; color: #6b7280;">${{globalIndex}}</td>
                    <td>${{contact.first_name || contact.FirstName || '-'}}</td>
                    <td>${{contact.last_name || contact.LastName || '-'}}</td>
                    <td style="color: #3b82f6; font-weight: 500;">${{contact.email || '-'}}</td>
                    <td>${{contact.agency_name || contact.AgencyName || '-'}}</td>
                    <td>${{contact.state || contact.State || '-'}}</td>
                    <td>${{contact.entity_type || contact.EntityType || '-'}}</td>
                `;
                tbody.appendChild(row);
            }});
            
            // Update pagination info
            document.getElementById('modalCurrentPage').textContent = currentPage;
            document.getElementById('modalTotalPages').textContent = totalPages;
            document.getElementById('modalShowingCount').textContent = `${{startIdx + 1}}-${{endIdx}}`;
            
            // Update button states
            const prevBtn = document.getElementById('modalPrevBtn');
            const nextBtn = document.getElementById('modalNextBtn');
            
            prevBtn.disabled = currentPage === 1;
            prevBtn.style.opacity = currentPage === 1 ? '0.5' : '1';
            prevBtn.style.cursor = currentPage === 1 ? 'not-allowed' : 'pointer';
            
            nextBtn.disabled = currentPage === totalPages;
            nextBtn.style.opacity = currentPage === totalPages ? '0.5' : '1';
            nextBtn.style.cursor = currentPage === totalPages ? 'not-allowed' : 'pointer';
        }}
        
        // Close modal when clicking outside of it
        window.onclick = function(event) {{
            const modal = document.getElementById('targetContactsModal');
            if (event.target === modal) {{
                closeTargetContactsModal();
            }}
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
        
        // Fetch all contacts using pagination to handle large datasets (20k+ contacts)
        async function fetchAllContactsPaginated() {{
            let allContacts = [];
            let lastKey = null;
            let pageCount = 0;
            const pageSize = 1000;  // Fetch 1000 contacts per page
            
            console.log('Starting paginated contact fetch...');
            
            do {{
                pageCount++;
                const urlParams = new URLSearchParams();
                urlParams.append('limit', pageSize);
                
                if (lastKey) {{
                    urlParams.append('lastKey', JSON.stringify(lastKey));
                }}
                
                const url = `${{API_URL}}/contacts?${{urlParams.toString()}}`;
                console.log(`Fetching page ${{pageCount}} (batch size: ${{pageSize}})...`);
                
                const response = await fetch(url);
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const data = await response.json();
                const contacts = data.contacts || [];
                
                allContacts = allContacts.concat(contacts);
                lastKey = data.lastEvaluatedKey || null;
                
                console.log(`Page ${{pageCount}}: Fetched ${{contacts.length}} contacts. Total so far: ${{allContacts.length}}`);
                
                // Show progress to user
                if (pageCount % 5 === 0 || !lastKey) {{
                    Toast.info(`Loading contacts... ${{allContacts.length}} loaded`, 1000);
                }}
                
            }} while (lastKey);  // Continue until no more pages
            
            console.log(`✅ Pagination complete: Loaded ${{allContacts.length}} total contacts in ${{pageCount}} pages`);
            Toast.success(`Loaded ${{allContacts.length}} contacts successfully!`, 2000);
            
            return allContacts;
        }}
        
        async function sendCampaign(event) {{
            // Check form availability first
            if (!checkFormAvailability()) {{
                alert('Form is currently unavailable. Please refresh the page and try again.');
                return;
            }}
            
            const button = event?.target || document.querySelector('.btn-success');
            const originalText = button?.textContent || 'Send Campaign';
            
            try {{
                // IMPORTANT: Deactivate any active image resize handles first
                // This ensures images are in their final state before processing
                const resizeOverlays = document.querySelectorAll('.image-resize-overlay, .ql-image-resize-overlay');
                const resizeHandles = document.querySelectorAll('.image-resize-handle, .ql-image-resize-handle');
                
                if (resizeOverlays.length > 0 || resizeHandles.length > 0) {{
                    console.log(`🔧 Detected ${{resizeOverlays.length + resizeHandles.length}} active resize handle(s) - deactivating...`);
                    // Click elsewhere in the editor to deactivate resize handles
                    quillEditor.root.blur();
                    quillEditor.root.focus();
                    // Small delay to let resize module clean up
                    await new Promise(resolve => setTimeout(resolve, 100));
                    console.log(`   ✅ Resize handles deactivated`);
                }} else {{
                    console.log(`✅ No active resize handles detected`);
                }}
                
                // Show loading state
                button.textContent = 'Sending Campaign...';
                button.classList.add('loading');
                button.disabled = true;
                
            // Determine target contacts based on filter
            let targetContacts = [];
            let filterDescription = 'All Contacts';
            
            console.log('Campaign filter debug:', {{
                campaignFilteredContacts: campaignFilteredContacts === null ? 'null (no filter)' : 
                                         Array.isArray(campaignFilteredContacts) ? `array with ${{campaignFilteredContacts.length}} items` : 
                                         'invalid',
                selectedCampaignFilterValuesKeys: Object.keys(selectedCampaignFilterValues || {{}}).length,
                selectedCampaignFilterValues: selectedCampaignFilterValues
            }});
            
            // Check for To/CC/BCC early to allow To/CC/BCC-only campaigns
            const toValue = document.getElementById('campaignTo')?.value || '';
            const ccValue = document.getElementById('campaignCc')?.value || '';
            const bccValue = document.getElementById('campaignBcc')?.value || '';
            const hasToOrCcOrBcc = toValue.trim().length > 0 || ccValue.trim().length > 0 || bccValue.trim().length > 0;
            
            // THREE STATES: null = no filter, [] = filter with no results, [...] = filtered contacts
            if (campaignFilteredContacts === null) {{
                // No filters applied - check if To/CC/BCC exist
                if (!hasToOrCcOrBcc) {{
                    // No contacts selected and no To/CC/BCC
                    throw new Error('⚠️ Cannot send campaign: No targets selected.\\n\\nNo emails will be sent because you have not selected any targets.\\n\\nPlease select targets by:\\n• Clicking "All" to send to all contacts, OR\\n• Applying a filter to select specific contacts, OR\\n• Adding email addresses to To/CC/BCC fields\\n\\nThen click "Apply Filter" (if using contacts) before sending.');
                }}
                // To/CC/BCC exist, allow campaign with empty contact list
                targetContacts = [];
                filterDescription = 'To/CC/BCC Recipients Only';
                console.log('Sending to To/CC/BCC recipients only (no contacts from database)');
            }} else if (Array.isArray(campaignFilteredContacts) && campaignFilteredContacts.length > 0) {{
                // User has applied a filter and has results
                targetContacts = campaignFilteredContacts;
                const filterTags = Object.entries(selectedCampaignFilterValues || {{}})
                    .map(([field, values]) => `${{field}}: ${{values.join(', ')}}`)
                    .join('; ');
                filterDescription = filterTags || 'Filtered Contacts';
                console.log(`Using ${{targetContacts.length}} filtered contacts: ${{filterDescription}}`);
            }} else if (Array.isArray(campaignFilteredContacts) && campaignFilteredContacts.length === 0) {{
                // Filter was applied but returned no results - check if To/CC/BCC exist
                if (!hasToOrCcOrBcc) {{
                    // No contacts from filter and no To/CC/BCC
                    throw new Error('⚠️ Cannot send campaign: Your filter returned 0 contacts.\\n\\nNo emails will be sent because no targets are selected.\\n\\nPlease adjust your filter criteria, clear filters to send to all contacts, or add email addresses to To/CC/BCC fields.');
                }}
                // To/CC/BCC exist, allow campaign even with 0 filtered contacts
                targetContacts = [];
                filterDescription = 'To/CC/BCC Recipients Only (Filter returned 0 contacts)';
                console.log('Filter returned 0 contacts, but sending to To/CC/BCC recipients');
            }} else if (Object.keys(selectedCampaignFilterValues || {{}}).length > 0) {{
                // User has selected filter values but hasn't clicked "Apply Filter"
                console.log('Filters selected but not applied. Attempting to apply filter automatically...');
                
                try {{
                    await applyCampaignFilter();
                    
                    // Check the result after applying
                    if (campaignFilteredContacts && Array.isArray(campaignFilteredContacts) && campaignFilteredContacts.length > 0) {{
                        targetContacts = campaignFilteredContacts;
                        const filterTags = Object.entries(selectedCampaignFilterValues)
                            .map(([field, values]) => `${{field}}: ${{values.join(', ')}}`)
                            .join('; ');
                        filterDescription = filterTags;
                        console.log(`Auto-applied filter: ${{targetContacts.length}} contacts found`);
                    }} else {{
                        throw new Error('⚠️ Cannot send campaign: No contacts match the selected filter criteria.\\n\\nNo emails will be sent because no targets are selected.\\n\\nPlease adjust your filter or clear it to send to all contacts.');
                    }}
                }} catch (filterError) {{
                    console.error('Auto-apply filter failed:', filterError);
                    throw new Error('Please click "Apply Filter" button to see which contacts match your criteria, or clear the filter to send to all contacts.');
                }}
            }} else {{
                // Fallback: shouldn't get here, but fetch all contacts as safety
                console.warn('Unexpected state - falling back to fetch all contacts with pagination');
                try {{
                    targetContacts = await fetchAllContactsPaginated();
                    filterDescription = 'All Contacts';
                    console.log(`Fallback: Loaded ${{targetContacts.length}} contacts from database`);
                }} catch (loadError) {{
                    console.error('Failed to load contacts:', loadError);
                    throw new Error(`Failed to load contacts: ${{loadError.message}}`);
                }}
            }}
            
            // Note: Validation for targetContacts is done later after To/CC/BCC are parsed
            // to allow To/CC/BCC-only campaigns
            console.log(`Target contacts from filter: ${{targetContacts.length}} (${{filterDescription}})`);
            if (targetContacts.length > 0) {{
                console.log('Sample target contacts:', targetContacts.slice(0, 3));
            }}
            
            // Get content from Quill editor and clean it thoroughly
            let emailBody = quillEditor.root.innerHTML;
            
            // DEBUG: Check initial HTML from Quill editor
            console.log(`📝 Original Quill HTML length: ${{emailBody.length}} characters`);
            const imgInOriginal = emailBody.match(/<img[^>]+>/g);
            if (imgInOriginal) {{
                console.log(`🖼️ Original Quill HTML contains ${{imgInOriginal.length}} <img> tag(s):`);
                imgInOriginal.forEach((tag, i) => {{
                    const srcMatch = tag.match(/src="([^"]+)"/);
                    const srcType = srcMatch ? (srcMatch[1].startsWith('data:') ? 'data:' : 
                                                srcMatch[1].startsWith('campaign-attachments/') ? 'S3 key' : 'other') : 'no src';
                    console.log(`  ${{i + 1}}. type=${{srcType}}, tag=${{tag.substring(0, 100)}}...`);
                }});
            }} else {{
                console.error(`❌ Original Quill HTML has NO <img> tags!`);
            }}
            
            // Create a temporary div to parse and clean the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = emailBody;
            
            // IMPORTANT: LOCK IMAGE SIZE & POSITION at the moment user clicks Send Campaign
            // This ensures the received email matches exactly what's shown in the Quill editor
            
            // Step 1: Find all images currently in the Quill editor (not in tempDiv yet)
            const editorImages = quillEditor.root.querySelectorAll('img');
            const imageComputedStyles = new Map();
            
            editorImages.forEach((editorImg, idx) => {{
                // Get the COMPUTED styles (actual rendered styles) from the live editor
                const computedStyle = window.getComputedStyle(editorImg);
                
                // Capture exact size and position as rendered
                const lockedStyles = {{
                    width: computedStyle.width,           // Exact rendered width
                    height: computedStyle.height,         // Exact rendered height
                    display: computedStyle.display,       // Display mode
                    margin: computedStyle.margin,         // All margins
                    marginLeft: computedStyle.marginLeft,
                    marginRight: computedStyle.marginRight,
                    marginTop: computedStyle.marginTop,
                    marginBottom: computedStyle.marginBottom,
                    float: computedStyle.float,           // Floating alignment
                    verticalAlign: computedStyle.verticalAlign,
                    textAlign: computedStyle.textAlign,   // Parent text alignment
                    maxWidth: computedStyle.maxWidth,
                    maxHeight: computedStyle.maxHeight
                }};
                
                // Store by src attribute for matching later
                const src = editorImg.getAttribute('src');
                if (src) {{
                    imageComputedStyles.set(src.substring(0, 100), lockedStyles); // Use first 100 chars as key
                    console.log(`🔒 Locked image ${{idx + 1}} size/position:`, {{
                        width: lockedStyles.width,
                        height: lockedStyles.height,
                        display: lockedStyles.display,
                        float: lockedStyles.float
                    }});
                }}
            }});
            
            // Step 2: Now process the HTML in tempDiv
            // Unwrap images from resize containers FIRST (before any cleanup)
            // The Quill image resize module wraps images in span containers
            const allImageElements = tempDiv.querySelectorAll('img');
            let unwrappedCount = 0;
            
            allImageElements.forEach((img, idx) => {{
                // FIRST: Apply locked styles from the live editor to ensure exact match
                const imgSrc = img.getAttribute('src');
                if (imgSrc && imageComputedStyles.has(imgSrc.substring(0, 100))) {{
                    const lockedStyles = imageComputedStyles.get(imgSrc.substring(0, 100));
                    
                    // Build complete style string with all locked attributes
                    let styleString = '';
                    
                    // Essential sizing (use exact rendered values)
                    if (lockedStyles.width && lockedStyles.width !== 'auto') {{
                        styleString += `width: ${{lockedStyles.width}}; `;
                    }}
                    if (lockedStyles.height && lockedStyles.height !== 'auto') {{
                        styleString += `height: ${{lockedStyles.height}}; `;
                    }}
                    
                    // Display mode
                    if (lockedStyles.display && lockedStyles.display !== 'inline') {{
                        styleString += `display: ${{lockedStyles.display}}; `;
                    }}
                    
                    // Positioning and spacing
                    if (lockedStyles.float && lockedStyles.float !== 'none') {{
                        styleString += `float: ${{lockedStyles.float}}; `;
                    }}
                    if (lockedStyles.verticalAlign && lockedStyles.verticalAlign !== 'baseline') {{
                        styleString += `vertical-align: ${{lockedStyles.verticalAlign}}; `;
                    }}
                    
                    // Margins (for positioning)
                    // Only add non-zero margins
                    if (lockedStyles.marginTop && lockedStyles.marginTop !== '0px') {{
                        styleString += `margin-top: ${{lockedStyles.marginTop}}; `;
                    }}
                    if (lockedStyles.marginBottom && lockedStyles.marginBottom !== '0px') {{
                        styleString += `margin-bottom: ${{lockedStyles.marginBottom}}; `;
                    }}
                    if (lockedStyles.marginLeft && lockedStyles.marginLeft !== '0px') {{
                        styleString += `margin-left: ${{lockedStyles.marginLeft}}; `;
                    }}
                    if (lockedStyles.marginRight && lockedStyles.marginRight !== '0px') {{
                        styleString += `margin-right: ${{lockedStyles.marginRight}}; `;
                    }}
                    
                    // Max width/height constraints
                    if (lockedStyles.maxWidth && lockedStyles.maxWidth !== 'none') {{
                        styleString += `max-width: ${{lockedStyles.maxWidth}}; `;
                    }}
                    if (lockedStyles.maxHeight && lockedStyles.maxHeight !== 'none') {{
                        styleString += `max-height: ${{lockedStyles.maxHeight}}; `;
                    }}
                    
                    // Apply the locked styles
                    if (styleString.trim()) {{
                        img.setAttribute('style', styleString.trim());
                        console.log(`  ✅ Applied locked styles to image ${{idx + 1}}`);
                    }}
                }}
                
                // SECOND: Check if image is wrapped in a resize container and unwrap it
                const parent = img.parentElement;
                if (parent && parent !== tempDiv && parent.tagName.toLowerCase() !== 'p') {{
                    // Check if this is a resize wrapper (typically has only the image and maybe text nodes)
                    const meaningfulChildren = Array.from(parent.childNodes).filter(n => {{
                        if (n.nodeType === Node.ELEMENT_NODE) return true;
                        if (n.nodeType === Node.TEXT_NODE && n.textContent.trim() !== '') return true;
                        return false;
                    }});
                    
                    // If parent only contains this image (and nothing else meaningful), unwrap it
                    if (meaningfulChildren.length === 1 && meaningfulChildren[0] === img) {{
                        const grandParent = parent.parentElement;
                        if (grandParent) {{
                            // Copy any alignment from parent's context
                            const parentStyle = parent.getAttribute('style');
                            if (parentStyle && parentStyle.includes('text-align')) {{
                                const textAlignMatch = parentStyle.match(/text-align:\\s*([^;]+)/);
                                if (textAlignMatch) {{
                                    // Wrap in a div with text-align for email client compatibility
                                    const alignDiv = document.createElement('div');
                                    alignDiv.setAttribute('style', `text-align: ${{textAlignMatch[1].trim()}}`);
                                    grandParent.insertBefore(alignDiv, parent);
                                    alignDiv.appendChild(img);
                                    parent.remove();
                                    console.log(`  📍 Preserved alignment: ${{textAlignMatch[1]}}`);
                                    unwrappedCount++;
                                    return; // Skip normal unwrap since we created alignment div
                                }}
                            }}
                            
                            // Normal unwrap: insert image before wrapper, then remove wrapper
                            grandParent.insertBefore(img, parent);
                            parent.remove();
                            unwrappedCount++;
                        }}
                    }}
                }}
            }});
            
            if (unwrappedCount > 0) {{
                console.log(`✂️ Unwrapped ${{unwrappedCount}} image(s) from resize containers`);
            }}
            console.log(`🔒 Locked ${{imageComputedStyles.size}} image(s) to exact editor size/position`);
            
            // THIRD: Preserve paragraph-level alignment for images (centered, right-aligned, etc.)
            tempDiv.querySelectorAll('p, div').forEach(container => {{
                // Check if this container has text-align style
                const containerStyle = container.getAttribute('style');
                if (containerStyle && (containerStyle.includes('text-align: center') || 
                                       containerStyle.includes('text-align: right') ||
                                       containerStyle.includes('text-align:center') ||
                                       containerStyle.includes('text-align:right'))) {{
                    // Check if container has an image
                    const imgInside = container.querySelector('img');
                    if (imgInside) {{
                        // Extract text-align value
                        const alignMatch = containerStyle.match(/text-align:\\s*(center|right|left)/);
                        if (alignMatch) {{
                            const alignment = alignMatch[1];
                            // Make sure the container style is preserved
                            let cleanedStyle = containerStyle.replace(/\\s+/g, ' ').trim();
                            if (!cleanedStyle.includes('text-align')) {{
                                cleanedStyle += `; text-align: ${{alignment}}`;
                            }}
                            container.setAttribute('style', cleanedStyle);
                            console.log(`  📍 Preserved container alignment: ${{alignment}} for image`);
                        }}
                    }}
                }}
            }});
            
            // Remove Quill's clipboard container element (often contains unwanted HTML at bottom)
            const clipboardElements = tempDiv.querySelectorAll('.ql-clipboard, [id*="ql-clipboard"], [class*="ql-clipboard"]');
            clipboardElements.forEach(el => el.remove());
            console.log(`Removed ${{clipboardElements.length}} Quill clipboard containers`);
            
            // Remove any hidden or display:none elements that Quill might add
            const hiddenElements = tempDiv.querySelectorAll('[style*="display: none"], [style*="display:none"]');
            hiddenElements.forEach(el => el.remove());
            console.log(`Removed ${{hiddenElements.length}} hidden elements`);
            
            // Remove Quill-specific attributes but PRESERVE all CSS classes
            const allElements = tempDiv.querySelectorAll('*');
            allElements.forEach(element => {{
                // PRESERVE all class attributes (Quill classes and user custom classes)
                // Remove data-* attributes EXCEPT data-s3-key and data-inline (needed for image processing)
                Array.from(element.attributes).forEach(attr => {{
                    if (attr.name.startsWith('data-') && 
                        attr.name !== 'data-s3-key' && 
                        attr.name !== 'data-inline') {{
                        element.removeAttribute(attr.name);
                    }}
                }});
                // Remove contenteditable attributes
                element.removeAttribute('contenteditable');
                // Remove spellcheck attributes
                element.removeAttribute('spellcheck');
                // Remove autocorrect attributes
                element.removeAttribute('autocorrect');
                // Remove autocapitalize attributes
                element.removeAttribute('autocapitalize');
            }});
            console.log('✅ Cleaned Quill attributes (preserved ALL CSS classes)');
            
            // DEBUG: Check what images exist before upload attempt
            const allImages = tempDiv.querySelectorAll('img');
            console.log(`🔍 Total images in tempDiv after cleanup: ${{allImages.length}}`);
            allImages.forEach((img, i) => {{
                const src = img.getAttribute('src');
                const dataS3Key = img.getAttribute('data-s3-key');
                console.log(`  Image ${{i + 1}}: src type=${{src ? src.substring(0, 20) : 'NO SRC'}}..., has data-s3-key=${{!!dataS3Key}}`);
            }});
            // IMPORTANT: Convert embedded images (base64 data URIs) to attachments
            // This allows inline images in the email body
            const allImgTags = tempDiv.querySelectorAll('img[src^="data:"], img[src^="blob:"]');
            console.log(`🔍 Images with data:/blob: URIs to upload: ${{allImgTags.length}}`);
            
            if (allImgTags.length > 0) {{
                console.log(`🖼️ Found ${{allImgTags.length}} embedded image(s) in email body`);
                
                // Check if upload endpoint is available first
                const ENABLE_INLINE_IMAGES = true;  // Set to false to disable automatic uploads
                
                if (!ENABLE_INLINE_IMAGES) {{
                    // Remove embedded images and show error
                    allImgTags.forEach(img => img.remove());
                    throw new Error(
                        `Embedded images are not supported.\\n\\n` +
                        `Please use the "📎 Add Attachments" button to attach images instead.\\n\\n` +
                        `To enable inline images, run: python add_attachment_endpoint.py`
                    );
                }}
                
                console.log(`Converting ${{allImgTags.length}} embedded image(s) to inline attachments...`);
                
                // Show progress to user
                button.textContent = `Uploading ${{allImgTags.length}} embedded image(s)...`;
                
                for (let index = 0; index < allImgTags.length; index++) {{
                    // Update progress
                    button.textContent = `Uploading embedded image ${{index + 1}}/${{allImgTags.length}}...`;
                    const img = allImgTags[index];
                    const dataUri = img.src;
                    const altText = img.alt || img.title || `InlineImage${{index + 1}}`;
                    
                    try {{
                        console.log(`Processing embedded image ${{index + 1}}/${{allImgTags.length}}`);
                        
                        // Extract base64 data from data URI
                        const matches = dataUri.match(/^data:([^;]+);base64,(.+)$/);
                        if (!matches) {{
                            console.warn(`Skipping invalid data URI for image ${{index}}`);
                            continue;
                        }}
                        
                        const mimeType = matches[1];
                        const base64Data = matches[2];
                        
                        console.log(`  MIME type: ${{mimeType}}`);
                        console.log(`  Base64 length: ${{base64Data.length}} chars`);
                        
                        // Determine file extension from MIME type
                        const extension = mimeType.split('/')[1] || 'png';
                        const filename = `${{altText.replace(/[^a-zA-Z0-9]/g, '_')}}_${{Date.now()}}_${{index}}.${{extension}}`;
                        
                        // Generate S3 key for this image
                        const timestamp = Date.now();
                        const randomStr = Math.random().toString(36).substring(7);
                        const s3Key = `campaign-attachments/${{timestamp}}-${{randomStr}}-${{filename}}`;
                        
                        console.log(`  Generated filename: ${{filename}}`);
                        console.log(`  S3 key: ${{s3Key}}`);
                        console.log(`  Uploading to ${{API_URL}}/upload-attachment...`);
                        
                        // Upload to S3 via backend (using same format as regular attachments)
                        const uploadResponse = await fetch(`${{API_URL}}/upload-attachment`, {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                filename: filename,
                                content_type: mimeType,
                                s3_key: s3Key,
                                data: base64Data  // Already extracted above
                            }})
                        }});
                        
                        console.log(`  Upload response status: ${{uploadResponse.status}} ${{uploadResponse.statusText}}`);
                        
                        // Get response text first to handle HTML error responses
                        const responseText = await uploadResponse.text();
                        
                        if (!uploadResponse.ok) {{
                            console.error(`❌ Upload failed with status ${{uploadResponse.status}}: ${{uploadResponse.statusText}}`);
                            console.error(`Response body (first 500 chars): ${{responseText.substring(0, 500)}}`);
                            
                            // Handle specific error codes
                            if (uploadResponse.status === 403) {{
                                throw new Error(
                                    `Upload Failed: 403 Forbidden\\n\\n` +
                                    `The /upload-attachment endpoint is blocked by API Gateway.\\n\\n` +
                                    `SOLUTIONS:\\n` +
                                    `1. Run: python add_attachment_endpoint.py\\n` +
                                    `   (This adds the endpoint to API Gateway)\\n\\n` +
                                    `2. OR deploy API Gateway:\\n` +
                                    `   python deploy_api_gateway.py\\n\\n` +
                                    `3. OR check API Gateway resource policy for restrictions`
                                );
                            }} else if (uploadResponse.status === 404) {{
                                throw new Error(
                                    `Upload Failed: 404 Not Found\\n\\n` +
                                    `The /upload-attachment endpoint does not exist.\\n\\n` +
                                    `Run: python add_attachment_endpoint.py`
                                );
                            }} else {{
                                throw new Error(`Upload failed (${{uploadResponse.status}}): ${{uploadResponse.statusText}}`);
                            }}
                        }}
                        
                        // Try to parse as JSON
                        let uploadResult;
                        try {{
                            uploadResult = JSON.parse(responseText);
                        }} catch (parseError) {{
                            console.error('Failed to parse upload response as JSON:', responseText.substring(0, 500));
                            throw new Error(`Upload endpoint returned invalid response (expected JSON, got HTML). Check Lambda logs.`);
                        }}
                        
                        if (uploadResult.error) {{
                            throw new Error(uploadResult.error);
                        }}
                        
                        console.log(`✅ Uploaded embedded image: ${{uploadResult.s3_key}}`);
                        
                        // Add to campaign attachments with inline flag
                        campaignAttachments.push({{
                            filename: uploadResult.filename,
                            s3_key: uploadResult.s3_key,
                            size: uploadResult.size,
                            type: uploadResult.type,
                            inline: true  // Mark as inline image
                        }});
                        
                        // Store S3 key as data attribute for reference, but KEEP the data URI for display
                        // The browser needs the data: URI to display the image in the editor
                        // Email worker will use the S3 key to fetch and embed the image
                        img.setAttribute('data-s3-key', uploadResult.s3_key);
                        img.setAttribute('data-inline', 'true');
                        // Keep img.src as data URI so image still displays in editor
                        
                    }} catch (uploadError) {{
                        console.error(`Failed to upload embedded image ${{index}}:`, uploadError);
                        // Keep the image but show warning
                        alert(`⚠️ Failed to upload embedded image "${{altText}}": ${{uploadError.message}}\\n\\nThe image will be removed from the email.`);
                        img.remove();
                    }}
                }}
                
                console.log(`✅ Converted ${{allImgTags.length}} embedded image(s) to inline attachments`);
                
                // Reset button text
                button.textContent = 'Sending Campaign...';
            }} else {{
                console.log(`ℹ️ No data:/blob: images found to upload (might already be uploaded)`);
                
                // Check for images that might have been uploaded previously
                const imagesWithS3src = tempDiv.querySelectorAll('img[src^="campaign-attachments/"]');
                if (imagesWithS3src.length > 0) {{
                    console.log(`♻️ Found ${{imagesWithS3src.length}} image(s) already uploaded to S3`);
                    
                    // Add these to campaignAttachments if not already there
                    imagesWithS3src.forEach((img, idx) => {{
                        const s3Key = img.getAttribute('src');
                        const alreadyExists = campaignAttachments.some(att => att.s3_key === s3Key);
                        
                        if (!alreadyExists) {{
                            console.log(`   Adding existing S3 image to attachments: ${{s3Key}}`);
                            campaignAttachments.push({{
                                filename: `ExistingImage${{idx + 1}}.png`,
                                s3_key: s3Key,
                                size: 0,  // Unknown size
                                type: 'image/png',
                                inline: true
                            }});
                        }} else {{
                            console.log(`   S3 image already in attachments: ${{s3Key}}`);
                        }}
                    }});
                }}
            }}
            
            // NOTE: Removed trailing image cleanup code - it was removing legitimate user images
            // Users can have images at the end of their emails intentionally

            // Get cleaned HTML (with data: URIs still intact or S3 keys if already uploaded)
            emailBody = tempDiv.innerHTML;
            
            // DEBUG: Check if tempDiv.innerHTML contains img tags
            const imgInTempDivHTML = emailBody.match(/<img[^>]+>/g);
            if (imgInTempDivHTML) {{
                console.log(`✅ tempDiv.innerHTML contains ${{imgInTempDivHTML.length}} <img> tag(s)`);
                imgInTempDivHTML.forEach((tag, i) => {{
                    console.log(`  ${{i + 1}}. ${{tag.substring(0, 120)}}...`);
                }});
            }} else {{
                console.error(`❌ tempDiv.innerHTML has NO <img> tags!`);
                console.error(`   tempDiv content (first 500 chars): ${{emailBody.substring(0, 500)}}...`);
            }}
            
            // Replace data: URIs with S3 keys for backend transmission
            // Do this via string replacement to avoid triggering browser image loads
            const imagesWithS3Keys = tempDiv.querySelectorAll('img[data-s3-key]');
            if (imagesWithS3Keys.length > 0) {{
                console.log(`📸 Replacing ${{imagesWithS3Keys.length}} data: URI(s) with S3 keys in HTML string`);
                console.log(`Email body length before replacement: ${{emailBody.length}}`);
                
                imagesWithS3Keys.forEach((img, idx) => {{
                    const s3Key = img.getAttribute('data-s3-key');
                    const currentSrc = img.getAttribute('src');
                    
                    console.log(`Image ${{idx + 1}}:`);
                    console.log(`  Current src: ${{currentSrc.substring(0, 80)}}...`);
                    console.log(`  S3 key: ${{s3Key}}`);
                    
                    if (s3Key && currentSrc && currentSrc.startsWith('data:')) {{
                        // Use string replacement to avoid browser fetching the image
                        // Escape special regex characters in the data URI
                        const escapedSrc = currentSrc.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
                        const regex = new RegExp('src="' + escapedSrc + '"', 'g');
                        const beforeLength = emailBody.length;
                        emailBody = emailBody.replace(regex, 'src="' + s3Key + '"');
                        const afterLength = emailBody.length;
                        
                        if (beforeLength !== afterLength) {{
                            console.log(`  ✅ Replaced in HTML (length changed: ${{beforeLength}} → ${{afterLength}})`);
                        }} else {{
                            console.warn(`  ⚠️ No replacement made (length unchanged)`);
                        }}
                        
                        console.log(`  New src will be: ${{s3Key}}`);
                    }}
                }});
                
                // Show sample of HTML with S3 keys
                console.log(`Email body sample after S3 replacement: ${{emailBody.substring(0, 300)}}...`);
                
                // Verify replacement happened
                if (emailBody.includes('data:image')) {{
                    console.error('⚠️ WARNING: Email body still contains data:image URIs after replacement!');
                    console.error('This will cause issues. The frontend replacement may have failed.');
                }} else {{
                    console.log('✅ Confirmed: No data:image URIs in email body (all replaced with S3 keys)');
                }}
                
                // Now remove data-s3-key attributes from final HTML (no longer needed)
                emailBody = emailBody.replace(/\\s+data-s3-key="[^"]*"/g, '');
                emailBody = emailBody.replace(/\\s+data-inline="[^"]*"/g, '');
                console.log('✅ Removed data-s3-key attributes from final HTML');
                
                // Verify img tags still exist after cleanup
                const imgAfterCleanup = emailBody.match(/<img[^>]+>/g);
                if (imgAfterCleanup) {{
                    console.log(`✅ After data-attr cleanup: ${{imgAfterCleanup.length}} <img> tag(s) still present`);
                }} else {{
                    console.error(`❌ After data-attr cleanup: <img> tags were LOST!`);
                }}
            }} else {{
                console.log('ℹ️ No images with S3 keys to replace');
            }}
            
            // Additional regex cleanup for any remaining artifacts
            // IMPORTANT: Preserve blank lines by converting <p><br></p> to <p>&nbsp;</p>
            const bodyBeforeRegexCleanup = emailBody;
            emailBody = emailBody
                .replace(/<p>\\s*<br\\s*\\/?\\s*>\\s*<\\/p>/g, '<p>&nbsp;</p>')  // Preserve blank lines as &nbsp;
                .replace(/<p>\\s*<\\/p>/g, '')  // Remove truly empty paragraphs (no content, no br)
                .replace(/<br>\\s*<br>/g, '<br>')  // Remove double line breaks (reduce to single)
                // PRESERVE class attributes (user custom classes and Quill classes)
                .replace(/\\s+data-[^=]*="[^"]*"/g, '')  // Remove all data-* attributes (S3 keys already in src)
                .trim();
            
            console.log('✅ Applied HTML cleanup and preserved blank lines as <p>&nbsp;</p>');
            
            // Add margin: 0 to all <p> tags for tight spacing
            // Line-height is controlled by .ql-size-* classes (0.9 for small, 1.2 for large, 1.3 for huge)
            emailBody = emailBody.replace(/<p>/g, '<p style="margin: 0;">');
            emailBody = emailBody.replace(/<p([^>]*?)style="([^"]*)"([^>]*)>/g, function(match, before, style, after) {{
                // Only add margin if not already present
                if (!style.includes('margin')) {{
                    return `<p${{before}}style="${{style}}; margin: 0;"${{after}}>`;
                }}
                return match;
            }});
            console.log('✅ Added margin: 0 to <p> tags (line-height controlled by size classes)');
            
            // Add Quill CSS styles to email body so Quill classes work in recipient emails
            const quillCSS = `<style type="text/css">
    /* Quill Editor Styles for Email Compatibility */
    .ql-align-center {{ text-align: center; }}
    .ql-align-right {{ text-align: right; }}
    .ql-align-left {{ text-align: left; }}
    .ql-align-justify {{ text-align: justify; }}
    .ql-indent-1 {{ padding-left: 3em; }}
    .ql-indent-2 {{ padding-left: 6em; }}
    .ql-indent-3 {{ padding-left: 9em; }}
    .ql-size-small {{ font-size: 0.75em; line-height: 0.9; }}
    .ql-size-large {{ font-size: 1.5em; line-height: 1.2; }}
    .ql-size-huge {{ font-size: 2.5em; line-height: 1.3; }}
    .ql-font-arial {{ font-family: Arial, sans-serif; }}
    .ql-font-times-new-roman {{ font-family: 'Times New Roman', Times, serif; }}
    .ql-font-courier-new {{ font-family: 'Courier New', Courier, monospace; }}
    .ql-font-georgia {{ font-family: Georgia, serif; }}
    .ql-font-verdana {{ font-family: Verdana, sans-serif; }}
    .ql-font-comic-sans {{ font-family: 'Comic Sans MS', cursive; }}
    .ql-font-trebuchet {{ font-family: 'Trebuchet MS', sans-serif; }}
    .ql-font-impact {{ font-family: Impact, sans-serif; }}
    /* Default paragraph spacing - size classes override line-height */
    p {{ line-height: 1.2; margin: 0; }}
</style>`;
            
            // Prepend CSS to email body
            emailBody = quillCSS + emailBody;
            console.log('✅ Added Quill CSS styles to email for class rendering');
            
            console.log(`Final email body preview: ${{emailBody.substring(0, 200)}}...`);
            
            // Verify img tags survived the regex cleanup
            const imgAfterRegexCleanup = emailBody.match(/<img[^>]+>/g);
            if (bodyBeforeRegexCleanup.includes('<img') && !imgAfterRegexCleanup) {{
                console.error(`❌ CRITICAL: <img> tags were REMOVED during regex cleanup!`);
                console.error(`   Before cleanup: ${{bodyBeforeRegexCleanup.substring(0, 300)}}...`);
                console.error(`   After cleanup: ${{emailBody.substring(0, 300)}}...`);
            }} else if (imgAfterRegexCleanup) {{
                console.log(`✅ After regex cleanup: ${{imgAfterRegexCleanup.length}} <img> tag(s) still present`);
            }}
            
            // Get user name from form
            const userName = document.getElementById('userName').value.trim() || 'Web User';
            
            // Read To/CC/BCC inputs and parse into arrays (normalize to lowercase for deduplication)
            const toList = parseEmails(document.getElementById('campaignTo')?.value || '').map(e => e.toLowerCase());
            const ccList = parseEmails(document.getElementById('campaignCc')?.value || '').map(e => e.toLowerCase());
            const bccList = parseEmails(document.getElementById('campaignBcc')?.value || '').map(e => e.toLowerCase());
            
            // 📧 ENHANCED LOGGING: Display To/CC/BCC lines in web UI console
            // 📧 ENHANCED LOGGING: Display To/CC/BCC lines in web UI console
            console.log('📧 EMAIL RECIPIENTS - WEB UI LOGGING:');
            console.log('=' .repeat(50));
            console.log('📬 To Recipients:', toList.length > 0 ? toList : 'None');
            console.log('📋 CC Recipients:', ccList.length > 0 ? ccList : 'None');
            console.log('🔒 BCC Recipients:', bccList.length > 0 ? bccList : 'None');
            console.log('📊 Total Recipients: To=' + toList.length + ', CC=' + ccList.length + ', BCC=' + bccList.length);
            console.log('=' .repeat(50));
            
            // 📧 VISUAL DEBUG DISPLAY: Show recipients in the UI temporarily
            let debugResultDiv = document.getElementById('campaignResult');
            if (debugResultDiv && (toList.length > 0 || ccList.length > 0 || bccList.length > 0)) {{
                debugResultDiv.innerHTML = `
                    <div style="background: var(--info-color); color: white; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <h4 style="margin: 0 0 10px 0;">📧 Campaign Recipients Debug</h4>
                        <div style="font-family: monospace; font-size: 0.9em;">
                            <div><strong>📬 To Recipients (${{toList.length}}):</strong> ${{toList.length > 0 ? toList.join(', ') : 'None'}}</div>
                            <div><strong>📋 CC Recipients (${{ccList.length}}):</strong> ${{ccList.length > 0 ? ccList.join(', ') : 'None'}}</div>
                            <div><strong>🔒 BCC Recipients (${{bccList.length}}):</strong> ${{bccList.length > 0 ? bccList.join(', ') : 'None'}}</div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.8em; opacity: 0.9;">
                            This debug info will be replaced when the campaign is sent...
                        </div>
                    </div>
                `;
            }}
            
            // 📧 TOAST NOTIFICATION: Show recipients summary
            // if (toList.length > 0 || ccList.length > 0 || bccList.length > 0) {{
            //     const recipientSummary = `To: ${{toList.length}}, CC: ${{ccList.length}}, BCC: ${{bccList.length}}`;
            //     Toast.info(`📧 Recipients: ${{recipientSummary}}`, 4000);
            // }}
            
            // Extract and validate email addresses from contacts (normalize to lowercase)
            const targetEmails = targetContacts.map(c => c?.email).filter(email => email && email.includes('@')).map(e => e.toLowerCase());
            // If user provided explicit To addresses, include them as targets (they may be external or not in Contacts DB)
            if (toList.length > 0) {{
                console.log('Using explicit To list with ' + toList.length + ' addresses');
            }}
            console.log('Extracted ' + targetEmails.length + ' valid emails from ' + targetContacts.length + ' contacts');
            
            // Combine contact-derived targets with explicit To addresses (but NOT CC/BCC - they're handled separately)
            let primaryTargetEmails = [...new Set([...targetEmails, ...toList])];
            
            // Total recipients for validation (includes CC/BCC for counting)
            let allTargetEmails = [...new Set([...targetEmails, ...toList, ...ccList, ...bccList])];
            
            console.log('Primary targets (contacts + To): ' + primaryTargetEmails.length + ' (Contacts: ' + targetEmails.length + ', To: ' + toList.length + ')');
            console.log('Total recipients including CC/BCC: ' + allTargetEmails.length + ' (CC: ' + ccList.length + ', BCC: ' + bccList.length + ')');
            console.log('Sample primary targets:', primaryTargetEmails.slice(0, 5));
            
            if (allTargetEmails.length === 0) {{
                throw new Error('No recipients specified. Please select contacts or add To/CC/BCC recipients.');
            }}
            
            if (primaryTargetEmails.length === 0 && ccList.length === 0 && bccList.length === 0) {{
                throw new Error('No recipients specified. Please select contacts or add To/CC/BCC recipients.');
            }}

            // CONFIRMATION POPUP - Show total recipient count and ask for confirmation
            const confirmationMessage = `
📧 Campaign Confirmation
You are about to send this campaign to:

📊 Total Recipients: ${{allTargetEmails.length}}

Breakdown:
• Contacts from database: ${{targetEmails.length}}
• To recipients: ${{toList.length}}
• CC recipients: ${{ccList.length}}
• BCC recipients: ${{bccList.length}}

Filter: ${{filterDescription}}

⚠️ Are you sure you want to send this campaign?

Click OK to proceed or Cancel to abort.
            `.trim();
            
            // Show confirmation dialog and wait for user response
            const userConfirmed = confirm(confirmationMessage);
            
            if (!userConfirmed) {{
                // User clicked Cancel
                button.textContent = originalText;
                button.classList.remove('loading');
                button.disabled = false;
                console.log('Campaign send cancelled by user');
                return; // Exit without sending
            }}
            
            console.log('User confirmed campaign send');
            
            // Log final email body for debugging
            console.log(`📧 Final email body length: ${{emailBody.length}} characters`);
            console.log(`📧 Email body sample (first 500 chars): ${{emailBody.substring(0, 500)}}...`);
            
            // Show image tags in email body
            const imgMatches = emailBody.match(/<img[^>]+>/g);
            if (imgMatches) {{
                console.log(`🖼️ Email body contains ${{imgMatches.length}} <img> tag(s):`);
                imgMatches.forEach((tag, i) => {{
                    console.log(`  ${{i + 1}}. ${{tag.substring(0, 120)}}...`);
                }});
            }} else {{
                console.log(`⚠️ No <img> tags found in email body!`);
            }}
            
            console.log(`📎 Campaign attachments: ${{campaignAttachments.length}}`);
            if (campaignAttachments.length > 0) {{
                console.log(`📎 Attachment details:`);
                campaignAttachments.forEach((att, i) => {{
                    console.log(`  ${{i + 1}}. ${{att.filename}} (s3_key: ${{att.s3_key}}, inline: ${{att.inline}})`);
                }});
            }}
            
            // Log font usage before sending campaign
            console.log('🎨 CAMPAIGN FONT ANALYSIS: Analyzing fonts used in email...');
            const fontMatches = emailBody.match(/class="[^"]*ql-font-([^"\s]+)/g) || [];
            const fontUsage = {{}};
            
            fontMatches.forEach(match => {{
                const fontMatch = match.match(/ql-font-([^"\s]+)/);
                if (fontMatch) {{
                    const font = fontMatch[1];
                    fontUsage[font] = (fontUsage[font] || 0) + 1;
                }}
            }});
            
            if (Object.keys(fontUsage).length > 0) {{
                console.log('🎨 FONTS BEING SENT TO RECIPIENTS:');
                Object.entries(fontUsage).forEach(([font, count]) => {{
                    console.log(`   • ${{font}}: ${{count}} occurrence(s)`);
                }});
            }} else {{
                console.log('🎨 FONTS BEING SENT: Default font only (no custom fonts detected)');
            }}
            
            const campaign = {{
                campaign_name: document.getElementById('campaignName').value,
                subject: document.getElementById('subject').value,
                body: emailBody,
                font_usage: fontUsage,  // Add font usage to campaign data
                launched_by: userName,                                                                 //Send user identity to backend
                filter_type: Object.keys(selectedCampaignFilterValues).length > 0 ? 'custom' : null,
                filter_values: Object.keys(selectedCampaignFilterValues).length > 0 ? JSON.stringify(selectedCampaignFilterValues): null,
                filter_description: filterDescription,
                // Send only primary targets (contacts + To) - CC/BCC handled separately by backend
                to: toList,
                target_contacts: primaryTargetEmails,  // Send only contacts + To addresses (NOT CC/BCC)
                cc: ccList,   // array of CC emails (backend will queue these separately)
                bcc: bccList, // array of BCC emails (backend will queue these separately)
                attachments: campaignAttachments  // Include attachments
            }};
            
            // 📡 CAMPAIGN DATA LOGGING
            console.log('📡 CAMPAIGN DATA PREPARED:');
            console.log('   Campaign Name:', campaign.campaign_name);
            console.log('   Subject:', campaign.subject);
            console.log('   Body Length:', campaign.body ? campaign.body.length : 0, 'characters');
            console.log('   Filter Description:', campaign.filter_description);
            console.log('   Target Contacts:', campaign.target_contacts.length, 'addresses');
            console.log('   To Recipients:', campaign.to.length, 'addresses');
            console.log('   CC Recipients:', campaign.cc.length, 'addresses');
            console.log('   BCC Recipients:', campaign.bcc.length, 'addresses');
            console.log('   Attachments:', campaign.attachments.length, 'files');
            console.log('   Full Campaign Object:', campaign);
                
                // Validate required fields
                if (!campaign.campaign_name || !campaign.subject || !campaign.body) {{
                    throw new Error('Please fill in all required fields');
                }}
                
                // Validate attachment size
                const totalAttachmentSize = campaignAttachments.reduce((sum, att) => sum + att.size, 0);
                if (totalAttachmentSize > MAX_ATTACHMENT_SIZE) {{
                    throw new Error(`Attachments exceed 40 MB limit (${{(totalAttachmentSize / 1024 / 1024).toFixed(2)}} MB)`);
                }}
            
            // Debug: Log campaign object before serialization
            console.log('Campaign object:', {{
                campaign_name: campaign.campaign_name,
                subject: campaign.subject,
                body_length: campaign.body?.length || 0,
                attachments_count: campaign.attachments?.length || 0,
                target_contacts_count: campaign.target_contacts?.length || 0
            }});
            
            // DEBUG: Verify img tags are in campaign.body before serialization
            const imgInCampaignBody = campaign.body.match(/<img[^>]+>/g);
            if (imgInCampaignBody) {{
                console.log(`🔍 BEFORE JSON: campaign.body has ${{imgInCampaignBody.length}} <img> tag(s)`);
            }} else {{
                console.error(`❌ BEFORE JSON: campaign.body has NO <img> tags!`);
                console.error(`   Body content: ${{campaign.body.substring(0, 300)}}...`);
            }}
            
            // Try to serialize campaign to JSON - catch errors early
            let campaignJSON;
            try {{
                campaignJSON = JSON.stringify(campaign);
                console.log(`✅ Campaign JSON serialized successfully`);
                console.log(`   Size: ${{(campaignJSON.length / 1024).toFixed(2)}} KB`);
                console.log(`   Body size: ${{(campaign.body?.length || 0 / 1024).toFixed(2)}} KB`);
                console.log(`   Attachments: ${{campaign.attachments?.length || 0}}`);
                
                // DEBUG: Check if img tags survived JSON serialization
                if (campaignJSON.includes('<img')) {{
                    console.log(`🔍 AFTER JSON: Serialized data contains <img> tags ✅`);
                }} else {{
                    console.error(`❌ AFTER JSON: Serialized data has NO <img> tags!`);
                }}
                
                // Warn if body is very large
                if (campaignJSON.length > 5000000) {{ // 5MB
                    console.warn(`⚠️ Campaign data is very large (${{(campaignJSON.length / 1024 / 1024).toFixed(2)}} MB)`);
                }}
            }} catch (jsonError) {{
                console.error('❌ JSON serialization error:', jsonError);
                console.error('Campaign object:', campaign);
                throw new Error(
                    `Failed to prepare campaign data: ${{jsonError.message}}\\n\\n` +
                    `This usually happens when the email contains invalid data.\\n` +
                    `Check browser console for details.`
                );
            }}
            
            console.log(`📤 Sending campaign to backend: ${{API_URL}}/campaign`);
            console.log(`   Campaign JSON size: ${{campaignJSON.length}} characters (${{(campaignJSON.length / 1024).toFixed(2)}} KB)`);
            
            // 📡 ENHANCED REQUEST LOGGING
            console.log('📡 SENDING CAMPAIGN REQUEST:');
            console.log('   URL:', `${{API_URL}}/campaign`);
            console.log('   Method: POST');
            console.log('   Headers:', {{'Content-Type': 'application/json'}});
            console.log('   Body size:', campaignJSON.length, 'characters');
            
            const response = await fetch(`${{API_URL}}/campaign`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: campaignJSON
            }});
            
            // 📡 ENHANCED RESPONSE LOGGING
            console.log('📡 CAMPAIGN RESPONSE RECEIVED:');
            console.log('   Status:', response.status, response.statusText);
            console.log('   Headers:', Object.fromEntries(response.headers.entries()));
            console.log('   OK:', response.ok);
            console.log('   Type:', response.type);
            console.log('   URL:', response.url);
            
            // Get response as text first to handle HTML error pages
            const responseText = await response.text();
            console.log('   Response length:', responseText.length, 'characters');
            console.log('   Response preview (first 200 chars):', responseText.substring(0, 200));
            
            // 📡 DETAILED RESPONSE ANALYSIS
            if (!response.ok) {{
                console.error('📡 ERROR RESPONSE DETAILS:');
                console.error('   Status Code:', response.status);
                console.error('   Status Text:', response.statusText);
                console.error('   Full Response Body:', responseText);
            }}
            
            // Check if response is HTML (error page) instead of JSON
            if (responseText.trim().startsWith('<')) {{
                console.error('📡 SERVER ERROR: HTML response instead of JSON');
                console.error('   Full HTML response:', responseText);
                throw new Error(
                    `Campaign Failed: Server returned an error page instead of JSON response\\n\\n` +
                    `Status: ${{response.status}} ${{response.statusText}}\\n\\n` +
                    `This indicates a backend error. Common causes:\\n` +
                    `• Lambda function error or crash\\n` +
                    `• Missing permissions (S3, DynamoDB, SQS)\\n` +
                    `• Email body too large\\n\\n` +
                    `Check CloudWatch Logs for details:\\n` +
                    `python tail_lambda_logs.py BulkEmailAPI`
                );
            }}
            
            // 📡 JSON PARSING
            let result;
            try {{
                console.log('📡 PARSING RESPONSE AS JSON...');
                result = JSON.parse(responseText);
                console.log('📡 JSON PARSE SUCCESS:');
                console.log('   Parsed result:', result);
                console.log('   Result keys:', Object.keys(result));
                if (result.error) {{
                    console.error('📡 API ERROR IN RESPONSE:', result.error);
                }}
                if (result.success) {{
                    console.log('📡 API SUCCESS:', result.success);
                }}
            }} catch (parseError) {{
                console.error('📡 JSON PARSE ERROR:', parseError);
                console.error('Response text:', responseText.substring(0, 500));
                throw new Error(
                    `Campaign Failed: Invalid server response\\n\\n` +
                    `${{parseError.message}}\\n\\n` +
                    `The server returned: ${{responseText.substring(0, 100)}}...\\n\\n` +
                    `Check CloudWatch Logs: python tail_lambda_logs.py BulkEmailAPI`
                );
            }}
            
            const resultDiv = document.getElementById('campaignResult');
                
                if (result.error) {{
                    console.error('Backend returned error:', result.error);
                    throw new Error(result.error);
                }}
                
                // Create a beautiful result display
                Toast.success('Campaign queued successfully! Emails are being sent.', 6000);
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
                        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--gray-200);">
                            <h4 style="margin: 0 0 10px 0; color: var(--gray-800);">📧 Email Recipients</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                                <div style="background: white; padding: 10px; border-radius: 6px; border-left: 4px solid var(--primary-color);">
                                    <strong style="color: var(--primary-color);">📬 To:</strong><br>
                                    <span style="font-size: 0.9em; color: var(--gray-600);">${{toList.length > 0 ? toList.join(', ') : 'None'}}</span>
                                </div>
                                <div style="background: white; padding: 10px; border-radius: 6px; border-left: 4px solid var(--warning-color);">
                                    <strong style="color: var(--warning-color);">📋 CC:</strong><br>
                                    <span style="font-size: 0.9em; color: var(--gray-600);">${{ccList.length > 0 ? ccList.join(', ') : 'None'}}</span>
                                </div>
                                <div style="background: white; padding: 10px; border-radius: 6px; border-left: 4px solid var(--gray-500);">
                                    <strong style="color: var(--gray-500);">🔒 BCC:</strong><br>
                                    <span style="font-size: 0.9em; color: var(--gray-600);">${{bccList.length > 0 ? bccList.join(', ') : 'None'}}</span>
                                </div>
                            </div>
                        </div>
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
                Toast.error(`Campaign failed: ${{error.message}}`);
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
        
        // Contact filter state
        let currentFilterType = null;  // null = no filter selected, '' = "All" selected, other = specific filter
        let selectedFilterValues = {{}};  // {{filterType: [values]}}
        
        // Helper function to get field value case-insensitively
        function getFieldValue(contact, fieldName) {{
            // Try exact match first
            if (contact[fieldName] !== undefined) {{
                return contact[fieldName];
            }}
            
            // Try case-insensitive search
            const lowerFieldName = fieldName.toLowerCase();
            for (const key in contact) {{
                if (key.toLowerCase() === lowerFieldName) {{
                    return contact[key];
                }}
            }}
            
            return null;
        }}
        
        async function selectFilterType(filterType) {{
            console.log('Filter type selected:', filterType, 'Current type:', currentFilterType);
            
            // Allow toggling off by clicking the same button (including "All")
            if (currentFilterType === filterType) {{
                console.log('Toggling off current filter type');
                currentFilterType = null;
                document.getElementById('availableValuesArea').style.display = 'none';
                updateButtonStyles(null);  // Reset all buttons to unselected state
                return;
            }}
            
            currentFilterType = filterType;
            updateButtonStyles(filterType);
            
            if (!filterType || filterType === '') {{
                // "All" selected - hide available values area
                document.getElementById('availableValuesArea').style.display = 'none';
                return;
            }}
            
            // Show loading message
            const availableValuesList = document.getElementById('availableValuesList');
            availableValuesList.innerHTML = '<div style="padding: 20px; text-align: center; color: #6b7280;"><span style="font-size: 14px;">⏳ Loading values from DynamoDB...</span></div>';
            document.getElementById('availableCount').textContent = 'Querying database...';
            document.getElementById('availableValuesArea').style.display = 'block';
            
            try {{
                console.log(`Querying DynamoDB for distinct values of field: ${{filterType}}`);
                
                // Call the backend API to get distinct values from DynamoDB
                const response = await fetch(`${{API_URL}}/contacts/distinct?field=${{encodeURIComponent(filterType)}}`);
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const result = await response.json();
                const distinctValues = result.values || [];
                
                console.log(`Received ${{distinctValues.length}} distinct values for ${{filterType}} from DynamoDB`);
                
                if (distinctValues.length === 0) {{
                    availableValuesList.innerHTML = '<div style="padding: 20px; text-align: center; color: #9ca3af;"><span style="font-size: 13px;">No values found for this field</span></div>';
                    document.getElementById('availableCount').textContent = 'No values available';
                    return;
                }}
                
                // Display available values as clickable buttons
                availableValuesList.innerHTML = '';
                
                distinctValues.forEach(value => {{
                    const btn = document.createElement('button');
                    btn.className = 'available-value-btn';
                    btn.textContent = value;
                    btn.onclick = () => addFilterValue(filterType, value);
                    btn.style.cssText = 'padding: 6px 12px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s; color: #374151;';
                    btn.onmouseover = () => {{ btn.style.background = '#eff6ff'; btn.style.borderColor = '#6366f1'; }};
                    btn.onmouseout = () => {{ btn.style.background = 'white'; btn.style.borderColor = '#cbd5e1'; }};
                    availableValuesList.appendChild(btn);
                }});
                
                document.getElementById('availableCount').textContent = `${{distinctValues.length}} values available`;
                
            }} catch (error) {{
                console.error('Error loading distinct values:', error);
                availableValuesList.innerHTML = `<div style="padding: 20px; text-align: center; color: #ef4444;"><span style="font-size: 13px;">❌ Error loading values: ${{error.message}}</span></div>`;
                document.getElementById('availableCount').textContent = 'Error loading values';
            }}
        }}
        
        function updateButtonStyles(filterType) {{
            // Update button styles based on selected filter type
            document.querySelectorAll('.filter-type-btn').forEach(btn => {{
                const btnFilter = btn.getAttribute('data-filter');
                
                if (filterType === null) {{
                    // Nothing selected - all buttons unselected
                    btn.style.background = 'white';
                    btn.style.borderColor = '#e5e7eb';
                    btn.style.color = '#374151';
                }} else if (btnFilter === filterType && filterType !== '') {{
                    // Selected filter type (not "All")
                    btn.style.background = '#6366f1';
                    btn.style.borderColor = '#6366f1';
                    btn.style.color = 'white';
                }} else if (filterType === '' && btnFilter === '') {{
                    // "All" button selected
                    btn.style.background = '#10b981';
                    btn.style.borderColor = '#10b981';
                    btn.style.color = 'white';
                }} else {{
                    // Unselected buttons
                    btn.style.background = 'white';
                    btn.style.borderColor = '#e5e7eb';
                    btn.style.color = '#374151';
                }}
            }});
        }}
        
        function addFilterValue(filterType, value) {{
            console.log('Adding filter value:', filterType, value);
            
            // Initialize array if needed
            if (!selectedFilterValues[filterType]) {{
                selectedFilterValues[filterType] = [];
            }}
            
            // Don't add duplicates
            if (selectedFilterValues[filterType].includes(value)) {{
                console.log('Value already selected');
                return;
            }}
            
            selectedFilterValues[filterType].push(value);
            updateSelectedValuesTags();
        }}
        
        function removeFilterValue(filterType, value) {{
            console.log('Removing filter value:', filterType, value);
            
            if (selectedFilterValues[filterType]) {{
                selectedFilterValues[filterType] = selectedFilterValues[filterType].filter(v => v !== value);
                
                // Remove filter type if no values left
                if (selectedFilterValues[filterType].length === 0) {{
                    delete selectedFilterValues[filterType];
                }}
            }}
            
            updateSelectedValuesTags();
        }}
        
        function updateSelectedValuesTags() {{
            const tagsContainer = document.getElementById('selectedValuesTags');
            tagsContainer.innerHTML = '';
            
            let hasValues = false;
            
            // Display all selected values as tags
            for (const [filterType, values] of Object.entries(selectedFilterValues)) {{
                if (values && values.length > 0) {{
                    hasValues = true;
                    
                    // Get filter type label
                    const filterLabels = {{
                        'entity_type': 'Entity Type',
                        'state': 'State',
                        'agency_name': 'Agency',
                        'sector': 'Sector',
                        'subsection': 'Sub-section',
                        'ms_isac_member': 'MS-ISAC Member',
                        'soc_call': 'SOC Call',
                        'fusion_center': 'Fusion Center',
                        'k12': 'K-12',
                        'water_wastewater': 'Water/Wastewater',
                        'weekly_rollup': 'Weekly Rollup',
                        'region': 'Region'
                    }};
                    
                    const label = filterLabels[filterType] || filterType;
                    
                    values.forEach(value => {{
                        const tag = document.createElement('div');
                        tag.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; background: #6366f1; color: white; border-radius: 6px; font-size: 13px; font-weight: 500;';
                        tag.innerHTML = `
                            <span style="font-size: 11px; opacity: 0.9;">${{label}}:</span>
                            <span>${{value}}</span>
                            <button onclick="removeFilterValue('${{filterType}}', '${{value.replace(/'/g, "\\\\'")}}');" style="background: none; border: none; color: white; cursor: pointer; padding: 0 2px; font-size: 16px; line-height: 1; opacity: 0.8;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.8'">
                                ×
                            </button>
                        `;
                        tagsContainer.appendChild(tag);
                    }});
                }}
            }}
            
            if (!hasValues) {{
                tagsContainer.innerHTML = '<small style="color: #9ca3af; font-style: italic;">No filters selected - showing all contacts</small>';
            }}
        }}
        
        function clearAllFilters() {{
            console.log('Clearing all filters');
            selectedFilterValues = {{}};
            currentFilterType = null;
            
            // Reset all buttons to unselected state
            updateButtonStyles(null);
            
            // Hide available values
            document.getElementById('availableValuesArea').style.display = 'none';
            
            // Clear tags
            updateSelectedValuesTags();
            
            // Show all contacts
            displayContacts(allContacts);
        }}
        
        // Font monitoring and logging functions
        function logFontUsage() {{
            if (!quillEditor) return;
            
            const content = quillEditor.root.innerHTML;
            const fontClasses = content.match(/class="[^"]*ql-font-([^"\s]+)/g) || [];
            const fontCounts = {{}};
            
            fontClasses.forEach(match => {{
                const font = match.match(/ql-font-([^"\s]+)/)[1];
                fontCounts[font] = (fontCounts[font] || 0) + 1;
            }});
            
            if (Object.keys(fontCounts).length > 0) {{
                console.log('🎨 CURRENT FONT USAGE IN EDITOR:');
                Object.entries(fontCounts).forEach(([font, count]) => {{
                    console.log(`   • ${{font}}: ${{count}} occurrence(s)`);
                }});
            }} else {{
                console.log('🎨 CURRENT FONT USAGE: Default font only');
            }}
            
            return fontCounts;
        }}
        
        function startFontMonitoring() {{
            console.log('🎨 FONT MONITORING: Started real-time font usage tracking');
            
            // Log font usage every 5 seconds when editor has content
            setInterval(() => {{
                if (quillEditor && quillEditor.getLength() > 1) {{
                    const fontUsage = logFontUsage();
                    
                    // Store in session for campaign sending
                    sessionStorage.setItem('currentFontUsage', JSON.stringify(fontUsage));
                }}
            }}, 5000);
        }}
        
        // ============================================
        // CAMPAIGN HISTORY FUNCTIONS
        // ============================================
        
        let currentCampaignId = null;
        let allCampaigns = [];
        window.__historyPrevTokens = [];
        window.__historyNextToken = null;

        function paginateHistory(direction) {{
            if (direction === 'next') {{
                const token = window.__historyNextToken;
                if (token) {{
                    loadCampaignHistory(token);
                }}
            }} else if (direction === 'prev') {{
                const stack = window.__historyPrevTokens || [];
                if (stack.length > 0) {{
                    // Pop current token
                    stack.pop();
                    const prevToken = stack.length > 0 ? stack[stack.length - 1] : null;
                    loadCampaignHistory(prevToken);
                }}
            }}
        }}
        async function loadCampaignHistory(nextToken = null) {{
            const loading = document.getElementById('historyLoading');
            const historyBody = document.getElementById('historyBody');
            const pager = document.getElementById('historyPager');
            if (!nextToken) {{
                // Reset pagination state on fresh load
                window.__historyPrevTokens = [];
                window.__historyNextToken = null;
            }}
            
            loading.style.display = 'block';
            historyBody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center;">Loading...</td></tr>';
            
            try {{
                // Fetch campaigns from DynamoDB via backend
                const url = new URL(`${{API_URL}}/campaigns`);
                if (nextToken) url.searchParams.set('next', nextToken);
                const searchEl = document.getElementById('historySearch');
                const q = (searchEl && searchEl.value ? searchEl.value : '').trim();
                if (q) url.searchParams.set('q', q);
                const response = await fetch(url.toString());
                
                if (!response.ok) {{
                    throw new Error(`Failed to load campaigns: ${{response.statusText}}`);
                }}
                
                const data = await response.json();
                allCampaigns = (data.campaigns || [])
                    .filter(c => c.type !== 'preview' && c.status !== 'preview')
                    .sort((a, b) => {{
                        const dateA = new Date(a.created_at || a.sent_at || 0);
                        const dateB = new Date(b.created_at || b.sent_at || 0);
                        return dateB - dateA;
                    }});
                const nextOut = data.next || null;
                window.__historyNextToken = nextOut; // store for pager
                window.__historyPrevTokens = window.__historyPrevTokens || [];
                if (nextToken) {{
                    // Navigating forward, push current token to prev stack
                    window.__historyPrevTokens.push(nextToken);
                }}
                
                // Filter out preview campaigns and sort by date (newest first)
                if (allCampaigns.length === 0) {{
                    historyBody.innerHTML = '<tr><td colspan="7" style="padding: 40px; text-align: center; color: #9ca3af;">No campaigns found</td></tr>';
                    return;
                }}
                
                // Display campaigns
                historyBody.innerHTML = '';
                allCampaigns.forEach(campaign => {{
                    const row = document.createElement('tr');
                    row.style.borderBottom = '1px solid #e5e7eb';
                    row.style.transition = 'all 0.2s ease';
                    row.onmouseover = function() {{ 
                        this.style.backgroundColor = '#f8fafc'; 
                        this.style.transform = 'scale(1.01)';
                        this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                    }};
                    row.onmouseout = function() {{ 
                        this.style.backgroundColor = ''; 
                        this.style.transform = 'scale(1)';
                        this.style.boxShadow = 'none';
                    }};
                    row.style.cursor = 'pointer';
                    
                    const date = new Date(campaign.created_at || campaign.sent_at);
                    const formattedDate = date.toLocaleString();
                    const recipients = campaign.total_contacts || 0;
                    const status = campaign.status || 'unknown';
                    const launchedBy = campaign.launched_by || 'Unknown';
                    
                    row.innerHTML = `
                        <td style="padding: 16px; color: #1f2937; font-size: 14px; font-weight: 600;">${{campaign.campaign_name || 'Unnamed Campaign'}}</td>
                        <td style="padding: 16px; color: #374151; font-size: 14px; font-weight: 500; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${{campaign.subject || 'No Subject'}}">${{campaign.subject || 'No Subject'}}</td>
                        <td style="padding: 16px; color: #1f2937; font-size: 14px; font-weight: 500; font-family: 'Monaco', monospace;">${{formattedDate}}</td>
                        <td style="padding: 16px; color: #059669; font-size: 14px; font-weight: 600; text-align: center;">${{recipients}}</td>
                        <td style="padding: 16px; text-align: center;">
                            <span style="padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                                background: ${{status === 'completed' ? '#d1fae5' : status === 'processing' ? '#fef3c7' : '#e5e7eb'}};
                                color: ${{status === 'completed' ? '#059669' : status === 'processing' ? '#d97706' : '#6b7280'}};">
                                ${{status.toUpperCase()}}
                            </span>
                        </td>
                        <td style="padding: 16px; color: #1f2937; font-size: 14px; font-weight: 500;">${{launchedBy}}</td>
                        <td style="padding: 16px; text-align: center;">
                            <button onclick="viewCampaignDetails('${{campaign.campaign_id}}'); event.stopPropagation();" 
                                style="padding: 8px 16px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);">
                                👁️ View
                            </button>
                        </td>
                    `;
                    
                    historyBody.appendChild(row);
                }});
                
                Toast.success(`Loaded ${{allCampaigns.length}} campaigns`, 2000);
                // Update pager
                if (pager) {{
                    const hasPrev = (window.__historyPrevTokens || []).length > 0;
                    const hasNext = !!window.__historyNextToken;
                    const pageNum = (window.__historyPrevTokens || []).length + 1;
                    document.getElementById('historyPrevBtn').disabled = !hasPrev;
                    document.getElementById('historyNextBtn').disabled = !hasNext;
                    document.getElementById('historyPageInfo').textContent = `Page ${{pageNum}} • Showing up to 50 campaigns`;
                }}
                
            }} catch (error) {{
                console.error('Error loading campaign history:', error);
                Toast.error(`Failed to load campaigns: ${{error.message}}`);
                historyBody.innerHTML = `<tr><td colspan="7" style="padding: 40px; text-align: center; color: #ef4444;">Error: ${{error.message}}</td></tr>`;
            }} finally {{
                loading.style.display = 'none';
            }}
        }}
        
        async function viewCampaignDetails(campaignId) {{
            currentCampaignId = campaignId;
            try {{
                // Fire-and-forget log to backend so CloudWatch records the view event
                fetch(`${{API_URL}}/campaign-viewed`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ campaign_id: campaignId, timestamp: Date.now() }})
                }}).then(async (r) => {{
                    if (!r.ok) {{
                        // Fallback to existing endpoint that will log view in backend
                        try {{
                            const res2 = await fetch(`${{API_URL}}/campaign/${{campaignId}}`);
                            console.log('📜 View fallback GET /campaign/{id} status=', res2.status);
                        }} catch (e2) {{
                            console.warn('📜 View fallback failed:', e2);
                        }}
                    }} else {{
                        console.log('📜 View log sent for campaign', campaignId, 'status=', r.status);
                    }}
                }}).catch(e => console.warn('📜 View log failed for campaign', campaignId, e));
            }} catch (e) {{
                console.warn('📜 Failed to send view log:', e);
            }}
            
            const campaign = allCampaigns.find(c => c.campaign_id === campaignId);
            if (!campaign) {{
                Toast.error('Campaign not found');
                return;
            }}
            
            // Populate modal with campaign details
            document.getElementById('detailCampaignName').textContent = campaign.campaign_name || 'Unnamed Campaign';
            document.getElementById('detailSubject').textContent = campaign.subject || 'No Subject';
            document.getElementById('detailDate').textContent = new Date(campaign.created_at || campaign.sent_at).toLocaleString();
            document.getElementById('detailLaunchedBy').textContent = campaign.launched_by || 'Unknown';
            
            // Display To, CC, BCC recipients
            const toRecipients = campaign.to || [];
            const ccRecipients = campaign.cc || [];
            const bccRecipients = campaign.bcc || [];
            
            document.getElementById('detailToRecipients').innerHTML = toRecipients.length > 0 
                ? toRecipients.map(email => `<span style="display: inline-block; padding: 4px 8px; margin: 2px; background: #dbeafe; border-radius: 4px; font-size: 12px;">${{email}}</span>`).join('')
                : '<span style="color: #9ca3af; font-style: italic;">None</span>';
            
            document.getElementById('detailCcRecipients').innerHTML = ccRecipients.length > 0
                ? ccRecipients.map(email => `<span style="display: inline-block; padding: 4px 8px; margin: 2px; background: #dcfce7; border-radius: 4px; font-size: 12px;">${{email}}</span>`).join('')
                : '<span style="color: #9ca3af; font-style: italic;">None</span>';
            
            document.getElementById('detailBccRecipients').innerHTML = bccRecipients.length > 0
                ? bccRecipients.map(email => `<span style="display: inline-block; padding: 4px 8px; margin: 2px; background: #fef9c3; border-radius: 4px; font-size: 12px;">${{email}}</span>`).join('')
                : '<span style="color: #9ca3af; font-style: italic;">None</span>';
            
            // Display email body with proper CSS styling
            const emailBody = campaign.body || '';
            
            // Add Quill CSS styles for proper rendering
            const quillCSS = '<style type="text/css">' +
                '.ql-align-center {{ text-align: center; }}' +
                '.ql-align-right {{ text-align: right; }}' +
                '.ql-align-left {{ text-align: left; }}' +
                '.ql-align-justify {{ text-align: justify; }}' +
                '.ql-indent-1 {{ padding-left: 3em; }}' +
                '.ql-indent-2 {{ padding-left: 6em; }}' +
                '.ql-indent-3 {{ padding-left: 9em; }}' +
                '.ql-size-small {{ font-size: 0.75em; }}' +
                '.ql-size-large {{ font-size: 1.5em; }}' +
                '.ql-size-huge {{ font-size: 2.5em; }}' +
                '.ql-font-arial {{ font-family: Arial, sans-serif; }}' +
                '.ql-font-calibri {{ font-family: Calibri, Arial, sans-serif; }}' +
                '.ql-font-cambria {{ font-family: Cambria, Georgia, serif; }}' +
                '.ql-font-times-new-roman {{ font-family: "Times New Roman", serif; }}' +
                '.ql-font-courier-new {{ font-family: "Courier New", monospace; }}' +
                '.ql-font-georgia {{ font-family: Georgia, serif; }}' +
                '.ql-font-verdana {{ font-family: Verdana, sans-serif; }}' +
                '.ql-font-tahoma {{ font-family: Tahoma, sans-serif; }}' +
                '.ql-font-trebuchet-ms {{ font-family: "Trebuchet MS", sans-serif; }}' +
                '.ql-font-helvetica {{ font-family: Helvetica, Arial, sans-serif; }}' +
                '.ql-font-segoe-ui {{ font-family: "Segoe UI", Tahoma, Arial, sans-serif; }}' +
                '.ql-font-open-sans {{ font-family: "Open Sans", Arial, sans-serif; }}' +
                '.ql-font-roboto {{ font-family: "Roboto", Arial, sans-serif; }}' +
                '</style>';
            
            if (emailBody) {{
                // Resolve inline images to presigned URLs before rendering
                console.log('🧩 Starting inline image resolution for campaign:', campaign && campaign.campaign_id);
                const processedBody = await resolveInlineImages(emailBody, campaign.attachments || []);
                console.log('🧩 Inline image resolution complete. Processed body length:', (processedBody || '').length);
                document.getElementById('detailBody').innerHTML = quillCSS + processedBody;
                console.log('🧩 detailBody updated in Campaign Details modal');
            }} else {{
                document.getElementById('detailBody').innerHTML = '<span style="color: #9ca3af; font-style: italic;">No content</span>';
            }}
            
            // Display attachments if present
            const attachments = campaign.attachments || [];
            const attachmentsContainer = document.getElementById('detailAttachments');
            
            if (attachments.length > 0) {{
                let attachmentsHTML = '<strong style="display: block; margin-bottom: 8px;">📎 Attachments (' + attachments.length + '):</strong>';
                attachmentsHTML += '<div style="padding: 15px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb;">';
                attachmentsHTML += '<ul style="margin: 0; padding-left: 20px;">';
                
                attachments.forEach(att => {{
                    const isInline = att.inline ? ' (Inline Image)' : '';
                    const fileSize = att.size ? ' - ' + (att.size / 1024).toFixed(1) + ' KB' : '';
                    const safeFile = (att.filename || 'attachment').replace(/`/g, '');
                    const safeKey = (att.s3_key || '').replace(/`/g, '');
                    attachmentsHTML += `<li style="margin: 6px 0; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                        <span>${{att.filename}}${{fileSize}}${{isInline}}</span>
                        <button onclick="downloadAttachment(\`${{safeKey}}\`, \`${{safeFile}}\`)" style="padding: 6px 12px; background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">⬇️ Download</button>
                    </li>`;
                }});
                
                attachmentsHTML += '</ul></div>';
                attachmentsContainer.innerHTML = attachmentsHTML;
            }} else {{
                attachmentsContainer.innerHTML = '';
            }}
            
            // Show modal
            document.getElementById('campaignDetailsModal').style.display = 'flex';
        }}

        async function resolveInlineImages(html, attachments) {{
            try {{
                console.log('🧩 resolveInlineImages() called. Attachments total:', (attachments || []).length);
                if (!attachments || attachments.length === 0) return html;
                let output = html;
                // Fetch presigned URLs in parallel for inline attachments
                const inlineAttachments = attachments.filter(a => a && a.inline && a.s3_key);
                console.log('🧩 Inline attachments detected:', inlineAttachments.length);
                if (inlineAttachments.length === 0) return output;

                const urlMap = new Map();
                await Promise.all(inlineAttachments.map(async (att) => {{
                    try {{
                        console.log('🧩 Requesting presigned URL for inline image:', att.s3_key, 'filename:', att.filename);
                        const url = new URL(`${{API_URL}}/attachment-url`);
                        url.searchParams.set('s3_key', att.s3_key);
                        if (att.filename) url.searchParams.set('filename', att.filename);
                        // Request inline content-disposition so browsers render in <img>
                        url.searchParams.set('disposition', 'inline');
                        const fullUrl = url.toString();
                        const resp = await fetch(fullUrl);
                        console.log('🧩 Presigned URL request status:', resp.status, 'for', att.s3_key);
                        if (!resp.ok) throw new Error(`URL gen failed (${{resp.status}})`);
                        const data = await resp.json();
                        if (data.url) {{
                            urlMap.set(att, data.url);
                            console.log('🧩 Received presigned URL (truncated):', String(data.url).slice(0, 120) + '...');
                        }} else {{
                            console.warn('🧩 No URL returned for inline image', att && att.s3_key);
                        }}
                    }} catch (e) {{
                        console.warn('Inline image URL generation failed for', att && att.s3_key, e);
                    }}
                }}));

                // Replace references for each inline attachment
                inlineAttachments.forEach((att) => {{
                    const presigned = urlMap.get(att);
                    if (!presigned) return;
                    const s3Key = att.s3_key;
                    const contentId = att.content_id || att.cid || att.contentId;
                    if (contentId) {{
                        console.log('🧩 Replacing inline image by s3_key and cid. s3_key=', s3Key, 'cid=', contentId);
                    }} else {{
                        console.log('🧩 Replacing inline image by s3_key only. s3_key=', s3Key);
                    }}

                    const before = output;
                    // Pattern 1: src="s3_key"
                    output = output.replace(new RegExp(`src=\\"${{s3Key.replace(/[.*+?^$()|[\\]\\\\]/g, '\\$&')}}\\"`, 'g'), `src=\"${{presigned}}\"`);
                    // Pattern 2: src='s3_key'
                    output = output.replace(new RegExp(`src=\'${{s3Key.replace(/[.*+?^$()|[\\]\\\\]/g, '\\$&')}}\'`, 'g'), `src=\"${{presigned}}\"`);
                    // Pattern 3: bare s3_key
                    output = output.split(s3Key).join(presigned);
                    const afterS3 = output;
                    if (afterS3 !== before) {{
                        console.log('🧩 s3_key references replaced for', s3Key);
                    }} else {{
                        console.log('🧩 No s3_key references found for', s3Key);
                    }}

                    // Pattern 4: cid:content-id
                    if (contentId) {{
                        const cidEsc = String(contentId).replace(/[.*+?^$()|[\\]\\\\]/g, '\\$&');
                        output = output.replace(new RegExp(`src=\\"cid:${{cidEsc}}\\"`, 'g'), `src=\"${{presigned}}\"`);
                        output = output.replace(new RegExp(`src=\'cid:${{cidEsc}}\'`, 'g'), `src=\"${{presigned}}\"`);
                        if (output !== afterS3) {{
                            console.log('🧩 cid references replaced for', contentId);
                        }} else {{
                            console.log('🧩 No cid references found for', contentId);
                        }}
                    }}
                }});

                // Fallback: if no <img> tags remain in output but we have inline attachments,
                // append a simple inline images block so the viewer still shows them.
                try {{
                    const hasImg = /<img\b[^>]*>/i.test(output);
                    if (!hasImg) {{
                        console.warn('🧩 No <img> tags found in processed body. Appending inline images block from attachments.');
                        const imagesHtml = inlineAttachments
                            .map(att => {{
                                const u = urlMap.get(att);
                                if (!u) return '';
                                const alt = (att.filename || 'Inline Image').replace(/"/g, '');
                                return `<div style="margin: 6px 0;"><img src="${{u}}" alt="${{alt}}" style="max-width: 100%; height: auto;" /></div>`;
                            }})
                            .join('');
                        if (imagesHtml) {{
                            const block = `<div style="margin-top: 12px; padding: 10px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;">`
                                + `<div style="font-weight: 600; margin-bottom: 6px;">Inline Images</div>`
                                + imagesHtml
                                + `</div>`;
                            output = output + block;
                            console.log('🧩 Appended inline images block with', inlineAttachments.length, 'image(s).');
                        }} else {{
                            console.warn('🧩 No presigned URLs available to append inline images block.');
                        }}
                    }}
                }} catch (appendErr) {{
                    console.warn('🧩 Failed to append inline images block:', appendErr);
                }}

                return output;
            }} catch (err) {{
                console.warn('resolveInlineImages failed:', err);
                return html;
            }}
        }}
        
        async function downloadAttachment(s3Key, filename) {{
            try {{
                const url = new URL(`${{API_URL}}/attachment-url`);
                url.searchParams.set('s3_key', s3Key);
                if (filename) url.searchParams.set('filename', filename);
                const response = await fetch(url.toString());
                if (!response.ok) throw new Error(`Failed to get URL (${{response.status}})`);
                const data = await response.json();
                if (!data.url) throw new Error('No URL returned');

                // Trigger download in browser
                const a = document.createElement('a');
                a.href = data.url;
                a.download = filename || 'attachment';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }} catch (err) {{
                console.error('Download failed:', err);
                Toast.error(`Download failed: ${{err.message}}`);
            }}
        }}

        function closeCampaignDetailsModal() {{
            document.getElementById('campaignDetailsModal').style.display = 'none';
            currentCampaignId = null;
            
            // Clear attachments container
            const attachmentsContainer = document.getElementById('detailAttachments');
            if (attachmentsContainer) {{
                attachmentsContainer.innerHTML = '';
            }}
        }}
        
        function exportCampaignTargets() {{
            if (!currentCampaignId) {{
                Toast.error('No campaign selected');
                return;
            }}
            
            const campaign = allCampaigns.find(c => c.campaign_id === currentCampaignId);
            if (!campaign) {{
                Toast.error('Campaign not found');
                return;
            }}
            
            // Get all target emails
            const targetEmails = campaign.target_contacts || [];
            const toEmails = campaign.to || [];
            const ccEmails = campaign.cc || [];
            const bccEmails = campaign.bcc || [];
            
            // Create CSV content
            let csvContent = 'Type,Email\\n';
            
            targetEmails.forEach(email => {{
                csvContent += `Target,${{email}}\\n`;
            }});
            
            toEmails.forEach(email => {{
                csvContent += `To,${{email}}\\n`;
            }});
            
            ccEmails.forEach(email => {{
                csvContent += `CC,${{email}}\\n`;
            }});
            
            bccEmails.forEach(email => {{
                csvContent += `BCC,${{email}}\\n`;
            }});
            
            // Download CSV
            const blob = new Blob([csvContent], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `campaign_${{campaign.campaign_name.replace(/[^a-z0-9]/gi, '_')}}_targets.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            Toast.success('CSV exported successfully', 2000);
        }}
        
        function exportAllCampaigns() {{
            if (allCampaigns.length === 0) {{
                Toast.error('No campaigns to export');
                return;
            }}
            
            // Create CSV with campaign summary
            let csvContent = 'Campaign Name,Subject,Date,Recipients,Status,Launched By,To Count,CC Count,BCC Count\\n';
            
            allCampaigns.forEach(campaign => {{
                const date = new Date(campaign.created_at || campaign.sent_at).toLocaleString();
                const toCount = (campaign.to || []).length;
                const ccCount = (campaign.cc || []).length;
                const bccCount = (campaign.bcc || []).length;
                
                csvContent += `"${{campaign.campaign_name || ''}}","${{campaign.subject || ''}}","${{date}}",${{campaign.total_contacts || 0}},"${{campaign.status || ''}}","${{campaign.launched_by || ''}}",${{toCount}},${{ccCount}},${{bccCount}}\\n`;
            }});
            
            // Download CSV
            const blob = new Blob([csvContent], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `all_campaigns_${{new Date().toISOString().split('T')[0]}}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            Toast.success('All campaigns exported to CSV', 2000);
        }}
        
        // ============================================
        // INITIALIZATION
        // ============================================
        
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
            # Convert Decimal types recursively
            config = convert_decimals(response['Item'])
            
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
        
        # Convert Decimal types recursively
        contacts = convert_decimals(response.get('Items', []))
        
        # Build response with pagination info
        result = {
            'contacts': contacts,
            'count': len(contacts)
        }
        
        # Include lastEvaluatedKey if there are more items
        if 'LastEvaluatedKey' in response:
            # Convert Decimal types in lastEvaluatedKey recursively
            result['lastEvaluatedKey'] = convert_decimals(response['LastEvaluatedKey'])
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
    
    except Exception as e:
        print(f"Error in get_contacts: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def get_distinct_values(headers, event):
    """Get distinct values for a specific field from DynamoDB"""
    try:
        # Get field name from query parameters
        query_params = event.get('queryStringParameters') or {}
        field_name_requested = query_params.get('field')
        
        if not field_name_requested:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'field parameter is required'})}
        
        print(f"Getting distinct values for field: {field_name_requested}")
        
        # Map frontend field names to actual DynamoDB field names
        # Try multiple variations for case-insensitive matching
        field_variations = [
            field_name_requested,  # Try as-is first (state)
            field_name_requested.capitalize(),  # Try capitalized (State)
            field_name_requested.upper(),  # Try uppercase (STATE)
            field_name_requested.lower(),  # Try lowercase (state)
            field_name_requested.title(),  # Try title case (State)
            field_name_requested.replace('_', ''),  # Try without underscore (statename)
            field_name_requested.replace('_', '').capitalize(),  # Try without underscore capitalized (Statename)
        ]
        
        # Add common field name variations
        common_mappings = {
            'state': ['State', 'state', 'STATE', 'state_name', 'State_Name', 'stateName'],
            'region': ['Region', 'region', 'REGION', 'region_name', 'Region_Name', 'regionName'],
            'agency_name': ['Agency_Name', 'agency_name', 'AgencyName', 'agencyName', 'Agency', 'agency'],
            'entity_type': ['Entity_Type', 'entity_type', 'EntityType', 'entityType', 'Entity', 'entity'],
        }
        
        if field_name_requested in common_mappings:
            field_variations.extend(common_mappings[field_name_requested])
        
        # Remove duplicates while preserving order
        seen = set()
        field_variations = [x for x in field_variations if not (x in seen or seen.add(x))]
        
        # Scan the entire table to get all values for the field
        distinct_values = set()
        last_evaluated_key = None
        scan_count = 0
        field_name = None
        
        # Try each field variation until we find one that works
        for attempted_field in field_variations:
            try:
                # Try a single scan with this field name
                # Use ExpressionAttributeNames to handle reserved words like "state", "region", "name", etc.
                test_scan = contacts_table.scan(
                    ProjectionExpression='#field',
                    ExpressionAttributeNames={'#field': attempted_field},
                    Select='SPECIFIC_ATTRIBUTES',
                    Limit=1
                )
                # If we get here, the field exists!
                field_name = attempted_field
                print(f"✓ Found field in DynamoDB as: {field_name}")
                break
            except Exception as e:
                continue
        
        if not field_name:
            print(f"❌ Field '{field_name_requested}' not found in any variation")
            print(f"Tried variations: {', '.join(field_variations[:10])}")  # Show first 10
            
            # Get a sample item to show available fields
            sample_scan = contacts_table.scan(Limit=1)
            available_fields = []
            if sample_scan.get('Items'):
                available_fields = list(sample_scan['Items'][0].keys())
            
            print(f"Available fields in table: {', '.join(sorted(available_fields[:20]))}")
            
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({
                'field': field_name_requested,
                'values': [],
                'count': 0,
                'error': f'Field not found. Tried: {", ".join(field_variations[:5])}... Available fields: {", ".join(sorted(available_fields[:10]))}'
            })}
        
        # Now scan with the correct field name
        while True:
            scan_params = {
                'ProjectionExpression': '#field',
                'ExpressionAttributeNames': {'#field': field_name},
                'Select': 'SPECIFIC_ATTRIBUTES'
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            try:
                response = contacts_table.scan(**scan_params)
            except Exception as e:
                # Field might not exist in schema, return empty
                print(f"Error scanning for field {field_name}: {str(e)}")
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'values': [], 'count': 0})}
            
            # Extract values from items
            for item in response.get('Items', []):
                if field_name in item:
                    value = item[field_name]
                    # Convert Decimal to int/float if needed
                    if isinstance(value, Decimal):
                        value = int(value) if value % 1 == 0 else float(value)
                    # Only add non-empty values
                    if value is not None and str(value).strip() != '':
                        distinct_values.add(str(value))
            
            scan_count += 1
            print(f"Scan iteration {scan_count}: Found {len(response.get('Items', []))} items, {len(distinct_values)} distinct values so far")
            
            # Check if there are more items to scan
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        # Convert set to sorted list
        values_list = sorted(list(distinct_values))
        
        print(f"Found {len(values_list)} distinct values for {field_name}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'field': field_name,
                'values': values_list,
                'count': len(values_list)
            })
        }
    
    except Exception as e:
        print(f"Error in get_distinct_values: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def filter_contacts(body, headers):
    """Filter contacts from DynamoDB based on multiple field filters"""
    try:
        filters = body.get('filters', [])
        
        if not filters:
            # No filters provided, return all contacts
            return get_contacts(headers, None)
        
        print(f"Filtering contacts with {len(filters)} filter(s)")
        
        # Build filter expression
        filter_expressions = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        name_counter = 0
        value_counter = 0
        
        for filter_item in filters:
            field = filter_item.get('field')
            values = filter_item.get('values', [])
            
            if not field or not values:
                continue
            
            print(f"Filter: {field} IN {values}")
            
            # Create placeholder for field name (to handle reserved words)
            field_placeholder = f'#field{name_counter}'
            expression_attribute_names[field_placeholder] = field
            name_counter += 1
            
            # Create OR conditions for values in the same field
            value_conditions = []
            for value in values:
                value_placeholder = f':val{value_counter}'
                expression_attribute_values[value_placeholder] = value
                value_conditions.append(f'{field_placeholder} = {value_placeholder}')
                value_counter += 1
            
            # Join OR conditions for this field
            if value_conditions:
                filter_expressions.append(f'({" OR ".join(value_conditions)})')
        
        if not filter_expressions:
            # No valid filters, return all contacts
            return get_contacts(headers, None)
        
        # Join all filter expressions with AND
        filter_expression = ' AND '.join(filter_expressions)
        
        print(f"Filter Expression: {filter_expression}")
        print(f"Expression Attribute Names: {expression_attribute_names}")
        
        # Scan DynamoDB with filter
        filtered_contacts = []
        last_evaluated_key = None
        scan_count = 0
        
        while True:
            scan_params = {
                'FilterExpression': filter_expression,
                'ExpressionAttributeNames': expression_attribute_names,
                'ExpressionAttributeValues': expression_attribute_values
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = contacts_table.scan(**scan_params)
            
            # Convert Decimal types recursively and add to filtered list
            items = convert_decimals(response.get('Items', []))
            filtered_contacts.extend(items)
            
            scan_count += 1
            print(f"Scan iteration {scan_count}: Found {len(response.get('Items', []))} items, {len(filtered_contacts)} total so far")
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        print(f"Filter complete: {len(filtered_contacts)} contacts match filters")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'contacts': filtered_contacts,
                'count': len(filtered_contacts)
            })
        }
    
    except Exception as e:
        print(f"Error in filter_contacts: {str(e)}")
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
        
        # Convert all contacts first (handles Decimal types)
        all_contacts = convert_decimals(all_contacts)
        
        # Filter contacts by name
        matched_contacts = []
        for contact in all_contacts:
            first_name = (contact.get('first_name') or '').lower()
            last_name = (contact.get('last_name') or '').lower()
            full_name = f"{first_name} {last_name}".strip()
            
            if (search_term in first_name or 
                search_term in last_name or 
                search_term in full_name):
                matched_contacts.append(contact)
        
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
            'body': json.dumps({'error': str(e)}, default=_json_default)
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
        print("📎 Upload attachment request received")
        print(f"Request body keys: {list(body.keys())}")
        
        filename = body.get('filename')
        content_type = body.get('content_type', 'application/octet-stream')
        s3_key = body.get('s3_key')
        data = body.get('data')  # Base64 encoded file data
        
        print(f"📄 Filename: {filename}")
        print(f"📋 ContentType: {content_type}")
        print(f"🗂️  S3Key: {s3_key}")
        print(f"📊 Data length: {len(data) if data else 0} characters (base64)")
        
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
        print("Decoding base64 data...")
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
                'filename': filename,
                's3_key': s3_key,
                'bucket': ATTACHMENTS_BUCKET,
                'size': len(file_data),
                'type': content_type
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
        import uuid
        contacts_table.put_item(
            Item={
                'contact_id': str(uuid.uuid4()),  # Generate unique contact_id
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
        contact_id = body.get('contact_id')
        email = body.get('email')
        
        if not contact_id:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'contact_id is required'})}
        
        # Define all possible contact fields
        contact_fields = [
            'email', 'first_name', 'last_name', 'title', 'entity_type', 'state', 
            'agency_name', 'sector', 'subsection', 'phone', 'ms_isac_member',
            'soc_call', 'fusion_center', 'k12', 'water_wastewater', 
            'weekly_rollup', 'alternate_email', 'region', 'group'
        ]
        
        update_expr = "SET "
        expr_values = {}
        expr_names = {}
        update_parts = []
        
        for field in contact_fields:
            if field in body and field != 'contact_id':
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
            Key={'contact_id': contact_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values
        )
        
        print(f"Updated contact {contact_id} (email: {email}) with fields: {list(body.keys())}")
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        print(f"Error updating contact: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def delete_contact(event, headers):
    """Delete contact"""
    try:
        # Get contact_id from query parameters
        query_params = event.get('queryStringParameters') or {}
        contact_id = query_params.get('contact_id')
        
        print(f"Delete request - contact_id: {contact_id}")
        
        if not contact_id:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'contact_id is required'})}
        
        contacts_table.delete_item(Key={'contact_id': contact_id})
        print(f"Successfully deleted contact: {contact_id}")
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'success': True})}
    except Exception as e:
        print(f"Error deleting contact: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def send_campaign(body, headers, event=None):
    """Send email campaign by saving to DynamoDB and queuing contacts to SQS"""
    try:
        # Log font usage analysis for the campaign
        email_body = body.get('body', '')
        print(f"🎨 FONT ANALYSIS: Analyzing email body for font usage...")
        
        # Extract font classes from the email HTML
        import re
        font_classes = re.findall(r'class="[^"]*ql-font-([^"\s]+)', email_body)
        if font_classes:
            unique_fonts = list(set(font_classes))
            print(f"🎨 FONTS USED IN CAMPAIGN: {len(unique_fonts)} different fonts detected")
            for i, font in enumerate(unique_fonts, 1):
                font_count = font_classes.count(font)
                print(f"   {i}. Font '{font}': used {font_count} time(s)")
            
            # Log to campaign metadata
            font_usage_summary = {font: font_classes.count(font) for font in unique_fonts}
            print(f"🎨 FONT USAGE SUMMARY: {font_usage_summary}")
        else:
            print(f"🎨 FONTS USED IN CAMPAIGN: No custom fonts detected (using default font)")
        
        # Check for inline font styles as backup
        inline_fonts = re.findall(r'font-family:\s*([^;"\'>]+)', email_body, re.IGNORECASE)
        if inline_fonts:
            unique_inline_fonts = list(set([font.strip().strip('"\'') for font in inline_fonts]))
            print(f"🎨 INLINE FONTS DETECTED: {unique_inline_fonts}")
        
        print(f"📧 Campaign body length: {len(email_body)} characters")
        # Get email configuration
        config_response = email_config_table.get_item(Key={'config_id': 'default'})
        if 'Item' not in config_response:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Email configuration not found'})}
        
        config = config_response['Item']
        
        # Get target contacts from frontend filter
        target_contact_emails = body.get('target_contacts', [])
        filter_description = body.get('filter_description', 'All Contacts')
        
        print(f"Received campaign request with {len(target_contact_emails)} email addresses")
        print(f"Sample emails: {target_contact_emails[:5]}")
        
        if not target_contact_emails:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No target email addresses specified. Please select recipients in the Campaign tab.'})}
        
        # Get CC and BCC lists FIRST to exclude them from regular contacts
        cc_list = body.get('cc', []) or []
        bcc_list = body.get('bcc', []) or []
        to_list = body.get('to', []) or []
        
        # Create normalized sets for exclusion (case-insensitive)
        cc_set = set([email.lower().strip() for email in cc_list if email and '@' in email])
        bcc_set = set([email.lower().strip() for email in bcc_list if email and '@' in email])
        to_set = set([email.lower().strip() for email in to_list if email and '@' in email])
        cc_bcc_to_combined = cc_set | bcc_set | to_set
        
        print(f"🔍 CC DUPLICATION FIX - EXCLUSION SETUP:")
        print(f"   CC list: {cc_list}")
        print(f"   BCC list: {bcc_list}")
        print(f"   To list: {to_list}")
        print(f"   Combined exclusion set: {cc_bcc_to_combined}")
        
        # Create contact objects directly from email addresses (independent of Contacts table)
        # IMPORTANT: Exclude anyone on CC/BCC/To lists - they'll be queued separately
        contacts = []
        excluded_count = 0
        
        for email in target_contact_emails:
            if email and '@' in email:  # Basic email validation
                normalized_email = email.lower().strip()
                
                # CRITICAL: Exclude if this email is on CC/BCC/To list
                if normalized_email in cc_bcc_to_combined:
                    print(f"   ✅ EXCLUDING {email} from regular contacts (found in CC/BCC/To list)")
                    excluded_count += 1
                else:
                    print(f"   ➕ ADDING {email} as regular contact")
                    contacts.append({
                        'email': email,
                        'first_name': '',
                        'last_name': '',
                        'company': ''
                    })
            else:
                print(f"Invalid email format, skipping: {email}")
        
        print(f"📊 CC DUPLICATION FIX - SUMMARY:")
        print(f"   Total target emails: {len(target_contact_emails)}")
        print(f"   Regular contacts created: {len(contacts)}")
        print(f"   Excluded (CC/BCC/To): {excluded_count}")
        
        # Check if we have any recipients at all (regular contacts + CC + BCC + To)
        total_recipients = len(contacts) + len(cc_list) + len(bcc_list) + len(to_list)
        
        print(f"Campaign targeting {len(contacts)} regular contacts + {len(cc_list)} CC + {len(bcc_list)} BCC + {len(to_list)} To = {total_recipients} total recipients ({filter_description})")
        
        if not contacts and not cc_list and not bcc_list and not to_list:
            error_msg = f'No recipients specified. Please add target contacts, or specify To/CC/BCC recipients.'
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': error_msg})}
        
        if not contacts and (cc_list or bcc_list or to_list):
            print(f"✅ CC/BCC/To-only campaign: {len(cc_list)} CC + {len(bcc_list)} BCC + {len(to_list)} To recipients")
        
        campaign_id = f"campaign_{int(datetime.now().timestamp())}"
        
        # Get attachments
        attachments = body.get('attachments', [])
        
        # Get email body for inspection
        email_body = body.get('body', '')
        
        # DEBUG: Show what was received from frontend
        print(f"📧 Campaign body length: {len(email_body)} characters")
        print(f"📧 Body sample (first 500 chars): {email_body[:500]}...")
        
        # Check for img tags in the received body
        import re
        img_tags = re.findall(r'<img[^>]+>', email_body, re.IGNORECASE)
        if img_tags:
            print(f"🖼️ Found {len(img_tags)} <img> tag(s) in campaign body:")
            for i, tag in enumerate(img_tags):
                print(f"   {i+1}. {tag[:200]}...")
        else:
            print(f"⚠️ No <img> tags found in campaign body!")
        
        # Show attachment details
        if attachments:
            print(f"📎 {len(attachments)} attachment(s) received:")
            for i, att in enumerate(attachments):
                print(f"   {i+1}. {att.get('filename')} - s3_key: {att.get('s3_key')}, inline: {att.get('inline')}, size: {att.get('size', 0)}")
        else:
            print(f"📎 No attachments received")
        
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
        # Persist explicit To list if provided
        if body.get('to'):
            campaign_item['to'] = body.get('to')
        # Persist CC and BCC lists if provided by the client so workers can honor them
        if body.get('cc'):
            campaign_item['cc'] = body.get('cc')
        if body.get('bcc'):
            campaign_item['bcc'] = body.get('bcc')
        
        # Add font usage analysis to campaign record
        if body.get('font_usage'):
            campaign_item['font_usage'] = body.get('font_usage')
            font_list = list(body.get('font_usage').keys())
            print(f"🎨 CAMPAIGN FONTS STORED: {font_list}")
        
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
        
        # Enqueue one message per CC and BCC recipient (single-send), avoid duplicates with target contacts
        # Normalize to lowercase for case-insensitive comparison
        all_target_emails = set([c.get('email').lower().strip() for c in contacts if c.get('email')])

        # Helper to enqueue additional recipients
        def enqueue_special(recipient_email, role):
            nonlocal queued_count, failed_to_queue
            if not recipient_email or '@' not in recipient_email:
                print(f"Skipping invalid {role} email: {recipient_email}")
                return
            # Case-insensitive comparison to avoid duplicates
            if recipient_email.lower().strip() in all_target_emails:
                print(f"Skipping {role} {recipient_email} because it is already in target contacts")
                return

            try:
                special_message = {
                    'campaign_id': campaign_id,
                    'contact_email': recipient_email,
                    'role': role
                }

                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(special_message),
                    MessageAttributes={
                        'campaign_id': {
                            'StringValue': campaign_id,
                            'DataType': 'String'
                        },
                        'contact_email': {
                            'StringValue': recipient_email,
                            'DataType': 'String'
                        },
                        'role': {
                            'StringValue': role,
                            'DataType': 'String'
                        }
                    }
                )
                queued_count += 1
                print(f"Queued {role.upper()} email for {recipient_email}")
            except Exception as e:
                print(f"Failed to queue {role} email for {recipient_email}: {str(e)}")
                failed_to_queue += 1

        # CC and BCC addresses are stored in campaign data and will be included in every email
        # No need to queue them individually - they'll be retrieved from campaign by email_worker
        # for cc in cc_list:
        #     enqueue_special(cc, 'cc')
        # for bcc in bcc_list:
        #     enqueue_special(bcc, 'bcc')
        
        # Enqueue explicit To addresses (single-send each) - skip addresses already in target contacts
        for to_addr in to_list:
            enqueue_special(to_addr, 'to')
        
        # If no messages were queued but we have CC/BCC recipients, queue one dummy message
        # so the email worker will process the campaign and send to CC/BCC
        if queued_count == 0 and (cc_list or bcc_list):
            print(f"⚠️ CC/BCC-only campaign with no regular contacts - queuing one message for CC/BCC delivery")
            try:
                # Queue a message with the first CC or BCC as the "To" recipient
                # They'll receive the email as both To and CC/BCC
                dummy_recipient = cc_list[0] if cc_list else bcc_list[0]
                message_body = {
                    'campaign_id': campaign_id,
                    'contact_email': dummy_recipient
                }
                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message_body),
                    MessageAttributes={
                        'campaign_id': {
                            'StringValue': campaign_id,
                            'DataType': 'String'
                        },
                        'contact_email': {
                            'StringValue': dummy_recipient,
                            'DataType': 'String'
                        }
                    }
                )
                queued_count += 1
                print(f"✅ Queued CC/BCC delivery message to {dummy_recipient}")
            except Exception as e:
                print(f"❌ Failed to queue CC/BCC delivery message: {str(e)}")
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

def send_ses_email(config, contact, subject, body):
    """Send email via AWS SES"""
    try:
        
        ses_client = boto3.client(
            'ses',
            region_name=config.get('aws_region', 'us-gov-west-1')
        )
        
        personalized_subject = personalize_content(subject, contact)
        personalized_body = personalize_content(body, contact)
        
        # Build destination with proper CC/BCC handling
        destination = {}
        
        # Check if this contact has a specific role (cc, bcc, or regular to)
        contact_role = contact.get('role', 'to')
        
        if contact_role == 'cc':
            # For CC recipients: they get the email with their address in CC field
            # We need to include at least one To address for SES to work
            destination = {
                'ToAddresses': [config.get('from_email', contact['email'])],  # Use from_email as To
                'CcAddresses': [contact['email']]
            }
        elif contact_role == 'bcc':
            # For BCC recipients: they get the email with their address in BCC field
            # We need to include at least one To address for SES to work
            destination = {
                'ToAddresses': [config.get('from_email', contact['email'])],  # Use from_email as To
                'BccAddresses': [contact['email']]
            }
        else:
            # For regular To recipients: they get the email normally
            destination = {'ToAddresses': [contact['email']]}
        
        ses_client.send_email(
            Source=config['from_email'],
            Destination=destination,
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


def get_attachment_url(event, headers):
    """Generate a short-lived presigned URL to download an attachment from S3"""
    try:
        print("🔗 Generating presigned URL for attachment download")
        # Support both HTTP API (queryStringParameters) and REST API (multiValueQueryStringParameters)
        qs = event.get('queryStringParameters') or {}
        s3_key = (qs.get('s3_key') or '').strip()
        filename = (qs.get('filename') or '').strip()
        disposition = (qs.get('disposition') or qs.get('inline') or '').strip().lower()
        print(f"   → Query params: s3_key='{s3_key}', filename='{filename}', disposition='{disposition}'")

        if not s3_key:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing required query parameter: s3_key'})
            }

        # Basic safety: prevent directory traversal (S3 keys are flat but be cautious)
        if '..' in s3_key:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid s3_key'})
            }

        # Default filename from key if not provided
        if not filename:
            filename = s3_key.split('/')[-1] or 'attachment'

        # Determine desired Content-Disposition
        inline_requested = disposition in ('1', 'true', 'yes', 'inline')
        response_content_disposition = (
            f'inline; filename="{filename}"' if inline_requested else f'attachment; filename="{filename}"'
        )
        print(f"   → Content-Disposition selected: '{response_content_disposition}'")

        # Generate presigned URL for GET
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': ATTACHMENTS_BUCKET,
                'Key': s3_key,
                'ResponseContentDisposition': response_content_disposition
            },
            ExpiresIn=3600  # 1 hour
        )
        print(f"   ✅ Presigned URL generated (truncated): {str(url)[:120]}...")

        return {
            'statusCode': 200,
            'headers': {**headers, 'Content-Type': 'application/json'},
            'body': json.dumps({'url': url})
        }
    except Exception as e:
        print(f"ERROR generating presigned URL: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to generate download URL'})
        }


def get_campaign_status(campaign_id, headers):
    """Get campaign status"""
    try:
        # Log view event for CloudWatch when this endpoint is hit (used by UI View button)
        print(f"👁️ CAMPAIGN VIEWED: campaign_id={campaign_id}")
        response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
        if 'Item' not in response:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Campaign not found'})}
        
        # Convert Decimal types recursively
        campaign = convert_decimals(response['Item'])
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(campaign, default=_json_default)}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}


def get_campaigns(headers, event=None):
    """Get campaigns page from DynamoDB with server-side pagination (limit=50) and optional search (q)."""
    try:
        qs = (event or {}).get('queryStringParameters') or {}
        limit = 50
        next_token = qs.get('next') if qs else None
        search_query = (qs.get('q') or qs.get('query') or '').strip()
        print(f"Fetching campaigns page (limit={limit}) next_token={next_token} q='{search_query}'")

        scan_kwargs = {
            'Limit': limit if not search_query else 100,  # when searching, fetch larger pages to find matches
        }
        if next_token:
            try:
                scan_kwargs['ExclusiveStartKey'] = json.loads(next_token)
            except Exception as tok_err:
                print(f"Invalid next token provided: {tok_err}")

        # If no search, return single page from DynamoDB
        if not search_query:
            response = campaigns_table.scan(**scan_kwargs)
            items = response.get('Items', [])
            items = convert_decimals(items)
            last_evaluated_key = response.get('LastEvaluatedKey')
            next_token_out = json.dumps(last_evaluated_key) if last_evaluated_key else None
            print(f"Page retrieved: {len(items)} items, has_more={bool(last_evaluated_key)}")
        else:
            # Case-insensitive search across campaign_name and subject
            ql = search_query.lower()
            results = []
            last_evaluated_key = None
            scanned_pages = 0
            while True:
                scanned_pages += 1
                response = campaigns_table.scan(**scan_kwargs)
                page_items = convert_decimals(response.get('Items', []))
                # Exclude previews and filter by substring
                for it in page_items:
                    if it.get('status') == 'preview' or it.get('type') == 'preview':
                        continue
                    name = str(it.get('campaign_name') or '').lower()
                    subj = str(it.get('subject') or '').lower()
                    if ql in name or ql in subj:
                        results.append(it)
                        if len(results) >= limit:
                            break
                last_evaluated_key = response.get('LastEvaluatedKey')
                if len(results) >= limit or not last_evaluated_key:
                    break
                # Keep scanning with new start key
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
            items = results
            next_token_out = json.dumps(last_evaluated_key) if last_evaluated_key else None
            print(f"Search '{search_query}' matched {len(items)} item(s) on this page; has_more={bool(last_evaluated_key)}; scanned_pages={scanned_pages}")

        response_headers = {
            **headers,
            'Content-Type': 'application/json'
        }

        return {
            'statusCode': 200,
            'headers': response_headers,
            'body': json.dumps({
                'success': True,
                'campaigns': items,
                'count': len(items),
                'next': next_token_out
            }, default=_json_default)
        }

    except Exception as e:
        print(f"Error fetching campaigns: {str(e)}")
        import traceback
        traceback.print_exc()

        error_headers = {
            **headers,
            'Content-Type': 'application/json'
        }

        return {
            'statusCode': 500,
            'headers': error_headers,
            'body': json.dumps({'error': str(e)}, default=_json_default)
        }


def mark_campaign_viewed(body, headers):
    """Record a campaign view event for CloudWatch visibility."""
    try:
        campaign_id = (body or {}).get('campaign_id')
        timestamp = (body or {}).get('timestamp')
        print(f"👁️ CAMPAIGN VIEWED: campaign_id={campaign_id}, ts={timestamp}")
        # Optionally increment a view counter in DynamoDB in the future
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'ok': True})
        }
    except Exception as e:
        print(f"ERROR logging campaign view: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to log campaign view'})
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
        
        print("Successfully retrieved AWS credentials from Secrets Manager")
        return credentials
        
    except Exception as e:
        print(f"Error retrieving credentials from Secrets Manager: {str(e)}")
        raise


