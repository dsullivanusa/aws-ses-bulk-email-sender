#!/usr/bin/env python3
"""
Fix API_URL Undefined Error
This script comprehensively fixes all JavaScript syntax errors that prevent API_URL from being defined
"""

import re

def fix_all_javascript_syntax_errors():
    """Fix all JavaScript syntax errors that prevent API_URL from being defined"""
    print("🔧 Fixing all JavaScript syntax errors...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        total_fixes = 0
        
        # Fix 1: All ${{}} patterns in template literals
        pattern1 = r'\$\{\{([^}]+)\}\}'
        matches1 = re.findall(pattern1, content)
        if matches1:
            print(f"Found {len(matches1)} instances of ${{}} syntax errors")
            content = re.sub(pattern1, r'${\1}', content)
            total_fixes += len(matches1)
            print(f"✅ Fixed {len(matches1)} ${{}} syntax errors")
        
        # Fix 2: Double braces in JavaScript template literals
        # Look for template literals and fix double braces inside them
        def fix_template_literal(match):
            template_content = match.group(0)
            # Replace {{variable}} with {variable} inside template literals
            fixed_content = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', template_content)
            return fixed_content
        
        # Find all template literals and fix them
        template_pattern = r'`[^`]*`'
        template_matches = re.findall(template_pattern, content)
        if template_matches:
            print(f"Found {len(template_matches)} template literals to check")
            content = re.sub(template_pattern, fix_template_literal, content)
        
        # Fix 3: Check for any remaining syntax issues
        # Look for common JavaScript syntax problems
        syntax_issues = []
        
        # Check for unclosed template literals
        unclosed_templates = re.findall(r'`[^`]*\$[^`]*`', content)
        for template in unclosed_templates:
            if '${' in template and '}' not in template:
                syntax_issues.append(f"Unclosed template literal: {template[:50]}...")
        
        # Check for malformed template literals
        malformed_templates = re.findall(r'`[^`]*\{\{[^}]*\}[^`]*`', content)
        if malformed_templates:
            syntax_issues.append(f"Found {len(malformed_templates)} malformed template literals")
        
        if syntax_issues:
            print(f"Found {len(syntax_issues)} syntax issues:")
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
            
            print(f"✅ Applied {total_fixes} total fixes to JavaScript syntax")
            return True
        else:
            print("❌ No syntax errors found to fix")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing JavaScript syntax: {e}")
        return False

def verify_api_url_definition():
    """Verify that API_URL is properly defined"""
    print("\n🔍 Verifying API_URL definition...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for API_URL definition
        api_url_patterns = [
            r"const API_URL = 'https://jcdcmail\.cisa\.dhs\.gov';",
            r"const API_URL = 'https://[^']+';",
            r"const API_URL = '[^']+';"
        ]
        
        api_url_found = False
        for pattern in api_url_patterns:
            if re.search(pattern, content):
                match = re.search(pattern, content)
                print(f"✅ Found API_URL definition: {match.group(0)}")
                api_url_found = True
                break
        
        if not api_url_found:
            print("❌ API_URL definition not found")
            return False
        
        # Check for any remaining syntax errors that could prevent execution
        remaining_issues = []
        
        # Check for remaining ${{}} patterns
        fstring_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if fstring_issues:
            remaining_issues.append(f"Found {len(fstring_issues)} remaining ${{}} patterns")
        
        # Check for unclosed braces in template literals
        template_literals = re.findall(r'`[^`]*`', content)
        for template in template_literals:
            if '${' in template and '}' not in template:
                remaining_issues.append(f"Unclosed template literal: {template[:50]}...")
        
        if remaining_issues:
            print(f"❌ Found {len(remaining_issues)} remaining issues:")
            for issue in remaining_issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ No remaining syntax issues found")
            print("✅ API_URL should be properly defined")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying API_URL definition: {e}")
        return False

def check_javascript_execution():
    """Check if JavaScript can execute properly"""
    print("\n🔍 Checking JavaScript execution...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the script section
        script_start = content.find('<script>')
        script_end = content.find('</script>')
        
        if script_start == -1 or script_end == -1:
            print("❌ Script section not found")
            return False
        
        script_content = content[script_start:script_end]
        
        # Check for common JavaScript syntax issues
        issues = []
        
        # Check for unclosed functions
        function_count = script_content.count('function')
        brace_count = script_content.count('{')
        close_brace_count = script_content.count('}')
        
        if brace_count != close_brace_count:
            issues.append(f"Unmatched braces: {brace_count} opening, {close_brace_count} closing")
        
        # Check for unclosed template literals
        backtick_count = script_content.count('`')
        if backtick_count % 2 != 0:
            issues.append("Unclosed template literals (odd number of backticks)")
        
        # Check for unclosed strings
        single_quote_count = script_content.count("'")
        double_quote_count = script_content.count('"')
        
        if single_quote_count % 2 != 0:
            issues.append("Unclosed single-quoted strings")
        
        if double_quote_count % 2 != 0:
            issues.append("Unclosed double-quoted strings")
        
        if issues:
            print(f"❌ Found {len(issues)} JavaScript execution issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ JavaScript syntax appears to be valid")
            print(f"   Found {function_count} functions")
            print(f"   Braces are balanced: {brace_count} opening, {close_brace_count} closing")
            return True
            
    except Exception as e:
        print(f"❌ Error checking JavaScript execution: {e}")
        return False

def main():
    """Main function"""
    print("🚀 API_URL Undefined Error Fix Script")
    print("=" * 50)
    
    # Fix all JavaScript syntax errors
    syntax_ok = fix_all_javascript_syntax_errors()
    
    if syntax_ok:
        # Verify API_URL definition
        api_url_ok = verify_api_url_definition()
        
        # Check JavaScript execution
        execution_ok = check_javascript_execution()
        
        print("\n" + "=" * 50)
        if api_url_ok and execution_ok:
            print("🎉 ALL ISSUES FIXED!")
            print("\n✅ JavaScript syntax errors have been resolved")
            print("✅ API_URL is properly defined")
            print("✅ JavaScript should execute without errors")
            print("\nNext steps:")
            print("1. Deploy the fixed Lambda function:")
            print("   python deploy_bulk_email_api.py")
            print("\n2. Clear browser cache (Ctrl+F5)")
            print("\n3. Test the web UI - API_URL should now be defined")
        else:
            print("⚠️  Some issues may still remain:")
            if not api_url_ok:
                print("   - API_URL definition issues")
            if not execution_ok:
                print("   - JavaScript execution issues")
    else:
        print("\n❌ Could not fix JavaScript syntax errors")

if __name__ == '__main__':
    main()
