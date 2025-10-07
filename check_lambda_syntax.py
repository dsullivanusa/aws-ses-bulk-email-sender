#!/usr/bin/env python3
"""
Check Lambda Function Syntax
This script checks for Python syntax errors in the Lambda function
"""

import ast
import sys

def check_python_syntax():
    """Check if the Lambda function has valid Python syntax"""
    print("🔍 Checking Python syntax in bulk_email_api_lambda.py...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse the Python code
        try:
            ast.parse(content)
            print("✅ Python syntax is valid")
            return True
        except SyntaxError as e:
            print(f"❌ Python syntax error found:")
            print(f"   Line {e.lineno}: {e.text}")
            print(f"   Error: {e.msg}")
            return False
        except Exception as e:
            print(f"❌ Error parsing Python code: {e}")
            return False
            
    except FileNotFoundError:
        print("❌ File bulk_email_api_lambda.py not found")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def check_javascript_syntax():
    """Check for obvious JavaScript syntax issues in the HTML/JS sections"""
    print("\n🔍 Checking for JavaScript syntax issues...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for f-string syntax issues
        import re
        fstring_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if fstring_issues:
            issues.append(f"Found {len(fstring_issues)} f-string syntax issues: ${{}}")
        
        # Check for unclosed template literals
        template_literals = re.findall(r'`[^`]*\$[^`]*`', content)
        for template in template_literals:
            if '${{' in template:
                issues.append(f"Template literal with f-string issue: {template[:50]}...")
        
        # Check for missing function definitions
        if 'function showTab(' not in content:
            issues.append("showTab function definition not found")
        
        if 'onclick="showTab(' in content and 'function showTab(' not in content:
            issues.append("showTab function is called but not defined")
        
        if issues:
            print(f"❌ Found {len(issues)} JavaScript issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ No obvious JavaScript syntax issues found")
            return True
            
    except Exception as e:
        print(f"❌ Error checking JavaScript syntax: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Lambda Function Syntax Checker")
    print("=" * 40)
    
    python_ok = check_python_syntax()
    js_ok = check_javascript_syntax()
    
    print("\n" + "=" * 40)
    if python_ok and js_ok:
        print("🎉 All syntax checks passed!")
        print("   The Lambda function should deploy successfully")
    else:
        print("❌ Syntax issues found!")
        print("   Fix these issues before deploying the Lambda function")
        
        if not python_ok:
            print("\n🔧 Python syntax issues need to be fixed")
        if not js_ok:
            print("\n🔧 JavaScript syntax issues need to be fixed")

if __name__ == '__main__':
    main()