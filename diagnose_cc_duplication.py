#!/usr/bin/env python3
"""
Diagnose CC Duplication Issue

This script helps diagnose why CC recipients are receiving duplicate emails
and provides a targeted fix.
"""

import json

def diagnose_cc_duplication():
    """
    Diagnose the CC duplication issue and provide targeted fixes
    """
    
    print("🔍 Diagnosing CC Duplication Issue")
    print("=" * 60)
    
    print("📋 PROBLEM STATEMENT:")
    print("User reported: 'each person on the cc line was sent an additional email'")
    print()
    
    print("🧪 DIAGNOSTIC SCENARIOS:")
    print("=" * 60)
    
    # Scenario 1: CC recipient is also in target contacts
    print("SCENARIO 1: CC recipient is also in target contacts")
    print("-" * 50)
    
    scenario1 = {
        'target_contacts': ['user1@example.com', 'user2@example.com'],
        'cc': ['user2@example.com'],  # user2 is in BOTH lists
        'bcc': []
    }
    
    print(f"Target contacts: {scenario1['target_contacts']}")
    print(f"CC list: {scenario1['cc']}")
    
    # Simulate current exclusion logic
    cc_set = set([email.lower().strip() for email in scenario1['cc'] if email])
    bcc_set = set()
    cc_bcc_combined = cc_set | bcc_set
    
    print(f"CC/BCC combined exclusion set: {cc_bcc_combined}")
    
    contacts_created = []
    excluded_count = 0
    
    for email in scenario1['target_contacts']:
        normalized_email = email.lower().strip()
        if normalized_email in cc_bcc_combined:
            print(f"   ✅ SHOULD EXCLUDE: {email} (found in CC list)")
            excluded_count += 1
        else:
            print(f"   ➕ WOULD ADD: {email} as regular contact")
            contacts_created.append(email)
    
    print(f"Result: {len(contacts_created)} regular contacts, {excluded_count} excluded")
    
    # Check if exclusion worked
    if 'user2@example.com' in contacts_created:
        print("❌ PROBLEM: user2@example.com was NOT excluded despite being in CC list!")
        print("   This would cause duplicate emails!")
    else:
        print("✅ GOOD: user2@example.com was properly excluded")
    
    print()
    
    # Scenario 2: Check SQS message creation
    print("SCENARIO 2: SQS Message Creation")
    print("-" * 50)
    
    print("Messages that would be created:")
    message_count = 0
    
    # Regular contacts
    for contact in contacts_created:
        message_count += 1
        print(f"   {message_count}. {contact} (role: None) - Regular contact")
    
    # CC recipients
    for cc_email in scenario1['cc']:
        message_count += 1
        print(f"   {message_count}. {cc_email} (role: 'cc') - CC recipient")
    
    print(f"Total messages: {message_count}")
    
    # Check for duplicates
    all_recipients = []
    for contact in contacts_created:
        all_recipients.append(contact.lower().strip())
    for cc_email in scenario1['cc']:
        all_recipients.append(cc_email.lower().strip())
    
    unique_recipients = set(all_recipients)
    if len(all_recipients) != len(unique_recipients):
        print("❌ DUPLICATE DETECTED: Some recipients will get multiple messages!")
        from collections import Counter
        counts = Counter(all_recipients)
        for email, count in counts.items():
            if count > 1:
                print(f"   🚨 {email} will receive {count} emails!")
    else:
        print("✅ NO DUPLICATES: Each recipient gets exactly one message")
    
    print()
    
    print("🔧 TARGETED FIXES:")
    print("=" * 60)
    
    print("1. ENHANCED EXCLUSION LOGGING:")
    print("   Add more detailed logging to see what's happening:")
    print()
    
    fix1 = '''
# In bulk_email_api_lambda.py, around line 6695-6705:

# Get CC and BCC lists to exclude from primary recipients
cc_list = body.get('cc', []) or []
bcc_list = body.get('bcc', []) or []

# DEBUG: Enhanced logging
print(f"🔍 EXCLUSION DEBUG:")
print(f"   Raw CC list: {cc_list}")
print(f"   Raw BCC list: {bcc_list}")

# Create normalized sets for comparison (lowercase, trimmed)
cc_set = set([email.lower().strip() for email in cc_list if email])
bcc_set = set([email.lower().strip() for email in bcc_list if email])
cc_bcc_combined = cc_set | bcc_set

print(f"   Normalized CC set: {cc_set}")
print(f"   Normalized BCC set: {bcc_set}")
print(f"   Combined exclusion set: {cc_bcc_combined}")
print(f"   Exclusion set size: {len(cc_bcc_combined)}")
'''
    
    print(fix1)
    
    print("2. ENHANCED CONTACT PROCESSING LOGGING:")
    print()
    
    fix2 = '''
# In the contact creation loop, around line 6716-6730:

contacts = []
excluded_count = 0
for email in target_contact_emails:
    if email and '@' in email:  # Basic email validation
        normalized_email = email.lower().strip()
        
        print(f"🔍 PROCESSING: {email}")
        print(f"   Normalized: {normalized_email}")
        print(f"   In exclusion set? {normalized_email in cc_bcc_combined}")
        
        # Exclude if this email is on CC or BCC list
        if normalized_email in cc_bcc_combined:
            print(f"   ✅ EXCLUDING {email} from primary recipients (on CC/BCC list)")
            excluded_count += 1
        else:
            print(f"   ➕ ADDING {email} as regular contact")
            contacts.append({
                'email': email,
                'first_name': '',
                'last_name': '',
                'company': '',
                'title': '',
                'agency_name': ''
            })

print(f"📊 CONTACT PROCESSING SUMMARY:")
print(f"   Total target emails: {len(target_contact_emails)}")
print(f"   Regular contacts created: {len(contacts)}")
print(f"   Excluded (CC/BCC): {excluded_count}")
'''
    
    print(fix2)
    
    print("3. ENHANCED SQS QUEUING LOGGING:")
    print()
    
    fix3 = '''
# In the SQS queuing section, add deduplication tracking:

queued_emails = set()  # Track all queued emails

# Queue regular contacts
for contact in contacts:
    email = contact.get('email')
    normalized = email.lower().strip()
    
    if normalized in queued_emails:
        print(f"⚠️  DUPLICATE DETECTED: {email} already queued!")
        continue
    
    # Queue the message
    message_body = {
        'campaign_id': campaign_id,
        'contact_email': email
    }
    
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
    queued_emails.add(normalized)
    print(f"✅ Queued regular contact: {email}")

# Queue CC recipients with deduplication
for cc_email in cc_list:
    if cc_email and '@' in cc_email:
        normalized = cc_email.lower().strip()
        
        if normalized in queued_emails:
            print(f"⚠️  SKIPPING CC {cc_email} - already queued as regular contact")
            continue
        
        message_body = {
            'campaign_id': campaign_id,
            'contact_email': cc_email,
            'role': 'cc'
        }
        
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        queued_emails.add(normalized)
        print(f"✅ Queued CC recipient: {cc_email}")

print(f"📊 FINAL SUMMARY: {len(queued_emails)} unique recipients queued")
'''
    
    print(fix3)
    
    print("🎯 IMMEDIATE ACTION ITEMS:")
    print("=" * 60)
    print("1. Add the enhanced logging to see what's happening")
    print("2. Test with a campaign that has CC recipients")
    print("3. Check CloudWatch logs for exclusion messages")
    print("4. Verify SQS messages don't contain duplicates")
    print("5. Monitor email delivery to confirm no duplicates")
    
    return True

if __name__ == "__main__":
    diagnose_cc_duplication()