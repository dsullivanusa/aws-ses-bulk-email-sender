#!/usr/bin/env python3
"""
Test API_URL Generation
This script tests how the API_URL will be generated in the Lambda function
"""

def test_api_url_generation():
    """Test how API_URL is generated"""
    print("Testing API_URL generation...")
    
    # Simulate the logic from serve_web_ui function
    CUSTOM_API_URL = "https://jcdcmail.cisa.dhs.gov"  # Your custom domain
    
    if CUSTOM_API_URL:
        api_url = CUSTOM_API_URL
        print(f"Using custom API URL: {api_url}")
    else:
        # Simulate API Gateway URL generation
        api_id = "yi6ss4dsoe"  # From your previous message
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"Using API Gateway URL: {api_url}")
    
    # Test the string formatting (this is what the Lambda function will do)
    html_template = """<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <script>
        const API_URL = '{api_url}';
        console.log('API_URL is:', API_URL);
    </script>
</body>
</html>"""
    
    # This is what the Lambda function will do
    html_content = html_template.format(api_url=api_url)
    
    # Extract the API_URL from the generated HTML
    import re
    api_url_match = re.search(r"const API_URL = '([^']+)';", html_content)
    if api_url_match:
        generated_api_url = api_url_match.group(1)
        print(f"Generated API_URL in JavaScript: {generated_api_url}")
        
        if generated_api_url == api_url:
            print("✅ API_URL is correctly generated!")
            return True
        else:
            print("❌ API_URL generation failed")
            return False
    else:
        print("❌ Could not find API_URL in generated HTML")
        return False

if __name__ == '__main__':
    test_api_url_generation()
