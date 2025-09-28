import json
import base64

def lambda_handler(event, context):
    """Serve the VPC SMTP web UI HTML file"""
    
    # Get the API Gateway URL from the request context
    api_id = event.get('requestContext', {}).get('apiId', 'UNKNOWN')
    api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMTP Bulk Email Sender</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #6f42c1; color: white; padding: 20px; text-align: center; margin-bottom: 30px; }}
        .vpc-info {{ background: #e7f1ff; padding: 15px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #6f42c1; }}
        .tabs {{ display: flex; background: white; border-radius: 8px; overflow: hidden; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .tab {{ flex: 1; padding: 15px; text-align: center; cursor: pointer; border: none; background: #f8f9fa; }}
        .tab.active {{ background: #6f42c1; color: white; }}
        .tab-content {{ display: none; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .tab-content.active {{ display: block; }}
        .form-group {{ margin-bottom: 20px; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .form-group input, .form-group textarea, .form-group select {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
        .form-group textarea {{ height: 200px; resize: vertical; }}
        .btn {{ padding: 12px 24px; background: #6f42c1; color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 10px; }}
        .btn:hover {{ background: #5a32a3; }}
        .btn-success {{ background: #28a745; }}
        .btn-danger {{ background: #dc3545; }}
        .contacts-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .contacts-table th, .contacts-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        .contacts-table th {{ background: #f8f9fa; }}
        .progress-container {{ margin: 20px 0; }}
        .progress-bar {{ width: 100%; height: 25px; background: #f0f0f0; border-radius: 12px; overflow: hidden; position: relative; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #6f42c1, #8e5ec7); width: 0%; transition: width 0.3s; }}
        .progress-text {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: bold; color: #333; }}
        .alert {{ padding: 15px; margin: 10px 0; border-radius: 4px; }}
        .alert-success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .alert-error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 SMTP Bulk Email Sender</h1>
            <p>Secure Email Campaigns</p>
        </div>

        <div class="vpc-info">
            <strong>🛡️ VPC Security:</strong> Connected to private API Gateway: {api_url}
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('contacts')">Contacts</button>
            <button class="tab" onclick="showTab('smtp-config')">SMTP Config</button>
            <button class="tab" onclick="showTab('template')">Email Template</button>
            <button class="tab" onclick="showTab('campaign')">Send Campaign</button>
        </div>

        <div id="contacts" class="tab-content active">
            <h2>Contact Management</h2>
            <button class="btn" onclick="loadContacts()">Load Contacts</button>
            <button class="btn btn-success" onclick="showAddContactForm()">Add Contact</button>
            <input type="file" id="csvFile" accept=".csv" style="display: none;" onchange="importCSV()">
            <button class="btn" onclick="document.getElementById('csvFile').click()">Import CSV</button>
            
            <div id="addContactForm" class="hidden" style="margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 4px;">
                <h3>Add New Contact</h3>
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" id="newEmail" required>
                </div>
                <div class="form-group">
                    <label>First Name:</label>
                    <input type="text" id="newFirstName">
                </div>
                <div class="form-group">
                    <label>Last Name:</label>
                    <input type="text" id="newLastName">
                </div>
                <div class="form-group">
                    <label>Company:</label>
                    <input type="text" id="newCompany">
                </div>
                <button class="btn" onclick="addContact()">Add Contact</button>
                <button class="btn btn-danger" onclick="hideAddContactForm()">Cancel</button>
            </div>
            
            <table class="contacts-table">
                <thead>
                    <tr><th>Email</th><th>First Name</th><th>Last Name</th><th>Company</th><th>Actions</th></tr>
                </thead>
                <tbody id="contactsTableBody"></tbody>
            </table>
        </div>

        <div id="smtp-config" class="tab-content">
            <h2>SMTP Configuration</h2>
            <div class="form-group">
                <label>SMTP Relay IP Address:</label>
                <input type="text" id="smtpServer" value="192.168.1.100" placeholder="192.168.1.100">
            </div>
            <div class="form-group">
                <label>SMTP Port:</label>
                <input type="number" id="smtpPort" value="25" placeholder="25">
            </div>
            <div class="form-group">
                <label>From Email:</label>
                <input type="email" id="fromEmail" placeholder="sender@domain.com">
            </div>
            <button class="btn" onclick="saveSMTPConfig()">Save Configuration</button>
        </div>

        <div id="template" class="tab-content">
            <h2>Email Template</h2>
            <div class="form-group">
                <label>Subject:</label>
                <input type="text" id="emailSubject">
            </div>
            <div class="form-group">
                <label>Body:</label>
                <textarea id="emailBody"></textarea>
            </div>
            <button class="btn" onclick="loadSampleTemplate()">Load Sample</button>
        </div>

        <div id="campaign" class="tab-content">
            <h2>Send Campaign</h2>
            <div class="form-group">
                <label>Campaign Name:</label>
                <input type="text" id="campaignName">
            </div>
            <button class="btn btn-success" onclick="sendCampaign()">Send Campaign</button>
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                    <div class="progress-text" id="progressText">Ready</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE_URL = '{api_url}';
        
        function showTab(tabName) {{
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }}

        async function apiCall(endpoint, method = 'GET', data = null) {{
            const options = {{ method, headers: {{ 'Content-Type': 'application/json' }} }};
            if (data) options.body = JSON.stringify(data);
            
            try {{
                const response = await fetch(`${{API_BASE_URL}}${{endpoint}}`, options);
                return await response.json();
            }} catch (error) {{
                showAlert('API Error: ' + error.message, 'error');
                return null;
            }}
        }}

        async function loadContacts() {{
            const result = await apiCall('/contacts');
            if (result && result.contacts) {{
                displayContacts(result.contacts);
            }}
        }}

        function displayContacts(contacts) {{
            const tbody = document.getElementById('contactsTableBody');
            tbody.innerHTML = '';
            contacts.forEach(contact => {{
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${{contact.email}}</td>
                    <td>${{contact.first_name || ''}}</td>
                    <td>${{contact.last_name || ''}}</td>
                    <td>${{contact.company || ''}}</td>
                    <td>
                        <button class="btn" style="padding: 5px 10px; margin: 2px;" onclick="editContact('${{contact.email}}')">Edit</button>
                        <button class="btn btn-danger" style="padding: 5px 10px; margin: 2px;" onclick="deleteContact('${{contact.email}}')">Delete</button>
                    </td>
                `;
            }});
        }}

        function saveSMTPConfig() {{
            const config = {{
                smtp_server: document.getElementById('smtpServer').value,
                smtp_port: document.getElementById('smtpPort').value,
                from_email: document.getElementById('fromEmail').value
            }};
            localStorage.setItem('smtpConfig', JSON.stringify(config));
            showAlert('Configuration saved', 'success');
        }}

        function loadSampleTemplate() {{
            document.getElementById('emailSubject').value = 'Welcome {{{{first_name}}}}!';
            document.getElementById('emailBody').value = 'Hello {{{{first_name}}}}, welcome to our service!';
        }}

        function showAddContactForm() {{
            document.getElementById('addContactForm').classList.remove('hidden');
        }}

        function hideAddContactForm() {{
            document.getElementById('addContactForm').classList.add('hidden');
            document.getElementById('newEmail').readOnly = false;
            clearAddContactForm();
        }}

        function clearAddContactForm() {{
            document.getElementById('newEmail').value = '';
            document.getElementById('newFirstName').value = '';
            document.getElementById('newLastName').value = '';
            document.getElementById('newCompany').value = '';
        }}

        async function addContact() {{
            const contact = {{
                email: document.getElementById('newEmail').value,
                first_name: document.getElementById('newFirstName').value,
                last_name: document.getElementById('newLastName').value,
                company: document.getElementById('newCompany').value
            }};
            
            if (!contact.email) {{
                showAlert('Email is required', 'error');
                return;
            }}
            
            const result = await apiCall('/contacts', 'POST', {{ contact }});
            if (result) {{
                showAlert('Contact added successfully', 'success');
                hideAddContactForm();
                loadContacts();
            }}
        }}

        async function editContact(email) {{
            const result = await apiCall(`/contacts?email=${{encodeURIComponent(email)}}`);
            if (result && result.contact) {{
                const contact = result.contact;
                document.getElementById('newEmail').value = contact.email;
                document.getElementById('newFirstName').value = contact.first_name || '';
                document.getElementById('newLastName').value = contact.last_name || '';
                document.getElementById('newCompany').value = contact.company || '';
                document.getElementById('newEmail').readOnly = true;
                showAddContactForm();
            }}
        }}

        async function deleteContact(email) {{
            if (confirm(`Are you sure you want to delete contact: ${{email}}?`)) {{
                const result = await apiCall(`/contacts?email=${{encodeURIComponent(email)}}`, 'DELETE');
                if (result) {{
                    showAlert('Contact deleted successfully', 'success');
                    loadContacts();
                }}
            }}
        }}

        async function importCSV() {{
            const file = document.getElementById('csvFile').files[0];
            if (!file) return;
            
            const text = await file.text();
            const lines = text.split('\\n');
            const headers = lines[0].split(',').map(h => h.trim());
            
            for (let i = 1; i < lines.length; i++) {{
                if (lines[i].trim()) {{
                    const values = lines[i].split(',').map(v => v.trim());
                    const contact = {{}};
                    
                    headers.forEach((header, index) => {{
                        contact[header] = values[index] || '';
                    }});
                    
                    await apiCall('/contacts', 'POST', {{ contact }});
                }}
            }}
            
            showAlert('CSV imported successfully', 'success');
            loadContacts();
        }}

        async function sendCampaign() {{
            const config = JSON.parse(localStorage.getItem('smtpConfig') || '{{}}');
            const payload = {{
                subject: document.getElementById('emailSubject').value,
                body: document.getElementById('emailBody').value,
                campaign_name: document.getElementById('campaignName').value,
                ...config
            }};
            
            const result = await apiCall('/smtp-campaign', 'POST', payload);
            if (result) {{
                showAlert('Campaign sent successfully!', 'success');
                document.getElementById('progressFill').style.width = '100%';
                document.getElementById('progressText').textContent = 'Complete';
            }}
        }}

        function showAlert(message, type) {{
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${{type}}`;
            alertDiv.textContent = message;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.tabs'));
            setTimeout(() => alertDiv.remove(), 3000);
        }}

        window.onload = () => {{
            loadContacts();
            showAlert('Connected to VPC SMTP API', 'success');
        }};
    </script>
</body>
</html>"""

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache'
        },
        'body': html_content
    }