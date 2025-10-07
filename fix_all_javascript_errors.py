#!/usr/bin/env python3
"""
Fix All JavaScript Syntax Errors in bulk_email_api_lambda.py
Fixes f-string syntax that's generating invalid JavaScript
"""

import re

def fix_javascript_syntax():
    """Fix all JavaScript syntax errors caused by incorrect f-string syntax"""
    
    print("🔧 Fixing all JavaScript syntax errors...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = 0
        
        # Fix 1: The pagination complete log message
        old_pattern1 = r'console\.log\(`✅ Pagination complete: Loaded \$\{\{allContacts\.length\}\} total contacts in \$\{\{pageCount\}\} pages`\);'
        new_pattern1 = 'console.log(`✅ Pagination complete: Loaded ${allContacts.length} total contacts in ${pageCount} pages`);'
        
        if re.search(old_pattern1, content):
            content = re.sub(old_pattern1, new_pattern1, content)
            fixes_applied += 1
            print("✅ Fixed pagination complete log message")
        
        # Fix 2: Any other ${{}} patterns in console.log statements
        old_pattern2 = r'\$\{\{([^}]+)\}\}'
        new_pattern2 = r'${\1}'
        
        # Only replace in JavaScript sections (after function definitions)
        js_sections = re.findall(r'(function\s+\w+\([^)]*\)\s*\{[^}]*\})', content, re.DOTALL)
        for section in js_sections:
            if '${{' in section:
                fixed_section = re.sub(old_pattern2, new_pattern2, section)
                content = content.replace(section, fixed_section)
                fixes_applied += 1
                print("✅ Fixed f-string syntax in JavaScript function")
        
        # Fix 3: Check for any remaining ${{}} patterns in the entire file
        remaining_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if remaining_issues:
            print(f"⚠️  Found {len(remaining_issues)} remaining ${{}} patterns:")
            for issue in remaining_issues[:5]:  # Show first 5
                print(f"   - {issue}")
        
        if content != original_content:
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Applied {fixes_applied} fixes to JavaScript syntax")
            print("   All f-string syntax errors should now be resolved")
        else:
            print("❌ No syntax errors found to fix")
            print("   The file may already be correct or the patterns are different")
            
    except Exception as e:
        print(f"❌ Error fixing syntax: {e}")

def check_showtab_function():
    """Check if showTab function is properly defined"""
    print("\n🔍 Checking showTab function definition...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for showTab function definition
        showtab_matches = re.findall(r'function\s+showTab\s*\([^)]*\)\s*\{', content)
        if showtab_matches:
            print(f"✅ Found {len(showtab_matches)} showTab function definition(s)")
        else:
            print("❌ showTab function not found!")
            print("   This would cause 'showTab is not defined' error")
        
        # Look for onclick="showTab(" calls
        onclick_matches = re.findall(r'onclick="showTab\([^)]*\)"', content)
        if onclick_matches:
            print(f"✅ Found {len(onclick_matches)} showTab onclick calls")
        else:
            print("❌ No showTab onclick calls found!")
            
    except Exception as e:
        print(f"❌ Error checking showTab: {e}")

if __name__ == '__main__':
    fix_javascript_syntax()
    check_showtab_function()
    print("\n💡 Next step: Deploy the fixed Lambda function")
    print("   python deploy_bulk_email_api.py")
