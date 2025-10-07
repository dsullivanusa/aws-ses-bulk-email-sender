#!/usr/bin/env python3
"""
Fix Line 1566 F-String Syntax Error
This script fixes the specific f-string syntax error on line 1566
"""

import re

def fix_line_1566_syntax_error():
    """Fix the f-string syntax error on line 1566"""
    print("🔧 Fixing f-string syntax error on line 1566...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Find the specific problematic lines around line 1566
        # The issue is ${{}} should be {{}} to generate ${} in JavaScript
        lines = content.split('\n')
        
        if len(lines) >= 1566:
            print(f"Line 1566: {lines[1565]}")
            
            # Check if this line has the f-string syntax error
            if '${{' in lines[1565]:
                print("✅ Found f-string syntax error on line 1566")
                
                # Fix the f-string syntax by replacing ${{}} with {{}}
                # This will generate ${} in the JavaScript output
                fixed_line = lines[1565].replace('${{', '{{').replace('}}', '}}')
                lines[1565] = fixed_line
                
                print(f"Fixed line 1566: {fixed_line}")
                
                # Also check the surrounding lines for similar issues
                for i in range(1564, 1570):
                    if i < len(lines) and '${{' in lines[i]:
                        print(f"Also fixing line {i+1}: {lines[i]}")
                        lines[i] = lines[i].replace('${{', '{{').replace('}}', '}}')
                
                # Reconstruct the content
                content = '\n'.join(lines)
                
                if content != original_content:
                    # Create backup
                    backup_file = 'bulk_email_api_lambda.py.backup'
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(original_content)
                    print(f"✅ Created backup: {backup_file}")
                    
                    # Write fixed content
                    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print("✅ Fixed f-string syntax error on line 1566")
                    return True
                else:
                    print("❌ No changes were made")
                    return False
            else:
                print("❌ Line 1566 does not contain the expected f-string syntax error")
                return False
        else:
            print("❌ File does not have enough lines")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing line 1566: {e}")
        return False

def verify_fix():
    """Verify that the fix was applied correctly"""
    print("\n🔍 Verifying the fix...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        if len(lines) >= 1566:
            line_1566 = lines[1565]
            print(f"Line 1566 after fix: {line_1566}")
            
            # Check if the f-string syntax error is still present
            if '${{' in line_1566:
                print("❌ F-string syntax error still present")
                return False
            else:
                print("✅ F-string syntax error has been fixed")
                return True
        else:
            print("❌ File does not have enough lines")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying fix: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Line 1566 F-String Syntax Error Fix")
    print("=" * 50)
    
    # Fix the syntax error
    success = fix_line_1566_syntax_error()
    
    if success:
        # Verify the fix
        verify_success = verify_fix()
        
        print("\n" + "=" * 50)
        if verify_success:
            print("🎉 F-STRING SYNTAX ERROR FIXED!")
            print("\n✅ Line 1566 f-string syntax error has been resolved")
            print("✅ The Lambda function should now deploy successfully")
            print("\nNext steps:")
            print("1. Deploy the fixed Lambda function:")
            print("   python deploy_bulk_email_api.py")
            print("\n2. Clear browser cache (Ctrl+F5)")
            print("\n3. Test the web UI")
        else:
            print("⚠️  The fix may not have been applied correctly")
    else:
        print("\n❌ Could not fix the f-string syntax error")

if __name__ == '__main__':
    main()
