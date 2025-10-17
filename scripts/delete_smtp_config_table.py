#!/usr/bin/env python3
"""
Delete SMTPConfig DynamoDB Table
⚠️  WARNING: This will permanently delete the table and ALL data!
"""

import boto3
from botocore.exceptions import ClientError
import sys

REGION = 'us-gov-west-1'
TABLE_NAME = 'SMTPConfig'

def delete_smtp_config_table():
    """Delete SMTPConfig table"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=REGION)
    
    print("\n" + "="*70)
    print("⚠️  DELETE SMTPCONFIG TABLE")
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
        
        # Warning
        print("⚠️  WARNING: This action will:")
        print("  • Permanently delete the SMTPConfig table")
        print(f"  • Delete all {item_count:,} records")
        print("  • Cannot be undone")
        print("  • SMTP configuration data will be lost")
        print()
        print("Note: This table is no longer needed if you're using EmailConfig")
        print()
        
        # Confirmation
        response = input("Do you want to delete this table? Type 'DELETE' to confirm: ").strip()
        
        if response != 'DELETE':
            print("\n❌ Deletion cancelled.")
            return False
        
        # Delete table
        print()
        print(f"🗑️  Deleting table '{TABLE_NAME}'...")
        
        try:
            dynamodb_client.delete_table(TableName=TABLE_NAME)
            
            print(f"⏳ Waiting for table to be fully deleted...")
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
            print("  1. Update Lambda references to SMTPConfig (if any)")
            print("  2. Use EmailConfig table for all email configuration")
            print("  3. Update DynamoDB Manager GUI project tables list")
            print("="*70)
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting table: {str(e)}")
            return False
        
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
    try:
        result = delete_smtp_config_table()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Deletion cancelled by user (Ctrl+C)")
        sys.exit(1)

if __name__ == '__main__':
    main()


