#!/usr/bin/env python3
"""
Apply CC Duplication Fix to Lambda

This script applies the CC duplication fix directly to bulk_email_api_lambda.py
"""

import re

def apply_cc_fix_to_lambda():
    """
    Apply the CC duplication fix to the bulk_email_api_lambda.py file
    """
    
    print("🔧 Applying CC Duplication Fix to bulk_email_api_lambda.py")
    print("=" * 60)
    
    try:
        # Read the current file
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ Successfully read bulk_email_api_lambda.py")
        
        # Check if fix is already applied
        if "🔍 CC DUPLICATION DEBUG" in content:
            print("⚠️  CC duplication debug logging already present")
            return True
        
        # Apply Fix 1: Enhanced exclusion logging
        fix1_pattern = r'(cc_bcc_combined = cc_set \| bcc_set)'
        fix1_replacement = r'''\1
        
        # DEBUG: Enhanced logging for CC duplication diagnosis
        print(f"🔍 CC DUPLICATION DEBUG - EXCLUSION SETS:")
        print(f"   CC set: {cc_set}")
        print(f"   BCC set: {bcc_set}")
        print(f"   Combined exclusion set: {cc_bcc_combined}")
        print(f"   Exclusion set size: {len(cc_bcc_combined)}")'''
        
        if re.search(fix1_pattern, content):
            content = re.sub(fix1_pattern, fix1_replacement, content)
            print("✅ Applied Fix 1: Enhanced exclusion logging")
        else:
            print("⚠️  Could not find cc_bcc_combined pattern for Fix 1")
        
        # Apply Fix 2: Enhanced contact processing logging
        fix2_pattern = r'(contacts = \[\]\s+excluded_count = 0\s+for email in target_contact_emails:)'
        fix2_replacement = r'''contacts = []
        excluded_count = 0
        
        print(f"🔍 CC DUPLICATION DEBUG - CONTACT PROCESSING:")
        
        for email in target_contact_emails:'''
        
        if re.search(fix2_pattern, content, re.MULTILINE):
            content = re.sub(fix2_pattern, fix2_replacement, content, flags=re.MULTILINE)
            print("✅ Applied Fix 2: Enhanced contact processing logging")
        else:
            print("⚠️  Could not find contact processing pattern for Fix 2")
        
        # Apply Fix 3: Enhanced exclusion print statement
        fix3_pattern = r'print\(f"Excluding \{email\} from primary recipients \(on CC/BCC list\)"\)'
        fix3_replacement = r'''print(f"   ✅ EXCLUDING {email} from primary recipients (found in CC/BCC list)")
                    print(f"      Normalized: {normalized_email}")
                    print(f"      In exclusion set: {normalized_email in cc_bcc_combined}")'''
        
        if re.search(fix3_pattern, content):
            content = re.sub(fix3_pattern, fix3_replacement, content)
            print("✅ Applied Fix 3: Enhanced exclusion print statement")
        else:
            print("⚠️  Could not find exclusion print pattern for Fix 3")
        
        # Apply Fix 4: Add contact processing summary
        fix4_pattern = r'(excluded_count \+= 1\s+else:)'
        fix4_replacement = r'''excluded_count += 1
                else:
                    print(f"   ➕ ADDING {email} as regular contact")'''
        
        if re.search(fix4_pattern, content, re.MULTILINE):
            content = re.sub(fix4_pattern, fix4_replacement, content, flags=re.MULTILINE)
            print("✅ Applied Fix 4: Enhanced contact addition logging")
        else:
            print("⚠️  Could not find contact addition pattern for Fix 4")
        
        # Apply Fix 5: Add summary after contact processing
        # Look for the end of the contact processing loop
        fix5_pattern = r'(agency_name.*?\'\s*\}\s*\)\s*print\(f"Queuing)'
        fix5_replacement = r'''\1
        
        print(f"📊 CC DUPLICATION DEBUG - CONTACT SUMMARY:")
        print(f"   Total target emails: {len(target_contact_emails)}")
        print(f"   Regular contacts created: {len(contacts)}")
        print(f"   Excluded (CC/BCC): {excluded_count}")
        print(f"   CC recipients to queue separately: {len(cc_list)}")
        print(f"   BCC recipients to queue separately: {len(bcc_list)}")
        
        print(f"Queuing'''
        
        if re.search(fix5_pattern, content, re.DOTALL):
            content = re.sub(fix5_pattern, fix5_replacement, content, flags=re.DOTALL)
            print("✅ Applied Fix 5: Contact processing summary")
        else:
            print("⚠️  Could not find contact summary insertion point for Fix 5")
        
        # Write the updated file
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Successfully updated bulk_email_api_lambda.py")
        print()
        print("🎯 NEXT STEPS:")
        print("1. Deploy the updated Lambda function")
        print("2. Test with a campaign containing CC recipients")
        print("3. Check CloudWatch logs for the enhanced debug output")
        print("4. Verify that CC recipients no longer receive duplicate emails")
        
        return True
        
    except FileNotFoundError:
        print("❌ bulk_email_api_lambda.py not found in current directory")
        return False
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")
        return False

if __name__ == "__main__":
    apply_cc_fix_to_lambda()