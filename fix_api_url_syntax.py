#!/usr/bin/env python3
"""
Fix API_URL Syntax Errors
This script fixes all instances of ${{API_URL}} to ${API_URL} in the JavaScript code
"""

import re

def fix_api_url_syntax():
    """Fix all API_URL syntax errors"""
    print("🔧 Fixing API_URL syntax errors...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_applied = 0
        
        # Pattern to find all ${{API_URL}} instances
        pattern = r'\$\{\{API_URL\}\}'
        
        # Find all matches
        matches = re.findall(pattern, content)
        if matches:
            print(f"Found {len(matches)} instances of ${{API_URL}} syntax errors:")
            for i, match in enumerate(matches[:10]):  # Show first 10
                print(f"   {i+1}. {match}")
            if len(matches) > 10:
                print(f"   ... and {len(matches) - 10} more")
        
        # Replace all ${{API_URL}} with ${API_URL}
        content = re.sub(pattern, '${API_URL}', content)
        
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
            
            print(f"✅ Applied {fixes_applied} fixes to API_URL syntax")
            print("   All API_URL references should now work correctly")
            
            return True
        else:
            print("❌ No API_URL syntax errors found to fix")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing API_URL syntax: {e}")
        return False

def verify_api_url_fixes():
    """Verify that the API_URL fixes were applied correctly"""
    print("\n🔍 Verifying API_URL fixes...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for remaining ${{API_URL}} patterns
        remaining_issues = re.findall(r'\$\{\{API_URL\}\}', content)
        if remaining_issues:
            print(f"❌ Found {len(remaining_issues)} remaining API_URL syntax errors")
            return False
        else:
            print("✅ No remaining API_URL syntax errors found")
            
            # Check that API_URL is properly defined
            if "const API_URL = '{api_url}';" in content:
                print("✅ API_URL is properly defined")
                return True
            else:
                print("❌ API_URL definition not found")
                return False
            
    except Exception as e:
        print(f"❌ Error verifying API_URL fixes: {e}")
        return False

def main():
    """Main function"""
    print("🚀 API_URL Syntax Fix Script")
    print("=" * 40)
    
    # Fix the API_URL syntax errors
    success = fix_api_url_syntax()
    
    if success:
        # Verify the fixes
        verify_success = verify_api_url_fixes()
        
        print("\n" + "=" * 40)
        if verify_success:
            print("🎉 ALL API_URL FIXES APPLIED SUCCESSFULLY!")
            print("\nNext steps:")
            print("1. Deploy the fixed Lambda function:")
            print("   python deploy_bulk_email_api.py")
            print("\n2. Clear browser cache (Ctrl+F5)")
            print("\n3. Test the web UI - 502 error should be resolved")
        else:
            print("⚠️  Some API_URL issues may remain")
    else:
        print("\n❌ API_URL fixes could not be applied")

if __name__ == '__main__':
    main()
