#!/usr/bin/env python3
"""
Check line 3574 for JavaScript syntax error
"""

def check_line_3574():
    """Check the specific line causing the syntax error"""
    
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if len(lines) >= 3574:
        line = lines[3573]  # 0-based index
        print(f'Line 3574: {line.rstrip()}')
        print(f'Line length: {len(line)}')
        
        if len(line) > 112:
            print(f'Character 113: "{line[112]}"')
            print(f'Characters around 113: "{line[110:116]}"')
        else:
            print('Line is shorter than 113 characters')
        
        # Show context around line 3574
        print('\nContext:')
        for i in range(max(0, 3570), min(len(lines), 3578)):
            marker = '>>> ' if i == 3573 else '    '
            print(f'{marker}{i+1}: {lines[i].rstrip()}')
            
        # Look for common JavaScript syntax issues
        if ')' in line and '(' in line:
            print('\nChecking parentheses balance...')
            open_parens = line.count('(')
            close_parens = line.count(')')
            print(f'Open parentheses: {open_parens}')
            print(f'Close parentheses: {close_parens}')
            if open_parens != close_parens:
                print('❌ Unbalanced parentheses!')
            else:
                print('✅ Parentheses are balanced')
                
        # Check for other common issues
        if line.strip().endswith(','):
            print('⚠️  Line ends with comma - might be missing continuation')
        if '{{' in line and '}}' not in line:
            print('⚠️  Unmatched curly braces')
            
    else:
        print(f'File only has {len(lines)} lines')

if __name__ == "__main__":
    check_line_3574()