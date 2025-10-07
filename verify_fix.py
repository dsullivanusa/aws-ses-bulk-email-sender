#!/usr/bin/env python3
"""
Verify Fix
This script verifies that the f-string syntax errors have been fixed
"""

import re
import ast

def verify_fix():
    """Verify that the f-string syntax errors have been fixed"""
    print("Verifying fix...")
    
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
    verify_fix()
