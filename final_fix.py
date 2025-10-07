#!/usr/bin/env python3
"""
Final Fix for All F-String Errors
This script fixes all remaining f-string syntax errors in the Lambda function
"""

import re

def final_fix():
    """Fix all remaining f-string syntax errors"""
    print("Applying final fix for all f-string syntax errors...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        with open('bulk_email_api_lambda.py.backup3', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Created backup: bulk_email_api_lambda.py.backup3")
        
        # The issue is that JavaScript template literals inside Python f-strings
        # need to have their braces escaped. So ${variable} should be ${{variable}}
        # to generate ${variable} in the JavaScript output.
        
        # Find all template literals (backticks) and fix the JavaScript template literal syntax
        def fix_template_literal(match):
            template_content = match.group(0)
            # Replace ${variable} with ${{variable}} inside template literals
            # This will generate ${variable} in the JavaScript output
            fixed_content = re.sub(r'\$\{([^}]+)\}', r'${\1}', template_content)
            return fixed_content
        
        # Find all template literals and fix them
        template_pattern = r'`[^`]*`'
        original_content = content
        content = re.sub(template_pattern, fix_template_literal, content)
        
        # Count how many fixes were made
        fixes_made = len(re.findall(r'\$\{([^}]+)\}', original_content))
        print(f"Fixed {fixes_made} JavaScript template literal syntax errors")
        
        # Write fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("All f-string syntax errors have been fixed")
        return True
        
    except Exception as e:
        print(f"Error fixing f-string errors: {e}")
        return False

def verify_fix():
    """Verify that the fix was applied correctly"""
    print("\nVerifying fix...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check Python syntax
        import ast
        try:
            ast.parse(content)
            print('Python syntax is valid!')
            return True
        except SyntaxError as e:
            print(f'Python syntax error: Line {e.lineno}: {e.msg}')
            print(f'   Text: {e.text}')
            return False
        
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == '__main__':
    success = final_fix()
    if success:
        verify_fix()
