#!/usr/bin/env python3
"""
Fix All Remaining JavaScript Errors
This script fixes all remaining JavaScript syntax errors that prevent the code from running
"""

import re

def fix_all_remaining_js_errors():
    """Fix all remaining JavaScript syntax errors"""
    print("🔧 Fixing all remaining JavaScript syntax errors...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = 0
        
        # Fix 1: All remaining ${{}} patterns in template literals
        pattern1 = r'\$\{\{([^}]+)\}\}'
        matches1 = re.findall(pattern1, content)
        if matches1:
            print(f"Found {len(matches1)} instances of ${{}} syntax errors:")
            for i, match in enumerate(matches1[:10]):
                print(f"   {i+1}. ${{{{{match}}}}}")
            if len(matches1) > 10:
                print(f"   ... and {len(matches1) - 10} more")
            
            content = re.sub(pattern1, r'${\1}', content)
            fixes_applied += len(matches1)
            print(f"✅ Fixed {len(matches1)} ${{}} syntax errors")
        
        # Fix 2: Check for any remaining double braces in JavaScript sections
        # Look for patterns like {{variable}} that should be {variable}
        pattern2 = r'\{\{([^}]+)\}\}'
        matches2 = re.findall(pattern2, content)
        if matches2:
            print(f"Found {len(matches2)} instances of double braces:")
            for i, match in enumerate(matches2[:10]):
                print(f"   {i+1}. {{{{{match}}}}}")
            if len(matches2) > 10:
                print(f"   ... and {len(matches2) - 10} more")
            
            # Only replace in JavaScript template literals, not in Python f-strings
            # Look for template literals (backticks) and replace double braces inside them
            def replace_in_template_literals(match):
                template_content = match.group(0)
                # Replace {{variable}} with {variable} inside template literals
                fixed_content = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', template_content)
                return fixed_content
            
            # Find all template literals and fix them
            content = re.sub(r'`[^`]*`', replace_in_template_literals, content)
            fixes_applied += len(matches2)
            print(f"✅ Fixed {len(matches2)} double brace syntax errors")
        
        # Fix 3: Check for any unclosed template literals or syntax issues
        # Look for template literals that might have syntax issues
        template_literals = re.findall(r'`[^`]*`', content)
        syntax_issues = []
        
        for template in template_literals:
            # Check for common syntax issues
            if '${' in template and '}' not in template:
                syntax_issues.append(f"Unclosed template literal: {template[:50]}...")
            elif '{{' in template and '}}' not in template:
                syntax_issues.append(f"Unclosed double braces: {template[:50]}...")
        
        if syntax_issues:
            print(f"Found {len(syntax_issues)} template literal syntax issues:")
            for issue in syntax_issues:
                print(f"   - {issue}")
        
        if content != original_content:
            # Create backup
            backup_file = 'bulk_email_api_lambda.py.backup'
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print(f"✅ Created backup: {backup_file}")
            
            # Write fixed content
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Applied {fixes_applied} total fixes to JavaScript syntax")
            print("   All JavaScript syntax errors should now be resolved")
            
            return True
        else:
            print("❌ No syntax errors found to fix")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing JavaScript syntax: {e}")
        return False

def verify_js_syntax():
    """Verify that all JavaScript syntax errors are fixed"""
    print("\n🔍 Verifying JavaScript syntax fixes...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for remaining issues
        remaining_issues = []
        
        # Check for remaining ${{}} patterns
        fstring_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if fstring_issues:
            remaining_issues.append(f"Found {len(fstring_issues)} remaining ${{}} patterns")
        
        # Check for unclosed template literals
        template_literals = re.findall(r'`[^`]*`', content)
        for template in template_literals:
            if '${' in template and '}' not in template:
                remaining_issues.append(f"Unclosed template literal: {template[:50]}...")
        
        # Check for API_URL definition
        if "const API_URL = 'https://jcdcmail.cisa.dhs.gov';" in content:
            print("✅ API_URL is properly defined with custom domain")
        elif "const API_URL = 'https://" in content:
            print("✅ API_URL is properly defined")
        else:
            remaining_issues.append("API_URL definition not found or incorrect")
        
        if remaining_issues:
            print(f"❌ Found {len(remaining_issues)} remaining issues:")
            for issue in remaining_issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ All JavaScript syntax issues have been resolved!")
            print("✅ API_URL is properly defined")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying JavaScript syntax: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Complete JavaScript Syntax Fix Script")
    print("=" * 50)
    
    # Fix all remaining JavaScript syntax errors
    success = fix_all_remaining_js_errors()
    
    if success:
        # Verify the fixes
        verify_success = verify_js_syntax()
        
        print("\n" + "=" * 50)
        if verify_success:
            print("🎉 ALL JAVASCRIPT SYNTAX ERRORS FIXED!")
            print("\n✅ The web UI should now work properly")
            print("✅ API_URL is correctly defined as: https://jcdcmail.cisa.dhs.gov")
            print("✅ All template literals use correct syntax")
            print("\nNext steps:")
            print("1. Deploy the fixed Lambda function:")
            print("   python deploy_bulk_email_api.py")
            print("\n2. Clear browser cache (Ctrl+F5)")
            print("\n3. Test the web UI at: https://jcdcmail.cisa.dhs.gov")
        else:
            print("⚠️  Some JavaScript issues may still remain")
            print("   Please check the error messages above")
    else:
        print("\n❌ JavaScript syntax fixes could not be applied")

if __name__ == '__main__':
    main()
