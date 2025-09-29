import boto3

def create_smtp_config_table():
    dynamodb = boto3.client('dynamodb', region_name='us-gov-west-1')
    
    try:
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