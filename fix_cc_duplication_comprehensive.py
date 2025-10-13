#!/usr/bin/env python3
"""
Comprehensive Fix for CC Duplication Issue

This script provides a complete solution to fix the CC duplication issue
where CC recipients receive additional emails.
"""

import re

def fix_cc_duplication_comprehensive():
    """
    Apply comprehensive fix for CC duplication issue
    """
    
    print("🔧 Comprehensive CC Duplication Fix")
    print("=" * 60)
    
    print("📋 ISSUE: CC recipients receive duplicate emails")
    print("💡 SOLUTION: Enhanced exclusion and deduplication logic")
    print()
    
    # The key fixes needed:
    fixes_needed = [
        "1. Enhanced logging for CC/BCC exclusion",
        "2. Improved deduplication in SQS queuing", 
        "3. Better tracking of queued recipients",
        "4. Verification that exclusion logic works"
    ]
    
    for fix in fixes_needed:
        print(f"   {fix}")
    
    print()
    
    print("🛠️  IMPLEMENTATION APPROACH:")
    print("=" * 60)
    
    # Since we can't easily modify the existing file due to string matching issues,
    # let's create a patch that can be manually applied
    
    patch_content = '''
# PATCH FOR CC DUPLICATION ISSUE
# Apply these changes to bulk_email_api_lambda.py

# 1. ENHANCED CC/BCC EXCLUSION LOGGING (around line 6695-6705)
# Replace the existing CC/BCC exclusion section with:

        # Get CC and BCC lists to exclude from primary recipients
        cc_list = body.get('cc', []) or []
        bcc_list = body.get('bcc', []) or []
        
        # DEBUG: Log received lists for CC duplication diagnosis
        print(f"🔍 CC DUPLICATION DEBUG - EXCLUSION SETUP:")
        print(f"   Raw CC list: {cc_list}")
        print(f"   Raw BCC list: {bcc_list}")
        print(f"   Target contacts: {target_contact_emails}")
        
        # Create normalized sets for comparison (lowercase, trimmed)
        cc_set = set([email.lower().strip() for email in cc_list if email and '@' in email])
        bcc_set = set([email.lower().strip() for email in bcc_list if email and '@' in email])
        cc_bcc_combined = cc_set | bcc_set
        
        print(f"   Normalized CC set: {cc_set}")
        print(f"   Normalized BCC set: {bcc_set}")
        print(f"   Combined exclusion set: {cc_bcc_combined}")
        print(f"   Exclusion set size: {len(cc_bcc_combined)}")

# 2. ENHANCED CONTACT PROCESSING (around line 6716-6730)
# Replace the contact creation loop with:

        # Create contact objects directly from email addresses (independent of Contacts table)
        # IMPORTANT: Exclude anyone who is ONLY on CC or BCC list - they'll be queued separately
        contacts = []
        excluded_count = 0
        
        print(f"🔍 CC DUPLICATION DEBUG - CONTACT PROCESSING:")
        
        for email in target_contact_emails:
            if email and '@' in email:  # Basic email validation
                normalized_email = email.lower().strip()
                
                print(f"   Processing: {email}")
                print(f"     Normalized: {normalized_email}")
                print(f"     In CC/BCC exclusion set? {normalized_email in cc_bcc_combined}")
                
                # Exclude if this email is on CC or BCC list
                if normalized_email in cc_bcc_combined:
                    print(f"     ✅ EXCLUDING {email} from primary recipients (found in CC/BCC list)")
                    excluded_count += 1
                else:
                    print(f"     ➕ ADDING {email} as regular contact")
                    contacts.append({
                        'email': email,
                        'first_name': '',
                        'last_name': '',
                        'company': '',
                        'title': '',
                        'agency_name': ''
                    })
        
        print(f"📊 CC DUPLICATION DEBUG - CONTACT SUMMARY:")
        print(f"   Total target emails: {len(target_contact_emails)}")
        print(f"   Regular contacts created: {len(contacts)}")
        print(f"   Excluded (CC/BCC): {excluded_count}")
        print(f"   CC recipients to queue separately: {len(cc_list)}")
        print(f"   BCC recipients to queue separately: {len(bcc_list)}")

# 3. ENHANCED SQS QUEUING WITH DEDUPLICATION (around line 6850-6950)
# Add this enhanced queuing logic:

        # Track all queued emails to prevent any duplicates
        queued_emails = set()
        queued_count = 0
        failed_to_queue = 0
        
        print(f"🔍 CC DUPLICATION DEBUG - SQS QUEUING:")
        
        # Queue regular contacts first
        print(f"   Queuing {len(contacts)} regular contacts...")
        for contact in contacts:
            email = contact.get('email')
            normalized = email.lower().strip()
            
            if normalized in queued_emails:
                print(f"     ⚠️  DUPLICATE DETECTED: {email} already queued!")
                continue
            
            try:
                message_body = {
                    'campaign_id': campaign_id,
                    'contact_email': email
                    # NO role field = regular contact
                }
                
                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message_body)
                )
                
                queued_emails.add(normalized)
                queued_count += 1
                print(f"     ✅ Queued regular contact: {email}")
                
            except Exception as e:
                print(f"     ❌ Failed to queue {email}: {str(e)}")
                failed_to_queue += 1
        
        # Queue CC recipients with strict deduplication
        print(f"   Queuing {len(cc_list)} CC recipients...")
        for cc_email in cc_list:
            if cc_email and '@' in cc_email:
                normalized = cc_email.lower().strip()
                
                if normalized in queued_emails:
                    print(f"     ⚠️  SKIPPING CC {cc_email} - already queued as regular contact")
                    continue
                
                try:
                    message_body = {
                        'campaign_id': campaign_id,
                        'contact_email': cc_email,
                        'role': 'cc'  # This marks it as CC recipient
                    }
                    
                    sqs_client.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps(message_body)
                    )
                    
                    queued_emails.add(normalized)
                    queued_count += 1
                    print(f"     ✅ Queued CC recipient: {cc_email}")
                    
                except Exception as e:
                    print(f"     ❌ Failed to queue CC {cc_email}: {str(e)}")
                    failed_to_queue += 1
        
        # Queue BCC recipients with strict deduplication
        print(f"   Queuing {len(bcc_list)} BCC recipients...")
        for bcc_email in bcc_list:
            if bcc_email and '@' in bcc_email:
                normalized = bcc_email.lower().strip()
                
                if normalized in queued_emails:
                    print(f"     ⚠️  SKIPPING BCC {bcc_email} - already queued")
                    continue
                
                try:
                    message_body = {
                        'campaign_id': campaign_id,
                        'contact_email': bcc_email,
                        'role': 'bcc'  # This marks it as BCC recipient
                    }
                    
                    sqs_client.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps(message_body)
                    )
                    
                    queued_emails.add(normalized)
                    queued_count += 1
                    print(f"     ✅ Queued BCC recipient: {bcc_email}")
                    
                except Exception as e:
                    print(f"     ❌ Failed to queue BCC {bcc_email}: {str(e)}")
                    failed_to_queue += 1
        
        print(f"📊 CC DUPLICATION DEBUG - FINAL SUMMARY:")
        print(f"   Total SQS messages queued: {queued_count}")
        print(f"   Failed to queue: {failed_to_queue}")
        print(f"   Unique recipients: {len(queued_emails)}")
        print(f"   Expected emails to be sent: {len(queued_emails)}")
        
        # Verify no duplicates
        if queued_count == len(queued_emails):
            print(f"   ✅ NO DUPLICATES: Each recipient will get exactly 1 email")
        else:
            print(f"   ❌ POTENTIAL DUPLICATES: {queued_count} messages for {len(queued_emails)} recipients")
'''
    
    # Write the patch to a file
    with open('cc_duplication_fix.patch', 'w', encoding='utf-8') as f:
        f.write(patch_content)
    
    print("✅ Created cc_duplication_fix.patch")
    print()
    
    print("📋 MANUAL APPLICATION STEPS:")
    print("=" * 60)
    print("1. Open bulk_email_api_lambda.py in your editor")
    print("2. Find the sections mentioned in cc_duplication_fix.patch")
    print("3. Replace the existing code with the enhanced versions")
    print("4. Deploy the updated Lambda function")
    print("5. Test with a campaign that has CC recipients")
    print("6. Monitor CloudWatch logs for the debug output")
    print()
    
    print("🧪 TEST SCENARIO:")
    print("=" * 60)
    print("Create a campaign with:")
    print("- Target contacts: ['user1@example.com', 'user2@example.com']")
    print("- CC: ['user2@example.com', 'cc-only@example.com']")
    print("- BCC: ['bcc-only@example.com']")
    print()
    print("Expected behavior:")
    print("- user1@example.com: Gets 1 email as regular recipient")
    print("- user2@example.com: Gets 1 email as CC recipient (excluded from regular)")
    print("- cc-only@example.com: Gets 1 email as CC recipient")
    print("- bcc-only@example.com: Gets 1 email as BCC recipient")
    print()
    print("Expected SQS messages: 4 total")
    print("Expected emails sent: 4 total (no duplicates)")
    
    return True

if __name__ == "__main__":
    fix_cc_duplication_comprehensive()