import boto3

def create_campaigns_table():
    """Create DynamoDB table for email campaigns tracking"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
    
    table_name = 'EmailCampaigns'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'campaign_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'campaign_id',
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

if __name__ == "__main__":
    create_campaigns_table()