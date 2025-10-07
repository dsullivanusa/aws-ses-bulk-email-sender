#!/usr/bin/env python3
"""
Verify Final Fix
This script verifies that all f-string syntax errors have been fixed
"""

import re
import ast

def verify_final_fix():
    """Verify that all f-string syntax errors have been fixed"""
    print("Verifying final fix...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check Python syntax
        try:
            ast.parse(content)
            print('Python syntax is valid!')
        except SyntaxError as e:
            print(f'Python syntax error: Line {e.lineno}: {e.msg}')
            return False
        
        # Check for any remaining ${{}} patterns that might cause issues
        remaining_errors = re.findall(r'\$\{\{[^}]+\}\}', content)
        if remaining_errors:
            print(f'Found {len(remaining_errors)} remaining f-string syntax errors:')
            for error in remaining_errors[:5]:
                print(f'  - {error}')
            return False
        else:
            print('No remaining f-string syntax errors found!')
        
        # Check for any unclosed template literals
        template_literals = re.findall(r'`[^`]*`', content)
        unclosed_templates = [t for t in template_literals if '${' in t and '}' not in t]
        if unclosed_templates:
            print(f'Found {len(unclosed_templates)} unclosed template literals')
            return False
        else:
            print('All template literals appear to be properly closed')
        
        print('All checks passed! The source code is now fixed.')
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == '__main__':
    verify_final_fix()
