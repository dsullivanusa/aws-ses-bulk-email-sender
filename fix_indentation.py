#!/usr/bin/env python3
"""
Fix the indentation issue in bulk_email_api_lambda.py
"""

def fix_indentation():
    """Fix the JavaScript indentation issue"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and fix the problematic lines
    fixed_count = 0
    for i, line in enumerate(lines):
        # Fix the text variable line (should have 16 spaces, currently has 12)
        if 'const text = await file.text();' in line and line.startswith('            const text'):
            lines[i] = '                const text = await file.text();\n'
            fixed_count += 1
            print(f"Fixed line {i+1}: const text = await file.text();")
        
        # Fix the lines variable line (should have 16 spaces, currently has 12)
        elif 'const lines = text.split' in line and line.startswith('            const lines'):
            lines[i] = "                const lines = text.split('\\\\n').filter(line => line.trim());\n"
            fixed_count += 1
            print(f"Fixed line {i+1}: const lines = text.split...")
    
    if fixed_count > 0:
        # Write back the fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ Fixed {fixed_count} indentation issues")
    else:
        print("No indentation issues found")
    
    return fixed_count > 0

if __name__ == "__main__":
    fix_indentation()