#!/usr/bin/env python3
"""
Fix All Unescaped Variables
This script fixes all unescaped variables in JavaScript template literals
"""

import re

def fix_all_unescaped():
    """Fix all unescaped variables"""
    print("Fixing all unescaped variables...")
    
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the HTML content boundaries
    html_start = content.find('html_content = """')
    html_end = content.find('""".format(api_url=api_url)', html_start)
    
    if html_start == -1 or html_end == -1:
        print("Could not find HTML content boundaries")
        return False
    
    print(f"Found HTML content from {html_start} to {html_end}")
    
    # Extract the HTML section
    html_section = content[html_start:html_end + 27]
    
    # Replace ${variable} with ${{variable}} for all JavaScript template literals
    # But don't replace ${api_url} at line 1547
    # Pattern: ${anything} that is NOT already ${anything}
    fixed_html = re.sub(r'(?<!\{)\$\{', '${{', html_section)
    
    # Rebuild the file
    new_content = content[:html_start] + fixed_html + content[html_end + 27:]
    
    # Save the fixed file
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Fixed all unescaped variables!")
    
    # Now test if it works
    print("\nTesting...")
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    html_start = content.find('html_content = """')
    html_end = content.find('""".format(api_url=api_url)', html_start)
    html_template = content[html_start + 18:html_end]
    
    try:
        test_url = 'https://jcdcmail.cisa.dhs.gov'
        result = html_template.format(api_url=test_url)
        print("SUCCESS! HTML formatting works!")
        print(f"Result length: {len(result)} characters")
        
        # Check if API_URL is properly defined
        check_string = f"const API_URL = '{test_url}';"
        if check_string in result:
            print(f"API_URL is properly defined: {test_url}")
        else:
            print("API_URL is not properly defined")
        
        # Save the output
        with open('lambda_html_output.html', 'w', encoding='utf-8') as f:
            f.write(result)
        print("Saved output to: lambda_html_output.html")
        
        return True
    except KeyError as e:
        print(f"KeyError: Missing key '{e}'")
        return False
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False

if __name__ == '__main__':
    fix_all_unescaped()
