#!/usr/bin/env python3
"""
Fix CC Duplicate Issue - Comprehensive Solution

Based on the user report that "each person on the cc line was sent an additional email",
this script provides the fix for the CC duplication issue.
"""

def analyze_and_fix_cc_issue():
    """
    Analyze and provide fix for CC duplicate email issue
    """
    
    print("🔧 CC Duplicate Email Issue - Comprehensive Fix")
    print("=" * 60)
    
    print("📋 PROBLEM DESCRIPTION:")
    print("Each person on the CC line receives an additional email")
    print("This means they get:")
    print("1. Regular email (if they're in contacts database)")
    print("2. CC-specific email (with role='cc')")
    print()
    
    print("🔍 ROOT CAUSE ANALYSIS:")
    print("The issue could be in one of these areas:")
    print("1. CC exclusion logic not working properly")
    print("2. Deduplication in enqueue_special not working")
    print("3. CC recipients being processed as both regular and CC")
    print()
    
    print("🛠️  COMPREHENSIVE FIX:")
    print("=" * 60)
    
    # Show the fix for the API lambda
    api_fix = '''
# In bulk_email_api_lambda.py, in the send_campaign function:

# 1. ENSURE CC/BCC EXCLUSION HAPPENS EARLY
def send_campaign(body, headers, event=None):
    """Send email campaign by saving to DynamoDB and queuing contacts to SQS"""
    try:
        # ... existing code ...
        
        # Get target contact emails from request
        target_contact_emails = body.get('target_contacts', [])
        
        # Get CC and BCC lists FIRST (before any processing)
        cc_list = body.get('cc', []) or []
        bcc_list = body.get('bcc', []) or []
        to_list = body.get('to', []) or []
        
        # DEBUG: Log what we received
        print(f"📧 RECEIVED LISTS:")
        print(f"   Target contacts: {target_contact_emails}")
        print(f"   CC list: {cc_list}")
        print(f"   BCC list: {bcc_list}")
        print(f"   To list: {to_list}")
        
        # Create normalized sets for exclusion (case-insensitive, trimmed)
        cc_set = set()
        bcc_set = set()
        to_set = set()
        
        for email in cc_list:
            if email and '@' in email:
                cc_set.add(email.lower().strip())
        
        for email in bcc_list:
            if email and '@' in email:
                bcc_set.add(email.lower().strip())
                
        for email in to_list:
            if email and '@' in email:
                to_set.add(email.lower().strip())
        
        # Combine all special recipients (CC + BCC + To)
        special_recipients = cc_set | bcc_set | to_set
        
        print(f"🚫 EXCLUSION SETS:")
        print(f"   CC set: {cc_set}")
        print(f"   BCC set: {bcc_set}")
        print(f"   To set: {to_set}")
        print(f"   Combined special recipients: {special_recipients}")
        
        # Create contact objects - EXCLUDE anyone on CC/BCC/To lists
        contacts = []
        excluded_count = 0
        
        for email in target_contact_emails:
            if email and '@' in email:
                normalized_email = email.lower().strip()
                
                # CRITICAL: Exclude if this email is on ANY special list
                if normalized_email in special_recipients:
                    print(f"✅ EXCLUDING {email} from regular contacts (on CC/BCC/To list)")
                    excluded_count += 1
                    continue
                
                # Add as regular contact
                contacts.append({
                    'email': email,
                    'first_name': '',
                    'last_name': '',
                    'company': '',
                    'title': '',
                    'agency_name': ''
                })
                print(f"✅ ADDED {email} as regular contact")
        
        print(f"📊 CONTACT PROCESSING SUMMARY:")
        print(f"   Total target emails: {len(target_contact_emails)}")
        print(f"   Regular contacts created: {len(contacts)}")
        print(f"   Excluded (special recipients): {excluded_count}")
        
        # ... rest of existing campaign creation code ...
        
        # Queue regular contacts (these should NOT include CC/BCC recipients)
        queued_count = 0
        failed_to_queue = 0
        
        for contact in contacts:
            try:
                message_body = {
                    'campaign_id': campaign_id,
                    'contact_email': contact.get('email')
                    # NO role field = regular contact
                }
                
                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message_body)
                )
                queued_count += 1
                print(f"✅ Queued regular contact: {contact.get('email')}")
                
            except Exception as e:
                print(f"❌ Failed to queue {contact.get('email')}: {str(e)}")
                failed_to_queue += 1
        
        # Track all queued emails for deduplication
        queued_emails = set([c.get('email').lower().strip() for c in contacts])
        
        # Helper function for special recipients with deduplication
        def enqueue_special_recipient(recipient_email, role):
            nonlocal queued_count, failed_to_queue
            
            if not recipient_email or '@' not in recipient_email:
                print(f"❌ Skipping invalid {role} email: {recipient_email}")
                return
            
            normalized_email = recipient_email.lower().strip()
            
            # Check for duplicates
            if normalized_email in queued_emails:
                print(f"⚠️  SKIPPING {role.upper()} {recipient_email} - already queued")
                return
            
            try:
                message_body = {
                    'campaign_id': campaign_id,
                    'contact_email': recipient_email,
                    'role': role  # This is the key - marks special handling
                }
                
                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(message_body)
                )
                
                # Track this email as queued
                queued_emails.add(normalized_email)
                queued_count += 1
                print(f"✅ Queued {role.upper()} recipient: {recipient_email}")
                
            except Exception as e:
                print(f"❌ Failed to queue {role} {recipient_email}: {str(e)}")
                failed_to_queue += 1
        
        # Queue To recipients (explicit To list)
        for to_email in to_list:
            enqueue_special_recipient(to_email, 'to')
        
        # Queue CC recipients
        for cc_email in cc_list:
            enqueue_special_recipient(cc_email, 'cc')
        
        # Queue BCC recipients
        for bcc_email in bcc_list:
            enqueue_special_recipient(bcc_email, 'bcc')
        
        print(f"📊 FINAL QUEUING SUMMARY:")
        print(f"   Total messages queued: {queued_count}")
        print(f"   Failed to queue: {failed_to_queue}")
        print(f"   Unique recipients: {len(queued_emails)}")
        
        # ... rest of function ...
'''
    
    print("1. API LAMBDA FIX (bulk_email_api_lambda.py):")
    print(api_fix)
    print()
    
    # Show the worker lambda verification
    worker_verification = '''
# In email_worker_lambda.py, verify the role handling:

def lambda_handler(event, context):
    # ... existing code ...
    
    for idx, record in enumerate(event['Records'], 1):
        try:
            message = json.loads(record['body'])
            campaign_id = message.get('campaign_id')
            contact_email = message.get('contact_email')
            role = message.get('role')  # None, 'cc', 'bcc', or 'to'
            
            print(f"[Message {idx}] Processing: {contact_email}, Role: {role}")
            
            # Get campaign data
            campaign = get_campaign_from_dynamodb(campaign_id)
            
            # Get CC/BCC lists from campaign
            campaign_cc_list = campaign.get('cc', []) or []
            campaign_bcc_list = campaign.get('bcc', []) or []
            
            # Handle role-based email sending
            if role == 'cc':
                # CC recipient: they should appear in CC field
                print(f"[Message {idx}] CC RECIPIENT: {contact_email}")
                cc_list = [contact_email]  # Put this recipient in CC
                bcc_list = []
                # Use sender as To address (SES requirement)
                to_address = from_email
                
            elif role == 'bcc':
                # BCC recipient: they should appear in BCC field
                print(f"[Message {idx}] BCC RECIPIENT: {contact_email}")
                cc_list = []
                bcc_list = [contact_email]  # Put this recipient in BCC
                # Use sender as To address (SES requirement)
                to_address = from_email
                
            elif role == 'to':
                # Explicit To recipient
                print(f"[Message {idx}] TO RECIPIENT: {contact_email}")
                cc_list = campaign_cc_list  # Include campaign CC list
                bcc_list = campaign_bcc_list  # Include campaign BCC list
                to_address = contact_email
                
            else:
                # Regular contact from database
                print(f"[Message {idx}] REGULAR CONTACT: {contact_email}")
                cc_list = campaign_cc_list  # Include campaign CC list
                bcc_list = campaign_bcc_list  # Include campaign BCC list
                to_address = contact_email
            
            # Send email with proper headers
            send_ses_email(
                campaign=campaign,
                contact={'email': to_address},
                from_email=from_email,
                subject=personalized_subject,
                body=personalized_body,
                msg_idx=idx,
                cc_list=cc_list,
                bcc_list=bcc_list
            )
            
        except Exception as e:
            print(f"[Message {idx}] ERROR: {str(e)}")
'''
    
    print("2. WORKER LAMBDA VERIFICATION (email_worker_lambda.py):")
    print(worker_verification)
    print()
    
    print("🧪 TESTING STEPS:")
    print("=" * 60)
    print("1. Create test campaign with:")
    print("   - Target contacts: ['user1@example.com']")
    print("   - CC: ['user2@example.com']")
    print("   - BCC: ['user3@example.com']")
    print()
    print("2. Expected SQS messages:")
    print("   - Message 1: user1@example.com (role: None)")
    print("   - Message 2: user2@example.com (role: 'cc')")
    print("   - Message 3: user3@example.com (role: 'bcc')")
    print()
    print("3. Expected emails received:")
    print("   - user1: 1 email with user2 in CC field")
    print("   - user2: 1 email with their address in CC field")
    print("   - user3: 1 email with no visible CC/BCC")
    print()
    
    print("✅ IMPLEMENTATION PRIORITY:")
    print("1. Fix the exclusion logic in API lambda")
    print("2. Verify deduplication in enqueue_special")
    print("3. Test with real campaign")
    print("4. Monitor CloudWatch logs for duplicate detection")
    
    return True

if __name__ == "__main__":
    analyze_and_fix_cc_issue()