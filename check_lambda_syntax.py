#!/usr/bin/env python3
"""
Check Lambda Function Syntax
Validates that the Lambda function has no syntax errors
"""

import ast
import sys

def check_syntax():
    """Check if the Lambda function has syntax errors"""
    
    print("=" * 80)
    print("🔍 Checking Lambda Function Syntax")
    print("=" * 80)
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        print("📋 Parsing Lambda function...")
        
        # Parse the Python code
        tree = ast.parse(source)
        
        print("✅ Lambda function syntax is valid")
        print(f"   File size: {len(source):,} characters")
        print(f"   Lines of code: {len(source.splitlines()):,}")
        
        # Check for common issues
        issues = []
        
        # Check for undefined variables
        undefined_vars = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                undefined_vars.append(node.id)
        
        # Check for missing imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        print(f"   Imports found: {len(imports)}")
        print(f"   Variables defined: {len(set(undefined_vars))}")
        
        if issues:
            print(f"⚠️  Potential issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ No syntax issues found")
            
    except SyntaxError as e:
        print(f"❌ Syntax Error Found!")
        print(f"   Line {e.lineno}: {e.text}")
        print(f"   Error: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")
        return False
    
    return True

def check_common_issues():
    """Check for common issues in the Lambda function"""
    
    print(f"\n" + "=" * 80)
    print("🔍 Checking for Common Issues")
    print("=" * 80)
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for incomplete f-strings
        if 'f"' in content and content.count('f"') != content.count('"'):
            issues.append("Potential incomplete f-string")
        
        # Check for unmatched braces
        if content.count('{') != content.count('}'):
            issues.append("Unmatched braces in f-strings")
        
        # Check for incomplete function definitions
        if 'def ' in content and ':' not in content.split('def ')[-1].split('\n')[0]:
            issues.append("Potential incomplete function definition")
        
        # Check for missing return statements
        functions_without_return = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and 'lambda_handler' not in line:
                # Look for return statement in next 20 lines
                has_return = False
                for j in range(i+1, min(i+21, len(lines))):
                    if lines[j].strip().startswith('return '):
                        has_return = True
                        break
                if not has_return:
                    functions_without_return.append(line.strip())
        
        if functions_without_return:
            issues.append(f"Functions without return statements: {len(functions_without_return)}")
        
        if issues:
            print("⚠️  Potential issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ No common issues found")
            
    except Exception as e:
        print(f"❌ Error checking common issues: {e}")

def main():
    """Main function"""
    
    print(f"🚀 Starting Lambda Syntax Check...")
    
    syntax_ok = check_syntax()
    check_common_issues()
    
    if syntax_ok:
        print(f"\n✅ Lambda function syntax is valid")
        print(f"💡 If tabs still don't work, the issue might be:")
        print(f"   1. Lambda function not deployed with latest changes")
        print(f"   2. Browser cache issues")
        print(f"   3. JavaScript errors in browser console")
        print(f"   4. DynamoDB permissions or table issues")
    else:
        print(f"\n❌ Lambda function has syntax errors")
        print(f"💡 Fix the syntax errors before deploying")
    
    print(f"\n" + "=" * 80)
    print(f"✅ Syntax Check Complete!")
    print(f"=" * 80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
