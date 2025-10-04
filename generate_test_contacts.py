#!/usr/bin/env python3
"""
Generate 10,000 test contacts with same email address
For load testing the email campaign system
"""

import boto3
import uuid
from datetime import datetime
import time

REGION = 'us-gov-west-1'
TABLE_NAME = 'EmailContactsNew'  # Change to 'EmailContacts' if using new schema
TEST_EMAIL = 'test@example.com'
TOTAL_CONTACTS = 10000

def generate_test_contacts():
    """Generate 10,000 test contacts with same email and data"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("="*70)
    print(f"Generating {TOTAL_CONTACTS:,} Test Contacts")
    print("="*70)
    print(f"\nTable: {TABLE_NAME}")
    print(f"Test Email: {TEST_EMAIL}")
    print(f"Contact Data: John Doe, IT Director, CA, Test Agency")
    print()
    
    # Test contact template
    contact_template = {
        'email': TEST_EMAIL,
        'first_name': 'Test',
        'last_name': 'User',
        'title': 'IT Director',
        'entity_type': 'State Government',
        'state': 'CA',
        'agency_name': 'Test Agency',
        'sector': 'Government',
        'subsection': 'IT Services',
        'phone': '555-0100',
        'ms_isac_member': 'Yes',
        'soc_call': 'Yes',
        'fusion_center': 'No',
        'k12': 'No',
        'water_wastewater': 'No',
        'weekly_rollup': 'Yes',
        'alternate_email': 'test.alt@example.com',
        'region': 'West',
        'created_at': datetime.now().isoformat()
    }
    
    print("🚀 Starting batch import...")
    print(f"⏱️  Estimated time: ~{TOTAL_CONTACTS / 25 * 0.5 / 60:.1f} minutes")
    print()
    
    total_imported = 0
    total_errors = 0
    batch_num = 0
    BATCH_SIZE = 25  # DynamoDB batch_write_item limit
    
    start_time = time.time()
    
    # Process in batches
    with table.batch_writer() as batch:
        for i in range(TOTAL_CONTACTS):
            # Create contact with unique contact_id
            contact = contact_template.copy()
            contact['contact_id'] = str(uuid.uuid4())  # Auto-generated UUID
            
            try:
                batch.put_item(Item=contact)
                total_imported += 1
                
                # Progress indicator
                if (i + 1) % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    remaining = (TOTAL_CONTACTS - (i + 1)) / rate
                    
                    print(f"  Progress: {i+1:,}/{TOTAL_CONTACTS:,} ({(i+1)/TOTAL_CONTACTS*100:.1f}%) "
                          f"- {rate:.1f} contacts/sec - ETA: {remaining:.0f}s")
                
            except Exception as e:
                total_errors += 1
                if total_errors <= 5:  # Show first 5 errors
                    print(f"  Error importing contact {i+1}: {str(e)}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print()
    print("="*70)
    print("✅ IMPORT COMPLETE")
    print("="*70)
    print(f"Total Contacts Created: {total_imported:,}")
    print(f"Errors: {total_errors}")
    print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"Rate: {total_imported/duration:.1f} contacts/second")
    print()
    print(f"All {total_imported:,} contacts have:")
    print(f"  • Unique contact_id (UUID)")
    print(f"  • Same email: {TEST_EMAIL}")
    print(f"  • Same contact data (Name: Test User)")
    print()
    print("🧪 Ready for load testing!")
    print()
    print("Verify with:")
    print(f"  aws dynamodb scan --table-name {TABLE_NAME} \\")
    print(f"    --select COUNT --region {REGION}")
    
    return total_imported

if __name__ == '__main__':
    import sys
    
    print()
    print("Test Contact Generator")
    print("=" * 50)
    print("1. Run CLI version (current terminal)")
    print("2. Launch GUI version (recommended)")
    print()
    
    choice = input("Select option (1 or 2, or 'gui' to launch GUI): ").strip().lower()
    
    if choice in ['2', 'gui']:
        print("\n🚀 Launching GUI application...")
        try:
            import subprocess
            subprocess.run([sys.executable, 'generate_test_contacts_gui.py'])
        except Exception as e:
            print(f"Error launching GUI: {e}")
            print("\nFalling back to CLI version...")
            response = input(f"\n⚠️  This will create {TOTAL_CONTACTS:,} test contacts in '{TABLE_NAME}'. Continue? (yes/no): ")
            if response.lower() == 'yes':
                generate_test_contacts()
            else:
                print("Cancelled.")
    elif choice == '1':
        print()
        response = input(f"⚠️  This will create {TOTAL_CONTACTS:,} test contacts in '{TABLE_NAME}'. Continue? (yes/no): ")
        if response.lower() == 'yes':
            generate_test_contacts()
        else:
            print("Cancelled.")
    else:
        print("Invalid choice. Exiting.")

