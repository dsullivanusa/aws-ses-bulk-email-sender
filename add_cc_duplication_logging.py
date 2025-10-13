#!/usr/bin/env python3
"""
Add CC Duplication Logging

This script adds enhanced logging to the bulk_email_api_lambda.py to help
identify where CC recipients are getting duplicated.
"""

def add_cc_duplication_logging():
    """
    Add enhanced logging to identify CC duplication issues
    """
    
    print("🔧 Adding CC Duplication Logging")
    print("=" * 60)
    
    print("This will add enhanced logging to help identify the CC duplication issue.")
    print()
    
    # Read the current file
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ bulk_email_api_lambda.py not found in current directory")
        return False
    
    # Check if logging is already added
    if "🔍 EXCLUSION DEBUG:" in content:
        print("✅ Enhanced logging already present in the file")
        return True
    
    # Find the CC/BCC exclusion section and add logging
    original_section = '''        # Get CC and BCC lists to exclude from primary recipients
        cc_list = body.get('cc', []) or []
        bcc_list = body.get('bcc', []) or []
        
        # Create normalized sets for comparison (lowercase, trimmed)
        cc_set = set([email.lower().strip() for email in cc_list if email])
        bcc_set = set([email.lower().strip() for email in bcc_list if email])
        cc_bcc_combined = cc_set | bcc_set'''
    
    enhanced_section = '''        # Get CC and BCC lists to exclude from primary recipients
        cc_list = body.get('cc', []) or []
        bcc_list = body.get('bcc', []) or []
        
        # DEBUG: Enhanced logging for CC duplication diagnosis
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
        print(f"   Exclusion set size: {len(cc_bcc_combined)}")'''
    
    if original_section in content:
        content = content.replace(original_section, enhanced_section)
        print("✅ Added enhanced exclusion logging")
    else:
        print("⚠️  Could not find exact exclusion section to enhance")
    
    # Find the contact processing section and add logging
    original_processing = '''                # Exclude if this email is on CC or BCC list
                if normalized_email in cc_bcc_combined:
                    print(f"Excluding {email} from primary recipients (on CC/BCC list)")
                    excluded_count += 1'''
    
    enhanced_processing = '''                # Exclude if this email is on CC or BCC list
                print(f"🔍 PROCESSING: {email}")
                print(f"   Normalized: {normalized_email}")
                print(f"   In exclusion set? {normalized_email in cc_bcc_combined}")
                
                if normalized_email in cc_bcc_combined:
                    print(f"   ✅ EXCLUDING {email} from primary recipients (on CC/BCC list)")
                    excluded_count += 1'''
    
    if original_processing in content:
        content = content.replace(original_processing, enhanced_processing)
        print("✅ Added enhanced contact processing logging")
    else:
        print("⚠️  Could not find exact contact processing section to enhance")
    
    # Add summary logging after contact creation
    summary_addition = '''        
        print(f"📊 CONTACT PROCESSING SUMMARY:")
        print(f"   Total target emails: {len(target_contact_emails)}")
        print(f"   Regular contacts created: {len(contacts)}")
        print(f"   Excluded (CC/BCC): {excluded_count}")
        print(f"   CC list size: {len(cc_list)}")
        print(f"   BCC list size: {len(bcc_list)}")'''
    
    # Find where to insert the summary
    if "excluded_count += 1" in content and "print(f\"📊 CONTACT PROCESSING SUMMARY:" not in content:
        # Find the end of the contact creation loop
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "excluded_count += 1" in line:
                # Find the end of the for loop
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith('        ') and not lines[j].startswith('\t'):
                        # Insert summary before this line
                        lines.insert(j, summary_addition)
                        content = '\n'.join(lines)
                        print("✅ Added contact processing summary")
                        break
                break
    
    # Write the enhanced file
    try:
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Enhanced logging added to bulk_email_api_lambda.py")
    except Exception as e:
        print(f"❌ Error writing file: {str(e)}")
        return False
    
    print()
    print("🎯 NEXT STEPS:")
    print("1. Deploy the updated Lambda function")
    print("2. Send a test campaign with CC recipients")
    print("3. Check CloudWatch logs for the enhanced logging")
    print("4. Look for any unexpected behavior in the logs")
    
    return True

if __name__ == "__main__":
    add_cc_duplication_logging()