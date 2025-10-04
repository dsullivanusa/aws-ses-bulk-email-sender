#!/usr/bin/env python3
"""
Migrate EmailContacts Table to New Schema
⚠️  Deletes old table and creates new one with auto-generated contact_id
"""

import boto3
from botocore.exceptions import ClientError
import json
import time
import sys

REGION = 'us-gov-west-1'
TABLE_NAME = 'EmailContacts'

def export_table_backup(dynamodb_client, table_name):
    """Export table data to JSON file for backup"""
    try:
        print(f"\n💾 Creating backup of existing data...")
        
        # Scan table
        items = []
        response = dynamodb_client.scan(TableName=table_name)
        items.extend(response.get('Items', []))
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = dynamodb_client.scan(
                TableName=table_name,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
        
        # Save to file
        backup_filename = f'{table_name}_backup_{int(time.time())}.json'
        with open(backup_filename, 'w') as f:
            json.dump(items, f, indent=2, default=str)
        
        print(f"✅ Backup saved: {backup_filename}")
        print(f"   Records backed up: {len(items):,}")
        return backup_filename
    except Exception as e:
        print(f"⚠️  Could not create backup: {str(e)}")
        return None

def migrate_emailcontacts_table():
    """Delete old table and create new one with new schema"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=REGION)
    
    print("\n" + "="*80)
    print("📊 MIGRATE EMAILCONTACTS TABLE TO NEW SCHEMA")
    print("="*80)
    print()
    print("This will:")
    print("  1. Check if EmailContacts table exists")
    print("  2. Create backup of existing data (if table exists)")
    print("  3. Delete old EmailContacts table")
    print("  4. Create new EmailContacts table with new schema:")
    print("     - Primary Key: contact_id (auto-generated UUID)")
    print("     - No 'group' column")
    print("     - Allows duplicate email addresses")
    print("="*80)
    print()
    
    # Step 1: Check if table exists
    old_table_exists = False
    item_count = 0
    
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.load()
        old_table_exists = True
        item_count = table.item_count
        table_size = table.table_size_bytes
        
        print(f"📋 Current Table Status:")
        print(f"   Name: {TABLE_NAME}")
        print(f"   Records: {item_count:,}")
        print(f"   Size: {table_size:,} bytes")
        print()
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"✓ Table '{TABLE_NAME}' does not exist (will create new)")
            print()
        else:
            print(f"❌ Error checking table: {str(e)}")
            return False
    
    # Step 2: Get confirmation if table exists
    if old_table_exists:
        print("⚠️  WARNING: DESTRUCTIVE OPERATION")
        print("="*80)
        print(f"  • Current table has {item_count:,} records")
        print(f"  • ALL DATA WILL BE PERMANENTLY DELETED")
        print(f"  • This action CANNOT BE UNDONE")
        print(f"  • New table will have different schema")
        print("="*80)
        print()
        
        # Offer backup
        create_backup = input("Create backup before deletion? (yes/no): ").strip().lower()
        if create_backup == 'yes':
            backup_file = export_table_backup(dynamodb_client, TABLE_NAME)
            if backup_file:
                print(f"✅ Backup created successfully")
            else:
                print(f"⚠️  Backup failed, but continuing...")
        
        print()
        
        # First confirmation
        response1 = input(f"Type 'DELETE' to confirm deletion of {item_count:,} records: ").strip()
        if response1 != 'DELETE':
            print("\n❌ Migration cancelled.")
            return False
        
        # Second confirmation
        print()
        response2 = input(f"Type the table name '{TABLE_NAME}' to confirm: ").strip()
        if response2 != TABLE_NAME:
            print("\n❌ Migration cancelled.")
            return False
        
        # Step 3: Delete old table
        print()
        print(f"🗑️  Deleting old table '{TABLE_NAME}'...")
        
        try:
            dynamodb_client.delete_table(TableName=TABLE_NAME)
            
            print(f"⏳ Waiting for table to be fully deleted...")
            waiter = dynamodb_client.get_waiter('table_not_exists')
            waiter.wait(TableName=TABLE_NAME)
            
            print(f"✅ Old table deleted successfully")
            
        except Exception as e:
            print(f"❌ Error deleting table: {str(e)}")
            return False
    
    # Step 4: Create new table with new schema
    print()
    print(f"📝 Creating new table '{TABLE_NAME}' with new schema...")
    print(f"   Primary Key: contact_id (auto-generated UUID)")
    print(f"   Global Secondary Index: email-index (for email lookups)")
    
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'contact_id',
                    'KeyType': 'HASH'  # Partition key (auto-generated UUID)
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'contact_id',
                    'AttributeType': 'S'  # String (UUID)
                },
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'  # String (for GSI)
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'email',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"⏳ Waiting for table to be created...")
        table.wait_until_exists()
        
        print()
        print("="*80)
        print("✅ MIGRATION COMPLETE!")
        print("="*80)
        print()
        print(f"New Table: {TABLE_NAME}")
        print(f"Primary Key: contact_id (auto-generated UUID)")
        print(f"GSI: email-index (allows duplicate emails)")
        print()
        print("📋 Schema Details:")
        print("   ✓ contact_id (Primary Key) - auto-generated UUID")
        print("   ✓ email - stored in GSI for lookups")
        print("   ✓ Allows duplicate email addresses")
        print("   ✗ No 'group' column (removed)")
        print()
        print("All other fields remain the same:")
        print("   first_name, last_name, title, entity_type, state,")
        print("   agency_name, sector, subsection, phone, ms_isac_member,")
        print("   soc_call, fusion_center, k12, water_wastewater,")
        print("   weekly_rollup, alternate_email, region, created_at")
        print()
        print("="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Generate test data:")
        print("   python generate_test_contacts.py")
        print()
        print("2. Or import contacts via Web UI:")
        print("   - CSV import will now use auto-generated contact_id")
        print()
        print("3. Update Lambda to use new table (if needed):")
        print("   python update_lambda.py")
        print("="*80)
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"✅ Table '{TABLE_NAME}' already exists with new schema")
            return True
        else:
            print(f"❌ Error creating table: {str(e)}")
            return False

def main():
    """Main function"""
    try:
        result = migrate_emailcontacts_table()
        
        if result:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

