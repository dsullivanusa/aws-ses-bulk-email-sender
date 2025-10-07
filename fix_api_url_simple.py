#!/usr/bin/env python3
"""
Fix API_URL Definition - Simple Approach
This script fixes the API_URL definition issue in the Lambda function
"""

def fix_api_url_definition():
    """Fix the API_URL definition issue"""
    print("Fixing API_URL definition...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        with open('bulk_email_api_lambda.py.backup4', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Created backup: bulk_email_api_lambda.py.backup4")
        
        # The issue is that the f-string is not processing the {api_url} placeholder correctly
        # because of the JavaScript template literals inside it. We need to ensure the API_URL
        # is properly defined by using a different approach.
        
        # Replace the f-string approach with string formatting
        # Change from: html_content = f"""..."""
        # To: html_content = """...""".format(api_url=api_url)
        
        if 'html_content = f"""' in content:
            # Replace f-string with regular string and format
            content = content.replace(
                'html_content = f"""',
                'html_content = """'
            )
            # Find the first """ and replace it with """.format(api_url=api_url)
            first_quote = content.find('"""')
            if first_quote != -1:
                content = content[:first_quote] + '""".format(api_url=api_url)' + content[first_quote + 3:]
        
        # Write fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("API_URL definition has been fixed")
        return True
        
    except Exception as e:
        print(f"Error fixing API_URL definition: {e}")
        return False

def verify_fix():
    """Verify that the fix was applied correctly"""
    print("\nVerifying fix...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the fix was applied
        if 'html_content = """' in content and '.format(api_url=api_url)' in content:
            print("API_URL definition fix was applied successfully")
            return True
        else:
            print("API_URL definition fix was not applied")
            return False
        
    except Exception as e:
        print(f"Error verifying fix: {e}")
        return False

if __name__ == '__main__':
    success = fix_api_url_definition()
    if success:
        verify_fix()
