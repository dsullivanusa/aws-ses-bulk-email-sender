import boto3
import json

def test_smtp_config():
    # Test DynamoDB connection
    dynamodb = boto3.client('dynamodb', region_name='us-gov-west-1')
    
    try:
        # Check if SMTPConfig table exists
        response = dynamodb.describe_table(TableName='SMTPConfig')
        print("✓ SMTPConfig table exists")
        
        # Test saving config directly to DynamoDB
        dynamodb.put_item(
            TableName='SMTPConfig',
            Item={
                'config_id': {'S': 'test'},
                'smtp_server': {'S': '192.168.1.100'},
                'smtp_port': {'N': '25'},
                'from_email': {'S': 'test@domain.com'}
            }
        )
        print("✓ Direct DynamoDB write successful")
        
        # Test reading config
        response = dynamodb.get_item(
            TableName='SMTPConfig',
            Key={'config_id': {'S': 'test'}}
        )
        if 'Item' in response:
            print("✓ Direct DynamoDB read successful")
        else:
            print("✗ Could not read from DynamoDB")
            
    except Exception as e:
        print(f"✗ DynamoDB error: {e}")
    
    # Test Lambda function endpoint
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    functions = lambda_client.list_functions()
    smtp_functions = [f['FunctionName'] for f in functions['Functions'] if 'smtp' in f['FunctionName'].lower() or 'email' in f['FunctionName'].lower()]
    
    if smtp_functions:
        function_name = smtp_functions[0]
        print(f"Testing SMTP config endpoint on: {function_name}")
        
        # Test POST /smtp-config
        test_payload = {
            "httpMethod": "POST",
            "resource": "/smtp-config",
            "body": json.dumps({
                "smtp_server": "192.168.1.200",
                "smtp_port": 587,
                "from_email": "test@example.com"
            }),
            "requestContext": {"identity": {"sourceIp": "192.168.1.1"}}
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(test_payload)
            )
            
            result = json.loads(response['Payload'].read().decode())
            print(f"Lambda response: {result}")
            
            if result.get('statusCode') == 200:
                print("✓ SMTP config save endpoint working")
            else:
                print("✗ SMTP config save endpoint failed")
                
        except Exception as e:
            print(f"✗ Lambda invoke error: {e}")
    else:
        print("✗ No SMTP Lambda function found")

if __name__ == "__main__":
    test_smtp_config()