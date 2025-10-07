#!/usr/bin/env python3
"""
Find Unescaped Variables
This script finds all unescaped variables in JavaScript template literals
"""

import re

def find_unescaped_vars():
    """Find all unescaped variables"""
    print("Finding unescaped variables...")
    
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the HTML content
    html_start = content.find('html_content = """')
    html_end = content.find('""".format(api_url=api_url)', html_start)
    
    if html_start != -1 and html_end != -1:
        html_template = content[html_start + 18:html_end]
        
        # Find all {variable} patterns that are NOT {{variable}}
        # Pattern: ${variable} that should be ${{variable}}
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_\.]*)\}'
        matches = re.finditer(pattern, html_template)
        
        unescaped = []
        for match in matches:
            var_name = match.group(1)
            # Check if it's escaped (preceded by {)
            start_pos = match.start()
            if start_pos > 0 and html_template[start_pos - 1] != '{':
                unescaped.append((var_name, match.start()))
        
        if unescaped:
            print(f"Found {len(unescaped)} unescaped variables:")
            for var_name, pos in unescaped[:20]:
                line_num = html_template[:pos].count('\n') + 1
                # Get context
                line_start = html_template.rfind('\n', max(0, pos - 100), pos) + 1
                line_end = html_template.find('\n', pos, min(len(html_template), pos + 100))
                context = html_template[line_start:line_end]
                print(f"\nLine ~{line_num}: Variable '{var_name}'")
                print(f"Context: {context[:150]}")
        else:
            print("No unescaped variables found!")
            
        # Now try to format and see what error we get
        print("\n\nTrying to format...")
        try:
            test_url = 'https://test.example.com'
            result = html_template.format(api_url=test_url)
            print("SUCCESS! HTML formatting works!")
        except KeyError as e:
            print(f"KeyError: Missing key '{e}'")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
    else:
        print("Could not find HTML content boundaries")

if __name__ == '__main__':
    find_unescaped_vars()
