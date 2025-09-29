import boto3

def test_web_ui():
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    # Test invoke the web UI function
    functions = lambda_client.list_functions()
    web_functions = [f['FunctionName'] for f in functions['Functions'] if 'web' in f['FunctionName'].lower()]
    
    if web_functions:
        function_name = web_functions[0]
        print(f"Testing function: {function_name}")
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload='{"httpMethod": "GET", "resource": "/web", "requestContext": {"apiId": "test"}}'
        )
        
        result = response['Payload'].read().decode()
        print("Function response received")
        
        # Check if SES dropdown is in the response
        if 'emailService' in result and 'AWS SES' in result:
            print("✓ SES configuration found in web UI")
        else:
            print("✗ SES configuration NOT found in web UI")
            print("The Lambda function needs to be updated")
    else:
        print("No web UI Lambda function found")

if __name__ == "__main__":
    test_web_ui()