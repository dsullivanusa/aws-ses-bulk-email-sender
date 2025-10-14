#!/usr/bin/env python3
"""
Fix CSS curly braces in bulk_email_api_lambda.py
"""

def fix_css_braces():
    """Fix single curly braces to double curly braces in CSS strings"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and fix CSS lines with single curly braces
    css_fixes = [
        ("'.ql-align-center { text-align: center; }'", "'.ql-align-center {{ text-align: center; }}'"),
        ("'.ql-align-right { text-align: right; }'", "'.ql-align-right {{ text-align: right; }}'"),
        ("'.ql-align-left { text-align: left; }'", "'.ql-align-left {{ text-align: left; }}'"),
        ("'.ql-align-justify { text-align: justify; }'", "'.ql-align-justify {{ text-align: justify; }}'"),
        ("'.ql-indent-1 { padding-left: 3em; }'", "'.ql-indent-1 {{ padding-left: 3em; }}'"),
        ("'.ql-indent-2 { padding-left: 6em; }'", "'.ql-indent-2 {{ padding-left: 6em; }}'"),
        ("'.ql-indent-3 { padding-left: 9em; }'", "'.ql-indent-3 {{ padding-left: 9em; }}'"),
        ("'.ql-size-small { font-size: 0.75em; }'", "'.ql-size-small {{ font-size: 0.75em; }}'"),
        ("'.ql-size-large { font-size: 1.5em; }'", "'.ql-size-large {{ font-size: 1.5em; }}'"),
        ("'.ql-size-huge { font-size: 2.5em; }'", "'.ql-size-huge {{ font-size: 2.5em; }}'"),
    ]
    
    fixed_count = 0
    for old_css, new_css in css_fixes:
        if old_css in content:
            content = content.replace(old_css, new_css)
            fixed_count += 1
            print(f"Fixed: {old_css}")
    
    # Also fix any other CSS properties that might have single braces
    import re
    
    # Find CSS lines with single braces in f-strings
    pattern = r"'\.ql-[^']*\s*\{\s*[^}]*\s*\}'"
    matches = re.findall(pattern, content)
    
    for match in matches:
        if '{{' not in match:  # Only fix if not already double braces
            fixed_match = match.replace('{', '{{').replace('}', '}}')
            if match != fixed_match:
                content = content.replace(match, fixed_match)
                fixed_count += 1
                print(f"Auto-fixed: {match} -> {fixed_match}")
    
    if fixed_count > 0:
        # Write back the fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed {fixed_count} CSS brace issues")
    else:
        print("No CSS brace issues found")
    
    return fixed_count > 0

if __name__ == "__main__":
    fix_css_braces()