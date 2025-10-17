#!/usr/bin/env python3
"""
Comprehensive DynamoDB table setup script for the CISA Bulk Email System.
This script safely creates all necessary tables, handling existing tables gracefully.
"""

import boto3
import json
from botocore.exceptions import ClientError

def create_table_if_not_exists(table_name, key_schema, attribute_definitions, billing_mode='PAY_PER_REQUEST'):
    """Create a DynamoDB table if it doesn't already exist"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
    
    try:
        # Check if table already exists
        try:
            table = dynamodb.Table(table_name)
            table.load()  # This will raise an exception if table doesn't exist
            print(f"✅ Table '{table_name}' already exists (Status: {table.table_status})")
            return table
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                pass
            else:
                raise e
        
        # Create the table
        print(f"📝 Creating table '{table_name}'...")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode=billing_mode
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        print(f"✅ Table '{table_name}' created successfully! (Status: {table.table_status})")
        return table
        
    except Exception as e:
        print(f"❌ Error with table '{table_name}': {str(e)}")
        return None

def setup_email_contacts_table():
    """Setup EmailContacts table with all CISA fields"""
    
    table_name = 'EmailContacts'
    key_schema = [
        {
            'AttributeName': 'email',
            'KeyType': 'HASH'  # Partition key
        }
    ]
    attribute_definitions = [
        {
            'AttributeName': 'email',
            'AttributeType': 'S'
        }
    ]
    
    return create_table_if_not_exists(table_name, key_schema, attribute_definitions)

def setup_email_campaigns_table():
    """Setup EmailCampaigns table for campaign tracking"""
    
    table_name = 'EmailCampaigns'
    key_schema = [
        {
            'AttributeName': 'campaign_id',
            'KeyType': 'HASH'  # Partition key
        }
    ]
    attribute_definitions = [
        {
            'AttributeName': 'campaign_id',
            'AttributeType': 'S'
        }
    ]
    
    return create_table_if_not_exists(table_name, key_schema, attribute_definitions)

def setup_email_config_table():
    """Setup EmailConfig table for email service configuration"""
    
    table_name = 'EmailConfig'
    key_schema = [
        {
            'AttributeName': 'config_id',
            'KeyType': 'HASH'  # Partition key
        }
    ]
    attribute_definitions = [
        {
            'AttributeName': 'config_id',
            'AttributeType': 'S'
        }
    ]
    
    return create_table_if_not_exists(table_name, key_schema, attribute_definitions)

def add_sample_contacts():
    """Add sample contacts with all CISA fields"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
    table = dynamodb.Table('EmailContacts')
    
    # Check if sample contacts already exist
    try:
        response = table.get_item(Key={'email': 'john.doe@example.com'})
        if 'Item' in response:
            print("✅ Sample contacts already exist, skipping...")
            return
    except:
        pass
    
    sample_contacts = [
        {
            'email': 'john.doe@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'title': 'IT Director',
            'entity_type': 'State Government',
            'state': 'California',
            'agency_name': 'Department of Technology',
            'sector': 'Government',
            'subsection': 'IT Services',
            'phone': '555-0100',
            'ms_isac_member': 'Yes',
            'soc_call': 'Yes',
            'fusion_center': 'Yes',
            'k12': 'No',
            'water_wastewater': 'No',
            'weekly_rollup': 'Yes',
            'alternate_email': 'j.doe@alternate.com',
            'region': 'West',
            'group': 'State CISOs',
            'created_at': '2024-01-01T00:00:00',
            'last_email_sent': None,
            'email_count': 0
        },
        {
            'email': 'jane.smith@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'title': 'Security Analyst',
            'entity_type': 'Local Government',
            'state': 'Texas',
            'agency_name': 'City of Austin',
            'sector': 'Government',
            'subsection': 'Cybersecurity',
            'phone': '555-0200',
            'ms_isac_member': 'Yes',
            'soc_call': 'No',
            'fusion_center': 'No',
            'k12': 'No',
            'water_wastewater': 'No',
            'weekly_rollup': 'Yes',
            'alternate_email': '',
            'region': 'South',
            'group': 'Local Government',
            'created_at': '2024-01-01T00:00:00',
            'last_email_sent': None,
            'email_count': 0
        },
        {
            'email': 'bob.wilson@example.com',
            'first_name': 'Bob',
            'last_name': 'Wilson',
            'title': 'CISO',
            'entity_type': 'State Government',
            'state': 'New York',
            'agency_name': 'Office of IT Services',
            'sector': 'Government',
            'subsection': 'Security',
            'phone': '555-0300',
            'ms_isac_member': 'Yes',
            'soc_call': 'Yes',
            'fusion_center': 'Yes',
            'k12': 'No',
            'water_wastewater': 'No',
            'weekly_rollup': 'Yes',
            'alternate_email': 'b.wilson@alt.com',
            'region': 'Northeast',
            'group': 'State CISOs',
            'created_at': '2024-01-01T00:00:00',
            'last_email_sent': None,
            'email_count': 0
        }
    ]
    
    try:
        with table.batch_writer() as batch:
            for contact in sample_contacts:
                batch.put_item(Item=contact)
        
        print(f"✅ Added {len(sample_contacts)} sample contacts!")
        
    except Exception as e:
        print(f"❌ Error adding sample contacts: {str(e)}")

def main():
    """Main setup function"""
    
    print("🚀 Setting up CISA Bulk Email System DynamoDB Tables...")
    print("=" * 60)
    
    # Setup all tables
    contacts_table = setup_email_contacts_table()
    campaigns_table = setup_email_campaigns_table()
    config_table = setup_email_config_table()
    
    print("\n" + "=" * 60)
    
    # Add sample data if contacts table was created or already exists
    if contacts_table:
        print("\n📝 Adding sample contacts...")
        add_sample_contacts()
    
    print("\n" + "=" * 60)
    print("✅ DynamoDB setup complete!")
    print("\nTables created/verified:")
    print("  • EmailContacts - Contact management with all CISA fields")
    print("  • EmailCampaigns - Campaign tracking and status")
    print("  • EmailConfig - Email service configuration")
    print("\n🎉 Ready to deploy the bulk email system!")

if __name__ == "__main__":
    main()
