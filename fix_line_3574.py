#!/usr/bin/env python3
"""
Fix the broken line 3574 that has a line break in the middle
"""

def fix_line_3574():
    """Fix the JavaScript syntax error on line 3574"""
    
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and fix line 3574 (0-based index 3573)
    if len(lines) > 3573:
        # Check if line 3574 has the issue
        if "const errorMsg = 'Column count mismatch:" in lines[3573]:
            # The line is split incorrectly - fix it
            lines[3573] = "                            const errorMsg = 'Column count mismatch: ' + values.length + ' columns found, ' + headers.length + ' expected';\n"
            print('✅ Fixed line 3574 - removed line break in string')
        else:
            print('Line 3574 does not have the expected content')
    
    # Write back
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print('File updated')
    
    # Verify the fix
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print('\nVerification - lines 3573-3577:')
    for i in range(3572, 3577):
        if i < len(lines):
            print(f'{i+1}: {lines[i].rstrip()}')

if __name__ == "__main__":
    fix_line_3574()