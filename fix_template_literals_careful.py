#!/usr/bin/env python3
"""
Fix Template Literals Carefully
This script properly escapes JavaScript template literals for Python's .format()
WITHOUT breaking existing Python code
"""

import re

def fix_template_literals():
    """Fix template literals carefully"""
    print("Reading file...")
    
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the HTML content boundaries
    html_start = content.find('html_content = """')
    html_end = content.find('""".format(api_url=api_url)', html_start)
    
    if html_start == -1 or html_end == -1:
        print("Could not find HTML content boundaries")
        return False
    
    print(f"Found HTML content from {html_start} to {html_end}")
    
    # Extract the parts
    before_html = content[:html_start]
    html_section = content[html_start + 18:html_end]  # Skip 'html_content = """'
    after_html = content[html_end:]
    
    print(f"HTML section length: {len(html_section)} characters")
    
    # Now we need to escape all ${variable} to ${{variable}} for JavaScript template literals
    # BUT we need to keep {api_url} as-is because it's for Python's .format()
    
    # Strategy:
    # 1. Find all backtick strings (JavaScript template literals)
    # 2. Inside those, find all ${...} patterns
    # 3. Replace ${...} with ${{...}}
    
    fixed_html = []
    i = 0
    while i < len(html_section):
        if html_section[i] == '`':
            # Found start of template literal
            fixed_html.append('`')
            i += 1
            # Find the end of this template literal
            while i < len(html_section):
                if html_section[i] == '`':
                    fixed_html.append('`')
                    i += 1
                    break
                elif html_section[i] == '$' and i + 1 < len(html_section) and html_section[i + 1] == '{':
                    # Found ${, need to double the {
                    fixed_html.append('${{')
                    i += 2
                    # Now find the matching }
                    brace_count = 1
                    while i < len(html_section) and brace_count > 0:
                        if html_section[i] == '{':
                            brace_count += 1
                            fixed_html.append('{')
                        elif html_section[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # This is the closing }, need to double it
                                fixed_html.append('}}')
                            else:
                                fixed_html.append('}')
                        else:
                            fixed_html.append(html_section[i])
                        i += 1
                elif html_section[i] == '\\' and i + 1 < len(html_section):
                    # Escape sequence, copy both characters
                    fixed_html.append(html_section[i])
                    fixed_html.append(html_section[i + 1])
                    i += 2
                else:
                    fixed_html.append(html_section[i])
                    i += 1
        else:
            fixed_html.append(html_section[i])
            i += 1
    
    fixed_html_str = ''.join(fixed_html)
    
    # Rebuild the file
    new_content = before_html + 'html_content = """' + fixed_html_str + after_html
    
    # Save the fixed file
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Fixed template literals!")
    
    # Now test if it works
    print("\nTesting...")
    try:
        test_url = 'https://jcdcmail.cisa.dhs.gov'
        result = fixed_html_str.format(api_url=test_url)
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
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False

if __name__ == '__main__':
    fix_template_literals()
