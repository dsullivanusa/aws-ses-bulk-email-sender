import boto3
import zipfile
import os

def update_lambda_functions():
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    # Get all Lambda functions
    functions = lambda_client.list_functions()
    function_names = [f['FunctionName'] for f in functions['Functions']]
    
    print("Available Lambda functions:")
    for name in function_names:
        print(f"- {name}")
    
    # Update web UI Lambda
    web_ui_functions = [name for name in function_names if 'vpc-smtp-web-ui' in name]
    if web_ui_functions:
        with zipfile.ZipFile('web_ui_lambda.zip', 'w') as zip_file:
            zip_file.write('web_ui_lambda.py', 'lambda_function.py')
        
        with open('web_ui_lambda.zip', 'rb') as zip_file:
            lambda_client.update_function_code(
                FunctionName=web_ui_functions[0],
                ZipFile=zip_file.read()
            )
        print(f"Updated {web_ui_functions[0]} successfully!")
        os.remove('web_ui_lambda.zip')
    else:
        print("No web UI Lambda function found matching 'vpc-smtp-web-ui'")
    
    # Update VPC SMTP Lambda - try multiple patterns
    smtp_patterns = ['vpc-smtp-email-api-function', 'vpc-smtp-email', 'smtp', 'email']
    smtp_functions = []
    
    for pattern in smtp_patterns:
        smtp_functions = [name for name in function_names if pattern in name]
        if smtp_functions:
            print(f"Found SMTP function with pattern '{pattern}': {smtp_functions[0]}")
            break
    
    if smtp_functions:
        with zipfile.ZipFile('vpc_smtp_lambda.zip', 'w') as zip_file:
            zip_file.write('vpc_smtp_lambda_function.py', 'lambda_function.py')
        
        with open('vpc_smtp_lambda.zip', 'rb') as zip_file:
            lambda_client.update_function_code(
                FunctionName=smtp_functions[0],
                ZipFile=zip_file.read()
            )
        print(f"Updated {smtp_functions[0]} successfully!")
        os.remove('vpc_smtp_lambda.zip')
    else:
        print("No SMTP Lambda function found. You may need to deploy it first using deploy_vpc_smtp_api.py")

if __name__ == "__main__":
    update_lambda_functions()