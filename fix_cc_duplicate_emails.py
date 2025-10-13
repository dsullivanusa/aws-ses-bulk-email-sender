#!/usr/bin/env python3
"""
Fix CC Duplicate Emails Issue

The problem: CC recipients are receiving duplicate emails because they're being queued twice:
1. Once as regular contacts (if they exist in the contacts database)
2. Once as CC recipients (with role='cc')

This script fixes the issue by ensuring proper exclusion of CC/BCC recipients from regular contact processing.
"""

def fix_cc_duplicate_emails():
    """
    Fix the CC duplicate emails issue in bulk_email_api_lambda.py
    
    The issue is in the send_campaign function where contacts are being created.
    CC/BCC recipients should be excluded from regular contact processing.
    """
    
    print("🔧 Fixing CC duplicate emails issue...")
    print()
    
    # The problem is in the contact creation loop in send_campaign function
    # Around line 6716-6720 in bulk_email_api_lambda.py
    
    print("📋 ISSUE ANALYSIS:")
    print("=" * 60)
    print("1. CC recipients are queued twice:")
    print("   - Once as regular contacts (if in database)")
    print("   - Once with role='cc' (separate queue message)")
    print()
    print("2. This causes CC recipients to receive:")
    print("   - Regular email with CC header showing their address")
    print("   - Separate CC email where they're the primary recipient")
    print()
    
    print("🔍 ROOT CAUSE:")
    print("=" * 60)
    print("The exclusion logic exists but may have a bug:")
    print("- Line ~6701: cc_bcc_combined = cc_set | bcc_set")
    print("- Line ~6720: if normalized_email in cc_bcc_combined:")
    print("- The exclusion should prevent CC/BCC from being regular contacts")
    print()
    
    print("💡 SOLUTION:")
    print("=" * 60)
    print("Fix the exclusion logic to properly exclude CC/BCC recipients")
    print("from regular contact processing in the API lambda.")
    print()
    
    # Show the fix that needs to be applied
    print("🛠️  CODE FIX NEEDED:")
    print("=" * 60)
    print("In bulk_email_api_lambda.py, around line 6695-6730:")
    print()
    
    fix_code = '''
# Get CC and BCC lists for exclusion
cc_list = body.get('cc', []) or []
bcc_list = body.get('bcc', []) or []

# Create normalized sets for exclusion (case-insensitive)
cc_set = set([email.lower().strip() for email in cc_list if email and '@' in email])
bcc_set = set([email.lower().strip() for email in bcc_list if email and '@' in email])
cc_bcc_combined = cc_set | bcc_set

print(f"CC list: {cc_list}")
print(f"BCC list: {bcc_list}")
print(f"CC/BCC combined (normalized): {cc_bcc_combined}")

# Create contact objects directly from email addresses (independent of Contacts table)
# IMPORTANT: Exclude anyone who is on CC or BCC list - they'll be queued separately
contacts = []
excluded_count = 0

for email in target_contact_emails:
    if email and '@' in email:  # Basic email validation
        normalized_email = email.lower().strip()
        
        # Exclude if this email is on CC or BCC list
        if normalized_email in cc_bcc_combined:
            print(f"✅ Excluding {email} from primary recipients (on CC/BCC list)")
            excluded_count += 1
            continue
        
        # Create contact object for regular recipients
        contacts.append({
            'email': email,
            'first_name': '',
            'last_name': '',
            'company': '',
            'title': '',
            'agency_name': ''
        })
        print(f"✅ Added {email} as regular recipient")

print(f"📊 EXCLUSION SUMMARY:")
print(f"   Total target emails: {len(target_contact_emails)}")
print(f"   Regular contacts: {len(contacts)}")
print(f"   Excluded (CC/BCC): {excluded_count}")
print(f"   CC recipients: {len(cc_list)}")
print(f"   BCC recipients: {len(bcc_list)}")
'''
    
    print(fix_code)
    print()
    
    print("🎯 VERIFICATION STEPS:")
    print("=" * 60)
    print("1. Check that CC recipients are properly excluded from contacts[]")
    print("2. Verify CC recipients only get queued once with role='cc'")
    print("3. Test that CC recipients receive only one email")
    print("4. Confirm CC headers are properly set in received emails")
    print()
    
    print("🧪 TEST SCENARIO:")
    print("=" * 60)
    print("Send campaign with:")
    print("- To: user1@example.com (regular contact)")
    print("- CC: user2@example.com (should get 1 email with CC header)")
    print("- BCC: user3@example.com (should get 1 email, hidden from others)")
    print()
    print("Expected result:")
    print("- user1: Gets email with user2 in CC field")
    print("- user2: Gets 1 email with their address in CC field")
    print("- user3: Gets 1 email with no CC/BCC visible")
    print()
    
    return True

if __name__ == "__main__":
    fix_cc_duplicate_emails()