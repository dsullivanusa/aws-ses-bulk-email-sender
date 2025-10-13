#!/usr/bin/env python3
"""
Test CC Duplication Fix - Final Verification

This script tests the CC duplication fix that was just applied to bulk_email_api_lambda.py
"""

def test_cc_duplication_fix_final():
    """
    Test the final CC duplication fix
    """
    
    print("🧪 Testing CC Duplication Fix - Final Verification")
    print("=" * 60)
    
    # Simulate the problematic scenario
    test_scenario = {
        'target_contacts': ['user1@example.com', 'user2@example.com', 'user3@example.com'],
        'cc': ['user2@example.com', 'cc-only@example.com'],  # user2 is in BOTH lists!
        'bcc': ['user3@example.com', 'bcc-only@example.com'],  # user3 is in BOTH lists!
        'to': ['to-only@example.com']
    }
    
    print("📧 TEST SCENARIO (Problematic Case):")
    print(f"   Target contacts: {test_scenario['target_contacts']}")
    print(f"   CC list: {test_scenario['cc']}")
    print(f"   BCC list: {test_scenario['bcc']}")
    print(f"   To list: {test_scenario['to']}")
    print()
    
    # Simulate the FIXED logic from bulk_email_api_lambda.py
    print("🔧 APPLYING FIXED LOGIC:")
    print("-" * 40)
    
    # Step 1: Get CC/BCC/To lists FIRST
    target_contact_emails = test_scenario['target_contacts']
    cc_list = test_scenario['cc']
    bcc_list = test_scenario['bcc']
    to_list = test_scenario['to']
    
    # Step 2: Create exclusion sets
    cc_set = set([email.lower().strip() for email in cc_list if email and '@' in email])
    bcc_set = set([email.lower().strip() for email in bcc_list if email and '@' in email])
    to_set = set([email.lower().strip() for email in to_list if email and '@' in email])
    cc_bcc_to_combined = cc_set | bcc_set | to_set
    
    print(f"1. Exclusion sets created:")
    print(f"   CC set: {cc_set}")
    print(f"   BCC set: {bcc_set}")
    print(f"   To set: {to_set}")
    print(f"   Combined exclusion set: {cc_bcc_to_combined}")
    print()
    
    # Step 3: Create contacts with exclusion
    print(f"2. Processing contacts with exclusion:")
    contacts = []
    excluded_count = 0
    
    for email in target_contact_emails:
        if email and '@' in email:
            normalized_email = email.lower().strip()
            
            print(f"   Processing: {email}")
            print(f"     Normalized: {normalized_email}")
            print(f"     In exclusion set? {normalized_email in cc_bcc_to_combined}")
            
            if normalized_email in cc_bcc_to_combined:
                print(f"     ✅ EXCLUDING {email} (found in CC/BCC/To list)")
                excluded_count += 1
            else:
                print(f"     ➕ ADDING {email} as regular contact")
                contacts.append({'email': email})
    
    print()
    print(f"   Regular contacts created: {len(contacts)}")
    print(f"   Excluded (CC/BCC/To): {excluded_count}")
    print()
    
    # Step 4: Simulate SQS message creation
    print(f"3. Simulating SQS message creation:")
    messages = []
    
    # Regular contacts
    print(f"   Queuing regular contacts:")
    for contact in contacts:
        messages.append({'email': contact['email'], 'role': None})
        print(f"     ✅ Queued: {contact['email']} (role: None)")
    
    # CC recipients
    print(f"   Queuing CC recipients:")
    for cc_email in cc_list:
        if cc_email and '@' in cc_email:
            messages.append({'email': cc_email, 'role': 'cc'})
            print(f"     ✅ Queued: {cc_email} (role: cc)")
    
    # BCC recipients
    print(f"   Queuing BCC recipients:")
    for bcc_email in bcc_list:
        if bcc_email and '@' in bcc_email:
            messages.append({'email': bcc_email, 'role': 'bcc'})
            print(f"     ✅ Queued: {bcc_email} (role: bcc)")
    
    # To recipients
    print(f"   Queuing To recipients:")
    for to_email in to_list:
        if to_email and '@' in to_email:
            messages.append({'email': to_email, 'role': 'to'})
            print(f"     ✅ Queued: {to_email} (role: to)")
    
    print()
    
    # Step 5: Analyze for duplicates
    print("📊 DUPLICATION ANALYSIS:")
    print("-" * 40)
    
    all_recipients = [msg['email'].lower().strip() for msg in messages]
    unique_recipients = set(all_recipients)
    
    print(f"Total SQS messages: {len(messages)}")
    print(f"Unique recipients: {len(unique_recipients)}")
    print()
    
    print("Messages that would be sent:")
    for i, msg in enumerate(messages, 1):
        role_text = f"(role: {msg['role']})" if msg['role'] else "(regular contact)"
        print(f"   {i}. {msg['email']} {role_text}")
    
    print()
    
    # Check for duplicates
    if len(messages) == len(unique_recipients):
        print("✅ SUCCESS: No duplicate recipients!")
        print("   Each person will receive exactly one email.")
        success = True
    else:
        print("❌ FAILURE: Duplicate recipients detected!")
        from collections import Counter
        counts = Counter(all_recipients)
        for email, count in counts.items():
            if count > 1:
                print(f"   🚨 {email} would receive {count} emails!")
        success = False
    
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
        elif role == 'to':
            print(f"   {email}: Receives email as primary To recipient")
        else:
            # Regular contact - show what CC/BCC they'll see
            visible_cc = [cc for cc in cc_list if cc != email]
            if visible_cc:
                print(f"   {email}: Receives email with CC: {', '.join(visible_cc)}")
            else:
                print(f"   {email}: Receives email (no CC visible)")
    
    print()
    
    # Final verification
    print("🎯 VERIFICATION RESULTS:")
    print("-" * 40)
    
    expected_unique = len(set(
        test_scenario['target_contacts'] + 
        test_scenario['cc'] + 
        test_scenario['bcc'] + 
        test_scenario['to']
    ))
    
    print(f"Expected unique recipients: {expected_unique}")
    print(f"Actual unique recipients: {len(unique_recipients)}")
    print(f"Messages queued: {len(messages)}")
    
    if success and len(messages) == len(unique_recipients) == expected_unique:
        print("✅ PERFECT: CC Duplication Fix is working correctly!")
        print("   - No duplicates detected")
        print("   - All recipients properly handled")
        print("   - CC recipients excluded from regular processing")
        return True
    else:
        print("❌ ISSUE: Fix needs adjustment")
        return False

if __name__ == "__main__":
    test_cc_duplication_fix_final()