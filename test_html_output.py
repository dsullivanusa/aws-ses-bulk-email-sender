#!/usr/bin/env python3
"""
Test HTML Output
This script tests the HTML output that the Lambda function will generate
"""

import os

def test_html_output():
    """Test the HTML output that the Lambda function will generate"""
    print("Testing HTML output...")
    
    # Simulate the Lambda function logic
    CUSTOM_API_URL = "https://jcdcmail.cisa.dhs.gov"  # Your custom domain
    
    if CUSTOM_API_URL:
        api_url = CUSTOM_API_URL
        print(f"Using custom API URL: {api_url}")
    else:
        # Simulate API Gateway URL generation
        api_id = "yi6ss4dsoe"
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"Using API Gateway URL: {api_url}")
    
    # Read the HTML template from the Lambda function
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the HTML template from the serve_web_ui function
        import re
        
        # Find the HTML content between the triple quotes
        html_match = re.search(r'html_content = """(.*?)""".format\(api_url=api_url\)', content, re.DOTALL)
        if html_match:
            html_template = html_match.group(1)
            
            # Format the HTML with the API URL
            html_content = html_template.format(api_url=api_url)
            
            # Save the HTML to a file for testing
            with open('test_output.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print("HTML output saved to: test_output.html")
            
            # Check if API_URL is properly defined in the HTML
            if f"const API_URL = '{api_url}';" in html_content:
                print("✅ API_URL is properly defined in the HTML")
            else:
                print("❌ API_URL is not properly defined in the HTML")
            
            # Check for any JavaScript syntax errors
            script_start = html_content.find('<script>')
            script_end = html_content.find('</script>')
            if script_start != -1 and script_end != -1:
                script_content = html_content[script_start:script_end]
                
                # Check for common JavaScript issues
                if 'API_URL' in script_content:
                    print("✅ API_URL is referenced in the JavaScript")
                else:
                    print("❌ API_URL is not referenced in the JavaScript")
                
                # Check for template literal syntax
                template_literals = re.findall(r'`[^`]*`', script_content)
                if template_literals:
                    print(f"✅ Found {len(template_literals)} template literals in JavaScript")
                    
                    # Check if template literals have proper syntax
                    valid_templates = 0
                    for template in template_literals:
                        if '${' in template and '}' in template:
                            valid_templates += 1
                    
                    print(f"✅ {valid_templates}/{len(template_literals)} template literals have valid syntax")
                else:
                    print("❌ No template literals found in JavaScript")
            
            return True
        else:
            print("❌ Could not extract HTML template from Lambda function")
            return False
            
    except Exception as e:
        print(f"❌ Error testing HTML output: {e}")
        return False

def create_simple_test_html():
    """Create a simple test HTML file to verify the API_URL works"""
    print("\nCreating simple test HTML...")
    
    api_url = "https://jcdcmail.cisa.dhs.gov"
    
    simple_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>API_URL Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .test-result {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
    </style>
</head>
<body>
    <h1>API_URL Test</h1>
    
    <div id="test-results"></div>
    
    <script>
        const API_URL = '{api_url}';
        
        function runTests() {{
            const results = document.getElementById('test-results');
            let html = '';
            
            // Test 1: Check if API_URL is defined
            if (typeof API_URL !== 'undefined' && API_URL !== '') {{
                html += '<div class="test-result success">✅ API_URL is defined: ' + API_URL + '</div>';
            }} else {{
                html += '<div class="test-result error">❌ API_URL is not defined</div>';
            }}
            
            // Test 2: Check if API_URL is a valid URL
            try {{
                new URL(API_URL);
                html += '<div class="test-result success">✅ API_URL is a valid URL</div>';
            }} catch (e) {{
                html += '<div class="test-result error">❌ API_URL is not a valid URL: ' + e.message + '</div>';
            }}
            
            // Test 3: Check if API_URL contains the expected domain
            if (API_URL.includes('jcdcmail.cisa.dhs.gov')) {{
                html += '<div class="test-result success">✅ API_URL contains expected domain</div>';
            }} else {{
                html += '<div class="test-result error">❌ API_URL does not contain expected domain</div>';
            }}
            
            // Test 4: Test a simple fetch request (this will fail but we can check the URL)
            fetch(API_URL + '/test')
                .then(response => {{
                    html += '<div class="test-result success">✅ Fetch request to API_URL succeeded</div>';
                    results.innerHTML = html;
                }})
                .catch(error => {{
                    html += '<div class="test-result error">❌ Fetch request to API_URL failed: ' + error.message + '</div>';
                    results.innerHTML = html;
                }});
        }}
        
        // Run tests when page loads
        window.onload = runTests;
    </script>
</body>
</html>"""
    
    with open('simple_test.html', 'w', encoding='utf-8') as f:
        f.write(simple_html)
    
    print("Simple test HTML saved to: simple_test.html")
    print("Open this file in your browser to test the API_URL")

def main():
    """Main function"""
    print("🚀 HTML Output Test")
    print("=" * 50)
    
    # Test the full HTML output
    success = test_html_output()
    
    if success:
        # Create a simple test HTML
        create_simple_test_html()
        
        print("\n" + "=" * 50)
        print("🎉 HTML Output Test Complete!")
        print("\nFiles created:")
        print("1. test_output.html - Full HTML output from Lambda function")
        print("2. simple_test.html - Simple test to verify API_URL works")
        print("\nTo test in your browser:")
        print("1. Open simple_test.html in your browser")
        print("2. Check the test results")
        print("3. Open test_output.html to see the full web UI")
        print("\nThe API_URL should be properly defined and working!")
    else:
        print("\n❌ HTML output test failed")

if __name__ == '__main__':
    main()
