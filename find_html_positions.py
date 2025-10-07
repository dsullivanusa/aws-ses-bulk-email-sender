#!/usr/bin/env python3
"""
Find HTML Positions
This script finds the positions of the HTML content in the Lambda function
"""

def find_html_positions():
    """Find the positions of the HTML content"""
    print("Finding HTML content positions...")
    
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the HTML content start
    html_start = content.find('html_content = """')
    print(f"html_content = position: {html_start}")
    
    # Find the HTML content end (start searching after html_start)
    html_end = content.find('""".format(api_url=api_url)', html_start)
    print(f".format position: {html_end}")
    
    # Also try with space
    html_end2 = content.find('   """.format(api_url=api_url)', html_start)
    print(f".format position (with spaces): {html_end2}")
    
    if html_start != -1 and html_end != -1:
        # Extract the HTML template
        html_template = content[html_start + 18:html_end]
        print(f"HTML template length: {len(html_template)} characters")
        
        # Show first 200 characters of the template
        print("\nFirst 200 characters of template:")
        print(html_template[:200])
        
        # Show last 200 characters of the template
        print("\nLast 200 characters of template:")
        print(html_template[-200:])
        
        # Try to format it
        try:
            test_url = 'https://jcdcmail.cisa.dhs.gov'
            result = html_template.format(api_url=test_url)
            print("\nHTML formatting successful!")
            print(f"Result length: {len(result)} characters")
            
            # Check if API_URL is properly defined
            check_string = f"const API_URL = '{test_url}';"
            if check_string in result:
                print(f"API_URL is properly defined: {test_url}")
            else:
                print("API_URL is not properly defined")
                
            # Save the result for testing
            with open('lambda_html_output.html', 'w', encoding='utf-8') as f:
                f.write(result)
            print("Saved output to: lambda_html_output.html")
            
        except KeyError as e:
            print(f"\nKeyError: Missing key '{e}'")
        except Exception as e:
            print(f"\nError: {type(e).__name__}: {e}")
    else:
        print("Could not find HTML content boundaries")

if __name__ == '__main__':
    find_html_positions()
