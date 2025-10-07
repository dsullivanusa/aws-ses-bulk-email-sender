#!/usr/bin/env python3
"""
Quick Syntax Check
This script quickly identifies syntax errors in the Lambda function
"""

import ast
import re

def check_python_syntax():
    """Check Python syntax and return the exact error"""
    print("🔍 Checking Python syntax...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the Python code
        try:
            ast.parse(content)
            print("✅ Python syntax is valid")
            return True, None
        except SyntaxError as e:
            print(f"❌ Python syntax error found:")
            print(f"   Line {e.lineno}: {e.text}")
            print(f"   Error: {e.msg}")
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            print(f"❌ Error parsing Python code: {e}")
            return False, str(e)
            
    except FileNotFoundError:
        print("❌ File bulk_email_api_lambda.py not found")
        return False, "File not found"
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False, str(e)

def check_javascript_syntax():
    """Check JavaScript syntax and return specific issues"""
    print("\n🔍 Checking JavaScript syntax...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for f-string syntax issues
        fstring_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if fstring_issues:
            issues.append(f"Found {len(fstring_issues)} f-string syntax issues: ${{}}")
        
        # Check for unclosed template literals
        template_literals = re.findall(r'`[^`]*`', content)
        for template in template_literals:
            if '${' in template and '}' not in template:
                issues.append(f"Unclosed template literal: {template[:50]}...")
        
        # Check for missing function definitions
        if 'function showTab(' not in content:
            issues.append("showTab function definition not found")
        
        if issues:
            print(f"❌ Found {len(issues)} JavaScript issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False, issues
        else:
            print("✅ No obvious JavaScript syntax issues found")
            return True, []
            
    except Exception as e:
        print(f"❌ Error checking JavaScript syntax: {e}")
        return False, [str(e)]

def main():
    """Main function"""
    print("🚀 Quick Syntax Check")
    print("=" * 30)
    
    # Check Python syntax
    python_ok, python_error = check_python_syntax()
    
    # Check JavaScript syntax
    js_ok, js_errors = check_javascript_syntax()
    
    print("\n" + "=" * 30)
    if python_ok and js_ok:
        print("🎉 All syntax checks passed!")
        print("   The Lambda function should deploy successfully")
    else:
        print("❌ Syntax issues found!")
        
        if not python_ok:
            print(f"\n🔧 Python syntax error: {python_error}")
            print("   Fix this error before deploying")
        
        if not js_ok:
            print(f"\n🔧 JavaScript syntax issues: {len(js_errors)}")
            for error in js_errors:
                print(f"   - {error}")
            print("   Run: python fix_api_url_undefined.py")

if __name__ == '__main__':
    main()
