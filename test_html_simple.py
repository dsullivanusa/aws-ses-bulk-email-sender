#!/usr/bin/env python3
"""
Simple HTML Test
This script creates a simple test HTML file to verify the API_URL works
"""

def create_test_html():
    """Create a simple test HTML file"""
    print("Creating test HTML file...")
    
    api_url = "https://jcdcmail.cisa.dhs.gov"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>API_URL Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .test-result {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .info {{ background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
    </style>
</head>
<body>
    <h1>API_URL Test</h1>
    
    <div class="info">
        <h3>Test Results:</h3>
        <div id="test-results"></div>
    </div>
    
    <div class="info">
        <h3>API_URL Value:</h3>
        <div id="api-url-value"></div>
    </div>
    
    <div class="info">
        <h3>Test API Call:</h3>
        <button onclick="testApiCall()">Test API Call</button>
        <div id="api-test-result"></div>
    </div>
    
    <script>
        const API_URL = '{api_url}';
        
        function runTests() {{
            const results = document.getElementById('test-results');
            const apiUrlDiv = document.getElementById('api-url-value');
            let html = '';
            
            // Display API_URL value
            apiUrlDiv.innerHTML = '<strong>API_URL = "' + API_URL + '"</strong>';
            
            // Test 1: Check if API_URL is defined
            if (typeof API_URL !== 'undefined' && API_URL !== '') {{
                html += '<div class="test-result success">API_URL is defined: ' + API_URL + '</div>';
            }} else {{
                html += '<div class="test-result error">API_URL is not defined</div>';
            }}
            
            // Test 2: Check if API_URL is a valid URL
            try {{
                new URL(API_URL);
                html += '<div class="test-result success">API_URL is a valid URL</div>';
            }} catch (e) {{
                html += '<div class="test-result error">API_URL is not a valid URL: ' + e.message + '</div>';
            }}
            
            // Test 3: Check if API_URL contains the expected domain
            if (API_URL.includes('jcdcmail.cisa.dhs.gov')) {{
                html += '<div class="test-result success">API_URL contains expected domain</div>';
            }} else {{
                html += '<div class="test-result error">API_URL does not contain expected domain</div>';
            }}
            
            // Test 4: Check if API_URL starts with https
            if (API_URL.startsWith('https://')) {{
                html += '<div class="test-result success">API_URL uses HTTPS</div>';
            }} else {{
                html += '<div class="test-result error">API_URL does not use HTTPS</div>';
            }}
            
            results.innerHTML = html;
        }}
        
        function testApiCall() {{
            const resultDiv = document.getElementById('api-test-result');
            resultDiv.innerHTML = '<div class="test-result info">Testing API call to: ' + API_URL + '</div>';
            
            // Test a simple fetch request
            fetch(API_URL)
                .then(response => {{
                    if (response.ok) {{
                        resultDiv.innerHTML = '<div class="test-result success">API call successful! Status: ' + response.status + '</div>';
                    }} else {{
                        resultDiv.innerHTML = '<div class="test-result error">API call failed. Status: ' + response.status + '</div>';
                    }}
                }})
                .catch(error => {{
                    resultDiv.innerHTML = '<div class="test-result error">API call failed: ' + error.message + '</div>';
                }});
        }}
        
        // Run tests when page loads
        window.onload = runTests;
    </script>
</body>
</html>"""
    
    with open('api_url_test.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("Test HTML file created: api_url_test.html")
    print("Open this file in your browser to test the API_URL")
    return True

if __name__ == '__main__':
    create_test_html()
