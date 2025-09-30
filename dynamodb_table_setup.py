import boto3
import json

def create_dynamodb_table():
    """Create DynamoDB table for email contacts"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
    
    table_name = 'EmailContacts'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        
        print(f"Table {table_name} created successfully!")
        print(f"Table status: {table.table_status}")
        
        return table
        
    except Exception as e:
        print(f"Error creating table: {str(e)}")
        return None

def add_sample_contacts(table):
    """Add sample contacts to the table"""
    
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
        }
    ]
    
    try:
        with table.batch_writer() as batch:
            for contact in sample_contacts:
                batch.put_item(Item=contact)
        
        print(f"Added {len(sample_contacts)} sample contacts!")
        
    except Exception as e:
        print(f"Error adding sample contacts: {str(e)}")

if __name__ == "__main__":
    # Create table
    table = create_dynamodb_table()
    
    if table:
        # Add sample data
        add_sample_contacts(table)