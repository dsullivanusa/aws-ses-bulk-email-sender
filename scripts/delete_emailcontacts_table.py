#!/usr/bin/env python3
"""
Delete EmailContacts DynamoDB Table
⚠️  WARNING: This will permanently delete the table and ALL data!
"""

import boto3
from botocore.exceptions import ClientError
import sys

REGION = 'us-gov-west-1'
TABLE_NAME = 'EmailContacts'

def delete_emailcontacts_table():
    """Delete EmailContacts table"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=REGION)
    
    print("\n" + "="*70)
    print("⚠️  DELETE EMAILCONTACTS TABLE")
    print("="*70)
    print()
    
    # Check if table exists
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.load()
        
        # Get table details
        item_count = table.item_count
        table_size = table.table_size_bytes
        
        print(f"Table Found: {TABLE_NAME}")
        print(f"  Region: {REGION}")
        print(f"  Item Count: {item_count:,}")
        print(f"  Size: {table_size:,} bytes")
        print()
        
        # First confirmation
        print("⚠️  WARNING: This action will:")
        print("  • Permanently delete the table")
        print(f"  • Delete all {item_count:,} records")
        print("  • Cannot be undone")
        print("  • All contact data will be lost")
        print()
        
        response1 = input("Do you want to continue? Type 'yes' to proceed: ").strip()
        
        if response1.lower() != 'yes':
            print("\n❌ Deletion cancelled.")
            return False
        
        # Second confirmation
        print()
        print("⚠️  FINAL CONFIRMATION")
        print(f"Type the table name '{TABLE_NAME}' to confirm deletion:")
        response2 = input("> ").strip()
        
        if response2 != TABLE_NAME:
            print("\n❌ Table name doesn't match. Deletion cancelled.")
            return False
        
        # Delete table
        print()
        print(f"🗑️  Deleting table '{TABLE_NAME}'...")
        
        dynamodb_client.delete_table(TableName=TABLE_NAME)
        
        print(f"⏳ Waiting for table to be deleted...")
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(TableName=TABLE_NAME)
        
        print()
        print("="*70)
        print("✅ TABLE DELETED SUCCESSFULLY")
        print("="*70)
        print(f"\nDeleted: {TABLE_NAME}")
        print(f"Records Lost: {item_count:,}")
        print()
        print("Next steps:")
        print("  1. Create new table: python create_new_contacts_table.py")
        print("  2. Import contacts or generate test data")
        print("="*70)
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"✓ Table '{TABLE_NAME}' does not exist.")
            print(f"  Nothing to delete.")
            return False
        else:
            print(f"❌ Error: {str(e)}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    
    # Check for command-line confirmation flag
    if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
        print("Running with --confirm flag (skipping interactive prompts)")
        print("Deleting table in 5 seconds... Press Ctrl+C to cancel")
        import time
        for i in range(5, 0, -1):
            print(f"  {i}...")
            time.sleep(1)
    
    result = delete_emailcontacts_table()
    
    if result:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure or cancelled

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Deletion cancelled by user (Ctrl+C)")
        sys.exit(1)

