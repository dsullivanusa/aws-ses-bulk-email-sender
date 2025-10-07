#!/usr/bin/env python3
"""
Fix Source Code
This script fixes all f-string syntax errors in bulk_email_api_lambda.py
"""

import re
import sys

def fix_source_code():
    """Fix all f-string syntax errors in the source code"""
    print("🔧 Fixing source code...")
    
    try:
        # Read the file
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        with open('bulk_email_api_lambda.py.backup', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Created backup: bulk_email_api_lambda.py.backup")
        
        # Count how many errors we're fixing
        errors_to_fix = len(re.findall(r'\$\{\{[^}]+\}\}', content))
        print(f"✅ Found {errors_to_fix} f-string syntax errors to fix")
        
        if errors_to_fix == 0:
            print("✅ No f-string syntax errors found")
            return True
        
        # Fix all f-string syntax errors: change ${{}} to {{}}
        # In Python f-strings, {{}} generates {} in the output
        # So ${{}} is invalid, but {{}} generates ${} which is what we want for JavaScript
        fixed_content = re.sub(r'\$\{\{([^}]+)\}\}', r'${\1}', content)
        
        # Write fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"✅ Fixed {errors_to_fix} f-string syntax errors")
        print("✅ Source code has been updated")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing source code: {e}")
        return False

def verify_fix():
    """Verify that the source code is now valid"""
    print("\n🔍 Verifying source code...")
    
    try:
        # Read the file
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for remaining f-string syntax errors
        remaining_errors = re.findall(r'\$\{\{[^}]+\}\}', content)
        
        if remaining_errors:
            print(f"❌ Found {len(remaining_errors)} remaining f-string syntax errors")
            for error in remaining_errors[:5]:
                print(f"   - {error}")
            return False
        
        # Check Python syntax
        import ast
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
        print(f"❌ Error verifying source code: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Source Code Fix Script")
    print("=" * 50)
    
    # Fix the source code
    success = fix_source_code()
    
    if success:
        # Verify the fix
        verify_success = verify_fix()
        
        print("\n" + "=" * 50)
        if verify_success:
            print("🎉 SOURCE CODE HAS BEEN FIXED!")
            print("\n✅ All f-string syntax errors have been resolved")
            print("✅ Python syntax is valid")
            print("✅ The Lambda function should now deploy successfully")
            print("\nNext steps:")
            print("1. Deploy the fixed Lambda function:")
            print("   python deploy_bulk_email_api.py")
            print("\n2. Clear browser cache (Ctrl+F5)")
            print("\n3. Test the web UI")
        else:
            print("⚠️  Some issues may still remain")
            print("   Please check the error messages above")
    else:
        print("\n❌ Could not fix source code")

if __name__ == '__main__':
    main()
