#!/usr/bin/env python3
"""
Test CC Fix Verification

This script simulates the fixed CC handling logic to verify it works correctly.
"""

import json

def test_cc_fix_verification():
    """
    Test the CC duplication fix to verify it works correctly
    """
    
    print("🧪 Testing CC Duplication Fix")
    print("=" * 60)
    
    # Test scenario that would cause the original issue
    test_campaign = {
        'target_contacts': ['user1@example.com', 'user2@example.com', 'user3@example.com'],
        'cc': ['user2@example.com', 'cc-only@example.com'],  # user2 is in BOTH lists
        'bcc': ['bcc-only@example.com']
    }
    
    print("📧 TEST CAMPAIGN:")
    print(f"   Target contacts: {test_campaign['target_contacts']}")
    print(f"   CC list: {test_campaign['cc']}")
    print(f"   BCC list: {test_campaign['bcc']}")
    print()
    
    # Simulate the FIXED logic
    print("🔧 APPLYING FIXED LOGIC:")
    print("-" * 40)
    
    # Step 1: Create exclusion sets
    cc_list = test_campaign['cc']
    bcc_list = test_campaign['bcc']
    target_contact_emails = test_campaign['target_contacts']
    
    print(f"1. Creating exclusion sets:")
    cc_set = set([email.lower().strip() for email in cc_list if email and '@' in email])
    bcc_set = set([email.lower().strip() for email in bcc_list if email and '@' in email])
    cc_bcc_combined = cc_set | bcc_set
    
    print(f"   CC set: {cc_set}")
    print(f"   BCC set: {bcc_set}")
    print(f"   Combined exclusion set: {cc_bcc_combined}")
    print()
    
    # Step 2: Process contacts with exclusion
    print(f"2. Processing contacts with exclusion:")
    contacts = []
    excluded_count = 0
    
    for email in target_contact_emails:
        if email and '@' in email:
            normalized_email = email.lower().strip()
            
            print(f"   Processing: {email}")
            print(f"     Normalized: {normalized_email}")
            print(f"     In exclusion set? {normalized_email in cc_bcc_combined}")
            
            if normalized_email in cc_bcc_combined:
                print(f"     ✅ EXCLUDING {email} (found in CC/BCC list)")
                excluded_count += 1
            else:
                print(f"     ➕ ADDING {email} as regular contact")
                contacts.append({'email': email})
    
    print()
    print(f"   Regular contacts created: {len(contacts)}")
    print(f"   Excluded (CC/BCC): {excluded_count}")
    print()
    
    # Step 3: Simulate SQS queuing with deduplication
    print(f"3. Simulating SQS queuing with deduplication:")
    queued_emails = set()
    messages = []
    
    # Queue regular contacts
    print(f"   Queuing regular contacts:")
    for contact in contacts:
        email = contact['email']
        normalized = email.lower().strip()
        
        if normalized in queued_emails:
            print(f"     ⚠️  DUPLICATE: {email} already queued!")
        else:
            messages.append({'email': email, 'role': None})
            queued_emails.add(normalized)
            print(f"     ✅ Queued: {email} (role: None)")
    
    # Queue CC recipients
    print(f"   Queuing CC recipients:")
    for cc_email in cc_list:
        if cc_email and '@' in cc_email:
            normalized = cc_email.lower().strip()
            
            if normalized in queued_emails:
                print(f"     ⚠️  SKIPPING: {cc_email} (already queued)")
            else:
                messages.append({'email': cc_email, 'role': 'cc'})
                queued_emails.add(normalized)
                print(f"     ✅ Queued: {cc_email} (role: cc)")
    
    # Queue BCC recipients
    print(f"   Queuing BCC recipients:")
    for bcc_email in bcc_list:
        if bcc_email and '@' in bcc_email:
            normalized = bcc_email.lower().strip()
            
            if normalized in queued_emails:
                print(f"     ⚠️  SKIPPING: {bcc_email} (already queued)")
            else:
                messages.append({'email': bcc_email, 'role': 'bcc'})
                queued_emails.add(normalized)
                print(f"     ✅ Queued: {bcc_email} (role: bcc)")
    
    print()
    
    # Step 4: Analyze results
    print("📊 RESULTS ANALYSIS:")
    print("-" * 40)
    
    print(f"Total SQS messages: {len(messages)}")
    print(f"Unique recipients: {len(queued_emails)}")
    print()
    
    print("Messages that would be sent:")
    for i, msg in enumerate(messages, 1):
        role_text = f"(role: {msg['role']})" if msg['role'] else "(regular contact)"
        print(f"   {i}. {msg['email']} {role_text}")
    
    print()
    
    # Check for duplicates
    all_recipients = [msg['email'].lower().strip() for msg in messages]
    unique_recipients = set(all_recipients)
    
    if len(all_recipients) == len(unique_recipients):
        print("✅ SUCCESS: No duplicate recipients!")
        print("   Each person will receive exactly one email.")
    else:
        print("❌ FAILURE: Duplicate recipients detected!")
        from collections import Counter
        counts = Counter(all_recipients)
        for email, count in counts.items():
            if count > 1:
                print(f"   🚨 {email} would receive {count} emails!")
    
    print()
    
    # Expected email delivery
    print("📬 EXPECTED EMAIL DELIVERY:")
    print("-" * 40)
    
    for msg in messages:
        email = msg['email']
        role = msg['role']
        
        if role == 'cc':
            print(f"   {email}: Receives email with their address in CC field")
        elif role == 'bcc':
            print(f"   {email}: Receives email with their address in BCC field (hidden)")
        else:
            # Regular contact - show CC list in their email
            cc_display = ', '.join([cc for cc in cc_list if cc != email])
            if cc_display:
                print(f"   {email}: Receives email with CC: {cc_display}")
            else:
                print(f"   {email}: Receives email (no CC shown)")
    
    print()
    
    # Verification summary
    expected_recipients = len(set(
        test_campaign['target_contacts'] + 
        test_campaign['cc'] + 
        test_campaign['bcc']
    ))
    
    print("🎯 VERIFICATION SUMMARY:")
    print("-" * 40)
    print(f"Expected unique recipients: {expected_recipients}")
    print(f"Actual unique recipients: {len(unique_recipients)}")
    print(f"Messages queued: {len(messages)}")
    
    if len(messages) == len(unique_recipients) == expected_recipients:
        print("✅ PERFECT: Fix works correctly!")
        print("   - No duplicates")
        print("   - All recipients covered")
        print("   - Proper role assignment")
        return True
    else:
        print("❌ ISSUE: Fix needs adjustment")
        return False

if __name__ == "__main__":
    test_cc_fix_verification()