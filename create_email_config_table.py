import boto3

def create_email_config_table():
    """Create EmailConfig DynamoDB table"""
    
    dynamodb = boto3.client('dynamodb', region_name='us-gov-west-1')
    
    try:
        # Check if table exists
        try:
            dynamodb.describe_table(TableName='EmailConfig')
            print("EmailConfig table already exists!")
        except dynamodb.exceptions.ResourceNotFoundException:
            # Create table
            dynamodb.create_table(
                TableName='EmailConfig',
                KeySchema=[
                    {'AttributeName': 'config_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'config_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print("EmailConfig table created successfully!")
            
            # Wait for table to be active
            print("Waiting for table to be active...")
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(TableName='EmailConfig')
        
        # Add default config
        dynamodb.put_item(
            TableName='EmailConfig',
            Item={
                'config_id': {'S': 'default'},
                'email_service': {'S': 'ses'},
                'from_email': {'S': 'sender@domain.com'},
                'emails_per_minute': {'N': '60'},
                'aws_region': {'S': 'us-gov-west-1'}
            }
        )
        print("Default email config added!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_email_config_table()