#!/usr/bin/env python3
"""
Test Format Error
This script tests the .format() call to find the 'type' error
"""

def test_format_error():
    """Test the format error"""
    print("Testing .format() call...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the HTML content
        html_start = content.find('html_content = """')
        html_end = content.find('""".format(api_url=api_url)')
        
        if html_start != -1 and html_end != -1:
            print(f"Found HTML content from position {html_start} to {html_end}")
            
            # Extract the HTML template
            html_template = content[html_start + 18:html_end]
            
            print(f"HTML template length: {len(html_template)} characters")
            
            # Try to format it
            test_url = 'https://test.example.com'
            
            try:
                result = html_template.format(api_url=test_url)
                print("HTML formatting successful!")
            except KeyError as e:
                print(f"KeyError: Missing key {e}")
                print(f"The template expects a key that wasn't provided: {e}")
                
                # Find where this key is used in the template
                import re
                key_name = str(e).strip("'")
                pattern = f"{{{key_name}}}"
                matches = list(re.finditer(re.escape(pattern), html_template))
                for i, match in enumerate(matches):
                    start = max(0, match.start() - 50)
                    end = min(len(html_template), match.end() + 50)
                    context = html_template[start:end]
                    line_num = html_template[:match.start()].count('\n') + 1
                    print(f"\nOccurrence {i+1} at line ~{line_num}:")
                    print(f"Context: ...{context}...")
                    
            except Exception as e:
                print(f"Error: {type(e).__name__}: {e}")
        else:
            print("Could not find HTML content boundaries")
            print(f"html_start: {html_start}, html_end: {html_end}")
            
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == '__main__':
    test_format_error()
