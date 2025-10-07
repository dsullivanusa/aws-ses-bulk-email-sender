#!/usr/bin/env python3
"""
Final Verification
This script verifies that all fixes have been applied correctly
"""

import ast
import re

def final_verification():
    """Verify that all fixes have been applied correctly"""
    print("Final verification...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check Python syntax
        try:
            ast.parse(content)
            print("Python syntax is valid!")
        except SyntaxError as e:
            print(f"Python syntax error: Line {e.lineno}: {e.msg}")
            return False
        
        # Check that the API_URL definition fix was applied
        if 'html_content = """' in content and '.format(api_url=api_url)' in content:
            print("API_URL definition fix was applied successfully")
        else:
            print("API_URL definition fix was not applied")
            return False
        
        # Check that the API_URL is properly defined in the JavaScript
        if "const API_URL = '{api_url}';" in content:
            print("API_URL is properly defined in JavaScript")
        else:
            print("API_URL is not properly defined in JavaScript")
            return False
        
        # Check for any remaining f-string syntax errors
        remaining_errors = re.findall(r'\$\{\{[^}]+\}\}', content)
        if remaining_errors:
            print(f"Found {len(remaining_errors)} remaining f-string syntax errors")
            return False
        else:
            print("No remaining f-string syntax errors found")
        
        print("All checks passed! The source code is now fixed.")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    final_verification()
