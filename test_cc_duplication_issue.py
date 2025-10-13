#!/usr/bin/env python3
"""
Test CC Duplication Issue

This script tests the current CC recipient handling to identify the duplication issue.
"""

import json

def test_cc_duplication_issue():
    """Test the CC duplication issue by simulating the campaign creation process"""
    
    print("🧪 Testing CC Duplication Issue")
    print("=" * 60)
    
    # Simulate campaign data that would cause the issue
    campaign_data = {
        'campaign_name': 'Test CC Duplication',
        'subject': 'Test Email',
        'body': '<p>This is a test email to check CC duplication.</p>',
        'target_contacts': ['user1@example.com', 'user2@example.com'],  # Regular contacts
        'cc': ['user2@example.com', 'cc-user@example.com'],  # CC list (user2 is in both!)
        'bcc': ['bcc-user@example.com']  # BCC list
    }
    
    print("📧 CAMPAIGN DATA:")
    print(f"   Target contacts: {campaign_data['target_contacts']}")
    print(f"   CC list: {campaign_data['cc']}")
    print(f"   BCC list: {campaign_data['bcc']}")
    print()
    
    # Simulate the current logic
    target_contact_emails = campaign_data['target_contacts']
    cc_list = campaign_data['cc']
    bcc_list = campaign_data['bcc']
    
    # Current exclusion logic (what should happen)
    cc_set = set([email.lower().strip() for email in cc_list if email])
    bcc_set = set([email.lower().strip() for email in bcc_list if email])
    cc_bcc_combined = cc_set | bcc_set
    
    print("🔍 EXCLUSION ANALYSIS:")
    print(f"   CC set (normalized): {cc_set}")
    print(f"   BCC set (normalized): {bcc_set}")
    print(f"   Combined CC/BCC: {cc_bcc_combined}")
    print()
    
    # Simulate contact creation with exclusion
    contacts = []
    excluded_count = 0
    
    print("👥 CONTACT PROCESSING:")
    for email in target_contact_emails:
        if email and '@' in email:
            normalized_email = email.lower().strip()
            
            if normalized_email in cc_bcc_combined:
                print(f"   ❌ EXCLUDING {email} (found in CC/BCC list)")
                excluded_count += 1
            else:
                print(f"   ✅ ADDING {email} as regular contact")
                contacts.append({'email': email})
    
    print()
    
    # Simulate SQS message creation
    print("📨 SQS MESSAGES THAT WOULD BE CREATED:")
    print("-" * 40)
    
    message_count = 0
    
    # Regular contact messages
    print("Regular contact messages:")
    for contact in contacts:
        message_count += 1
        print(f"   {message_count}. To: {contact['email']} (role: None)")
    
    # CC messages
    print("CC recipient messages:")
    for cc_email in cc_list:
        if cc_email and '@' in cc_email:
            message_count += 1
            print(f"   {message_count}. To: {cc_email} (role: 'cc')")
    
    # BCC messages
    print("BCC recipient messages:")
    for bcc_email in bcc_list:
        if bcc_email and '@' in bcc_email:
            message_count += 1
            print(f"   {message_count}. To: {bcc_email} (role: 'bcc')")
    
    print()
    print("📊 SUMMARY:")
    print(f"   Total SQS messages: {message_count}")
    print(f"   Regular contacts: {len(contacts)}")
    print(f"   Excluded from regular: {excluded_count}")
    print(f"   CC messages: {len([cc for cc in cc_list if cc and '@' in cc])}")
    print(f"   BCC messages: {len([bcc for bcc in bcc_list if bcc and '@' in bcc])}")
    print()
    
    # Identify the duplication issue
    print("🚨 DUPLICATION ANALYSIS:")
    print("-" * 40)
    
    all_recipients = {}
    
    # Count regular contact emails
    for contact in contacts:
        email = contact['email'].lower().strip()
        if email not in all_recipients:
            all_recipients[email] = []
        all_recipients[email].append('regular')
    
    # Count CC emails
    for cc_email in cc_list:
        if cc_email and '@' in cc_email:
            email = cc_email.lower().strip()
            if email not in all_recipients:
                all_recipients[email] = []
            all_recipients[email].append('cc')
    
    # Count BCC emails
    for bcc_email in bcc_list:
        if bcc_email and '@' in bcc_email:
            email = bcc_email.lower().strip()
            if email not in all_recipients:
                all_recipients[email] = []
            all_recipients[email].append('bcc')
    
    duplicates_found = False
    for email, roles in all_recipients.items():
        if len(roles) > 1:
            duplicates_found = True
            print(f"   🚨 DUPLICATE: {email} will receive {len(roles)} emails ({', '.join(roles)})")
        else:
            print(f"   ✅ OK: {email} will receive 1 email ({roles[0]})")
    
    print()
    
    if duplicates_found:
        print("❌ ISSUE CONFIRMED: Some recipients will receive duplicate emails!")
        print()
        print("💡 SOLUTION: The exclusion logic should prevent this.")
        print("   Check if the exclusion is working properly in the actual code.")
    else:
        print("✅ NO DUPLICATES: Exclusion logic is working correctly!")
    
    return not duplicates_found

if __name__ == "__main__":
    test_cc_duplication_issue()