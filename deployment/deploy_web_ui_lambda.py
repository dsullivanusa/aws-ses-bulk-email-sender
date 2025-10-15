import boto3
import zipfile

def deploy_web_ui_lambda():
    """Deploy web UI Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    function_name = 'vpc-smtp-web-ui-function'
    
    # Create deployment package
    with zipfile.ZipFile('web_ui_lambda.zip', 'w') as zip_file:
        zip_file.write('web_ui_lambda.py', 'lambda_function.py')
    
    try:
        with open('web_ui_lambda.zip', 'rb') as zip_file:
            zip_content = zip_file.read()
        
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws-us-gov:iam::YOUR_ACCOUNT_ID:role/lambda-email-sender-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Web UI Lambda for VPC SMTP API',
                Timeout=30,
                MemorySize=128
            )
            print(f"Web UI Lambda function {function_name} created!")
            
        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"Web UI Lambda function {function_name} updated!")
        
        return function_name
        
    except Exception as e:
        print(f"Error deploying web UI Lambda: {str(e)}")
        return None

if __name__ == "__main__":
    print("Deploying Web UI Lambda...")
    result = deploy_web_ui_lambda()
    if result:
        print("Web UI Lambda deployed successfully!")
    else:
        print("Failed to deploy Web UI Lambda")