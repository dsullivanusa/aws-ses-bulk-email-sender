import boto3
import zipfile
import os

def update_web_ui_lambda():
    # Create zip file
    with zipfile.ZipFile('web_ui_lambda.zip', 'w') as zip_file:
        zip_file.write('web_ui_lambda.py')
    
    # Update Lambda function
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    with open('web_ui_lambda.zip', 'rb') as zip_file:
        lambda_client.update_function_code(
            FunctionName='web-ui-lambda',
            ZipFile=zip_file.read()
        )
    
    print("Lambda function updated successfully!")
    os.remove('web_ui_lambda.zip')

if __name__ == "__main__":
    update_web_ui_lambda()