#!/usr/bin/env python3
"""
Create new EmailContacts table with auto-generated contact_id as primary key
This allows duplicate email addresses for testing
"""

import boto3
import json
from botocore.exceptions import ClientError

REGION = 'us-gov-west-1'
TABLE_NAME = 'EmailContacts'
NEW_TABLE_NAME = 'EmailContactsNew'  # Create new table first to avoid data loss

def create_new_contacts_table():
    """Create new EmailContacts table with contact_id as primary key"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=REGION)
    
    print("="*70)
    print("Creating New EmailContacts Table Schema")
    print("="*70)
    print()
    
    # Check if old table exists
    try:
        old_table = dynamodb.Table(TABLE_NAME)
        old_table.load()
        print(f"⚠️  WARNING: Table '{TABLE_NAME}' already exists with old schema")
        print(f"   Creating new table as '{NEW_TABLE_NAME}' to preserve existing data")
        print(f"   After migration, you can delete old table and rename new one")
        target_table_name = NEW_TABLE_NAME
    except ClientError:
        print(f"✓ Table '{TABLE_NAME}' doesn't exist, will create with new schema")
        target_table_name = TABLE_NAME
    
    # Define new schema
    print(f"\n📝 Creating table: {target_table_name}")
    print(f"   Primary Key: contact_id (auto-generated UUID)")
    print(f"   Global Secondary Index: email-index (for email lookups)")
    
    try:
        table = dynamodb.create_table(
            TableName=target_table_name,
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
                    }
                    # ProvisionedThroughput not needed with PAY_PER_REQUEST
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"⏳ Waiting for table to be created...")
        table.wait_until_exists()
        
        print(f"✅ Table '{target_table_name}' created successfully!")
        
        # Display schema
        print(f"\n📋 New Schema:")
        print(f"   Primary Key: contact_id (UUID)")
        print(f"   GSI: email-index (allows email lookups)")
        print(f"   Fields: email, first_name, last_name, title, entity_type,")
        print(f"           state, agency_name, sector, subsection, phone,")
        print(f"           ms_isac_member, soc_call, fusion_center, k12,")
        print(f"           water_wastewater, weekly_rollup, alternate_email,")
        print(f"           region, created_at")
        print(f"   Removed: group (as requested)")
        
        print(f"\n✅ Table ready for contacts!")
        print(f"\nNext steps:")
        print(f"  1. Run: python generate_test_contacts.py")
        print(f"  2. This will create 10,000 test contacts with same email")
        print(f"  3. Update Lambda functions to use contact_id instead of email")
        
        return target_table_name
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"✅ Table '{target_table_name}' already exists")
            return target_table_name
        else:
            print(f"❌ Error creating table: {str(e)}")
            raise

if __name__ == '__main__':
    create_new_contacts_table()

