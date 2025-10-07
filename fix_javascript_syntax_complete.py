#!/usr/bin/env python3
"""
Complete JavaScript Syntax Fix for bulk_email_api_lambda.py
Fixes all f-string syntax errors that generate invalid JavaScript
Run this script on your other host to fix the syntax issues
"""

import re
import os

def fix_all_javascript_syntax():
    """Fix all JavaScript syntax errors caused by incorrect f-string syntax"""
    
    print("🔧 Fixing all JavaScript syntax errors in bulk_email_api_lambda.py...")
    
    if not os.path.exists('bulk_email_api_lambda.py'):
        print("❌ Error: bulk_email_api_lambda.py not found in current directory")
        print("   Please run this script from the directory containing the Lambda file")
        return False
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = 0
        
        # Pattern to find all ${{}} in template literals
        pattern = r'\$\{\{([^}]+)\}\}'
        
        # Find all matches
        matches = re.findall(pattern, content)
        if matches:
            print(f"Found {len(matches)} instances of incorrect f-string syntax:")
            for i, match in enumerate(matches[:10]):  # Show first 10
                print(f"   {i+1}. ${{{{{match}}}}}")
            if len(matches) > 10:
                print(f"   ... and {len(matches) - 10} more")
        
        # Replace all ${{}} with ${} to generate valid JavaScript
        content = re.sub(pattern, r'${\1}', content)
        
        # Count how many replacements were made
        fixes_applied = len(matches)
        
        if content != original_content:
            # Create backup
            backup_file = 'bulk_email_api_lambda.py.backup'
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
            print(f"✅ Created backup: {backup_file}")
            
            # Write fixed content
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Applied {fixes_applied} fixes to JavaScript syntax")
            print("   All f-string syntax errors have been resolved")
            print("   The JavaScript should now be valid")
            
            return True
        else:
            print("❌ No syntax errors found to fix")
            print("   The file may already be correct")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing syntax: {e}")
        return False

def verify_fixes():
    """Verify that the fixes were applied correctly"""
    print("\n🔍 Verifying fixes...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for remaining ${{}} patterns
        remaining_issues = re.findall(r'\$\{\{[^}]+\}\}', content)
        if remaining_issues:
            print(f"⚠️  Found {len(remaining_issues)} remaining issues:")
            for issue in remaining_issues[:5]:
                print(f"   - {issue}")
            return False
        else:
            print("✅ No remaining f-string syntax errors found")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying fixes: {e}")
        return False

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
            
        return len(showtab_matches) > 0 and len(onclick_matches) > 0
            
    except Exception as e:
        print(f"❌ Error checking showTab: {e}")
        return False

def main():
    """Main function to run all fixes and checks"""
    print("🚀 JavaScript Syntax Fix Script")
    print("=" * 50)
    
    # Fix the syntax errors
    success = fix_all_javascript_syntax()
    
    if success:
        # Verify the fixes
        verify_success = verify_fixes()
        
        # Check showTab function
        showtab_ok = check_showtab_function()
        
        print("\n" + "=" * 50)
        if verify_success and showtab_ok:
            print("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
            print("\nNext steps:")
            print("1. Deploy the fixed Lambda function:")
            print("   python deploy_bulk_email_api.py")
            print("\n2. Clear browser cache (Ctrl+F5)")
            print("\n3. Test the web UI - tabs should work now")
        else:
            print("⚠️  Some issues may remain:")
            if not verify_success:
                print("   - F-string syntax errors may still exist")
            if not showtab_ok:
                print("   - showTab function issues detected")
    else:
        print("\n❌ Fixes could not be applied")
        print("   Please check the error messages above")

if __name__ == '__main__':
    main()
