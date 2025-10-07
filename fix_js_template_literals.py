#!/usr/bin/env python3
"""
Fix JavaScript Template Literals
This script fixes f-string syntax errors in JavaScript template literals only
"""

import re

def fix_js_template_literals():
    """Fix f-string syntax errors in JavaScript template literals"""
    print("Fixing JavaScript template literals...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        with open('bulk_email_api_lambda.py.backup', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Created backup: bulk_email_api_lambda.py.backup")
        
        # Find all template literals (backticks) and fix f-string syntax inside them
        def fix_template_literal(match):
            template_content = match.group(0)
            # Replace ${{variable}} with ${variable} inside template literals
            fixed_content = re.sub(r'\$\{\{([^}]+)\}\}', r'${\1}', template_content)
            return fixed_content
        
        # Find all template literals and fix them
        template_pattern = r'`[^`]*`'
        original_content = content
        content = re.sub(template_pattern, fix_template_literal, content)
        
        # Count how many fixes were made
        fixes_made = len(re.findall(r'\$\{\{[^}]+\}\}', original_content))
        print(f"Fixed {fixes_made} f-string syntax errors in template literals")
        
        # Write fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("JavaScript template literals have been fixed")
        return True
        
    except Exception as e:
        print(f"Error fixing template literals: {e}")
        return False

def verify_fix():
    """Verify that the fix was applied correctly"""
    print("\nVerifying fix...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for any remaining ${{}} patterns
        remaining_errors = re.findall(r'\$\{\{[^}]+\}\}', content)
        if remaining_errors:
            print(f'Found {len(remaining_errors)} remaining f-string syntax errors:')
            for error in remaining_errors[:5]:
                print(f'  - {error}')
            return False
        else:
            print('No remaining f-string syntax errors found!')
        
        # Check Python syntax
        import ast
        try:
            ast.parse(content)
            print('Python syntax is valid!')
            return True
        except SyntaxError as e:
            print(f'Python syntax error: Line {e.lineno}: {e.msg}')
            return False
        
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == '__main__':
    success = fix_js_template_literals()
    if success:
        verify_fix()
