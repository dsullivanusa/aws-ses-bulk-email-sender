#!/usr/bin/env python3
"""
Fix the 'name: text is not defined' error in bulk_email_api_lambda.py
"""

def fix_lambda_error():
    """Fix potential issues causing the text undefined error"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for common issues that could cause "text is not defined"
    issues_found = []
    
    # 1. Check for function calls with missing parameters
    if 'fsWrite(' in content:
        issues_found.append("Found fsWrite calls - checking parameters")
    
    # 2. Check for undefined text variables
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # Look for standalone 'text' that's not defined
        if ' text' in line and not any(x in line for x in [
            'text =', 'def text', 'import text', '.text', 'text(', 
            '"text"', "'text'", 'text:', 'textContent', 'responseText',
            'originalText', 'errorText', 'text/html', 'text-', 'input type="text"'
        ]):
            # Check if it's actually a variable reference
            if 'text' in line and not line.strip().startswith('#'):
                issues_found.append(f"Line {i}: Potential undefined 'text' - {line.strip()}")
    
    if issues_found:
        print("Potential issues found:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("No obvious 'text' variable issues found")
    
    # The most likely cause is a missing parameter in a function call
    # Let's check if there are any function definitions that expect 'text' parameter
    print("\nChecking function definitions...")
    
    # Look for function definitions
    import re
    func_defs = re.findall(r'def\s+(\w+)\s*\([^)]*\):', content)
    print(f"Found {len(func_defs)} function definitions")
    
    # The error might be in the Lambda handler itself
    # Let's check if there's a missing variable in the lambda_handler
    print("\nThe error 'name: text is not defined' suggests:")
    print("1. There's a variable 'text' being used without being defined")
    print("2. This could be in a function call or variable assignment")
    print("3. Most likely in the web UI serving or API handling code")
    
    return True

if __name__ == "__main__":
    fix_lambda_error()