import boto3
import time

def create_smtp_config_table():
    dynamodb = boto3.client('dynamodb', region_name='us-gov-west-1')
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName='SMTPConfig')
            print("SMTPConfig table already exists!")
        except dynamodb.exceptions.ResourceNotFoundException:
            # Create table if it doesn't exist
            dynamodb.create_table(
                TableName='SMTPConfig',
                KeySchema=[
                    {'AttributeName': 'config_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'config_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print("SMTPConfig table created successfully!")
            
            # Wait for table to be active
            print("Waiting for table to be active...")
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(TableName='SMTPConfig')
        
        # Add default config
        dynamodb.put_item(
            TableName='SMTPConfig',
            Item={
                'config_id': {'S': 'default'},
                'smtp_server': {'S': '192.168.1.100'},
                'smtp_port': {'N': '25'},
                'from_email': {'S': 'sender@domain.com'}
            }
        )
        print("Default SMTP config added!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_smtp_config_table()