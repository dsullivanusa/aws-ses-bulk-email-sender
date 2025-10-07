#!/usr/bin/env python3
"""
Extract Lambda HTML
This script extracts the actual HTML from the Lambda function and creates a test file
"""

def extract_lambda_html():
    """Extract the HTML from the Lambda function"""
    print("Extracting HTML from Lambda function...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the HTML content between the triple quotes
        import re
        
        # Look for the HTML content in the serve_web_ui function
        html_start = content.find('html_content = """')
        if html_start == -1:
            print("Could not find HTML content start")
            return False
        
        # Find the end of the HTML content
        html_end = content.find('""".format(api_url=api_url)', html_start)
        if html_end == -1:
            print("Could not find HTML content end")
            return False
        
        # Extract the HTML template
        html_template = content[html_start + 18:html_end]  # 18 = len('html_content = """')
        
        # Set the API URL
        api_url = "https://jcdcmail.cisa.dhs.gov"
        
        # Format the HTML with the API URL
        html_content = html_template.format(api_url=api_url)
        
        # Save the HTML to a file
        with open('lambda_output.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("Lambda HTML output saved to: lambda_output.html")
        
        # Check if API_URL is properly defined
        if f"const API_URL = '{api_url}';" in html_content:
            print("API_URL is properly defined in the HTML")
        else:
            print("API_URL is not properly defined in the HTML")
        
        # Check the size of the HTML
        print(f"HTML file size: {len(html_content)} characters")
        
        return True
        
    except Exception as e:
        print(f"Error extracting HTML: {e}")
        return False

if __name__ == '__main__':
    extract_lambda_html()
