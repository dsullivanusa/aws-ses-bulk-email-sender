#!/usr/bin/env python3
"""
Quick Fix for F-String Errors

This script fixes the most common f-string errors in bulk_email_api_lambda.py
"""

def quick_fix_fstrings():
    """
    Quick fix for f-string errors
    """
    
    print("🔧 Quick Fix for F-String Errors")
    print("=" * 40)
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # List of specific f-strings to fix (without placeholders)
        fixes = [
            ('print(f"🔍 CC DUPLICATION DEBUG - EXCLUSION SETS:")', 'print("🔍 CC DUPLICATION DEBUG - EXCLUSION SETS:")'),
            ('print(f"🔍 CC DUPLICATION DEBUG - CONTACT PROCESSING:")', 'print("🔍 CC DUPLICATION DEBUG - CONTACT PROCESSING:")'),
            ('print(f"📎 Upload attachment request received")', 'print("📎 Upload attachment request received")'),
            ('print(f"Decoding base64 data...")', 'print("Decoding base64 data...")'),
            ('print(f"⚠️ No <img> tags found in campaign body!")', 'print("⚠️ No <img> tags found in campaign body!")'),
            ('print(f"📎 No attachments received")', 'print("📎 No attachments received")'),
            ('print(f"   ⚠️ No <img> tags found in received HTML body!")', 'print("   ⚠️ No <img> tags found in received HTML body!")'),
            ('print(f"   📎 Attachment details:")', 'print("   📎 Attachment details:")'),
            ('print(f"   📝 Cleaned HTML for preview (preserved blank lines as <p>&nbsp;</p>)")', 'print("   📝 Cleaned HTML for preview (preserved blank lines as <p>&nbsp;</p>)")'),
            ('print(f"      ✅ Replaced S3 key using pattern 1 (double quotes)")', 'print("      ✅ Replaced S3 key using pattern 1 (double quotes)")'),
            ('print(f"      ✅ Replaced S3 key using pattern 2 (single quotes)")', 'print("      ✅ Replaced S3 key using pattern 2 (single quotes)")'),
            ('print(f"      ✅ Replaced S3 key using pattern 3 (direct replacement)")', 'print("      ✅ Replaced S3 key using pattern 3 (direct replacement)")'),
            ('print(f"      ❌ No <img> tags found in HTML!")', 'print("      ❌ No <img> tags found in HTML!")'),
            ('print(f"   ✅ Saved preview metadata to DynamoDB")', 'print("   ✅ Saved preview metadata to DynamoDB")')
        ]
        
        changes_made = 0
        for old_str, new_str in fixes:
            if old_str in content:
                content = content.replace(old_str, new_str)
                changes_made += 1
                print(f"✅ Fixed: {old_str[:50]}...")
        
        if changes_made > 0:
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n✅ Fixed {changes_made} f-string errors")
            print("✅ File updated successfully")
        else:
            print("ℹ️  No matching f-string errors found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    quick_fix_fstrings()