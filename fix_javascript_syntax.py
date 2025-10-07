#!/usr/bin/env python3
"""
Fix JavaScript Syntax Error at Line 3672
Fixes f-string syntax that's generating invalid JavaScript
"""

import re

def fix_syntax():
    """Fix the JavaScript syntax error"""
    
    print("🔧 Fixing JavaScript syntax error...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # The issue is that ${{}} in f-strings should be {{}} to generate ${} in JavaScript
        # Find lines with console.log that have ${{}} pattern
        
        original_content = content
        
        # Fix the specific line at 3673
        content = content.replace(
            '            console.log(`✅ Pagination complete: Loaded ${{allContacts.length}} total contacts in ${{pageCount}} pages`);',
            '            console.log(`✅ Pagination complete: Loaded ${allContacts.length} total contacts in ${pageCount} pages`);'
        )
        
        if content != original_content:
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Fixed JavaScript syntax error")
            print("   The f-string now generates valid JavaScript template literals")
        else:
            print("❌ Could not find the problematic line")
            print("   The line may have already been fixed or the syntax is different")
            
    except Exception as e:
        print(f"❌ Error fixing syntax: {e}")

if __name__ == '__main__':
    fix_syntax()
    print("\n💡 Next step: Deploy the fixed Lambda function")
    print("   python deploy_bulk_email_api.py")
