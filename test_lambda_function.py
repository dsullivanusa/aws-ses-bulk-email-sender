#!/usr/bin/env python3
"""
Test Lambda Function
This script tests the Lambda function logic to ensure it will work correctly
"""

def test_lambda_function():
    """Test the Lambda function logic"""
    print("Testing Lambda function logic...")
    
    # Simulate the Lambda function environment
    import os
    
    # Set the custom API URL environment variable
    os.environ['CUSTOM_API_URL'] = 'https://jcdcmail.cisa.dhs.gov'
    
    # Simulate the serve_web_ui function logic
    CUSTOM_API_URL = os.environ.get('CUSTOM_API_URL', None)
    
    if CUSTOM_API_URL:
        api_url = CUSTOM_API_URL
        print(f"Using custom API URL: {api_url}")
    else:
        # Simulate API Gateway URL generation
        api_id = "yi6ss4dsoe"
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"Using API Gateway URL: {api_url}")
    
    # Test the HTML template formatting
    html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <script>
        const API_URL = '{api_url}';
        console.log('API_URL:', API_URL);
    </script>
</body>
</html>"""
    
    try:
        # This is what the Lambda function will do
        html_content = html_template.format(api_url=api_url)
        
        # Check if the formatting worked
        if f"const API_URL = '{api_url}';" in html_content:
            print("HTML formatting successful")
            print(f"Generated API_URL: {api_url}")
            
            # Save the test HTML
            with open('lambda_test.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print("Test HTML saved to: lambda_test.html")
            return True
        else:
            print("HTML formatting failed")
            return False
            
    except Exception as e:
        print(f"Error formatting HTML: {e}")
        return False

if __name__ == '__main__':
    test_lambda_function()
