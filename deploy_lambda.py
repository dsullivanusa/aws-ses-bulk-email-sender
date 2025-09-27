import boto3
import zipfile
import json
import os

def create_lambda_deployment_package():
    """Create deployment package for Lambda function"""
    
    # Create zip file
    with zipfile.ZipFile('lambda_function.zip', 'w') as zip_file:
        zip_file.write('lambda_email_sender.py', 'lambda_function.py')
    
    print("Lambda deployment package created: lambda_function.zip")

def deploy_lambda_function():
    """Deploy Lambda function to AWS"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    function_name = 'email-sender-function'
    
    try:
        # Read the zip file
        with open('lambda_function.zip', 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Create or update Lambda function
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-email-sender-role',  # Replace with your role ARN
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Bulk email sender with DynamoDB integration',
                Timeout=300,
                MemorySize=256
            )
            print(f"Lambda function {function_name} created successfully!")
            
        except lambda_client.exceptions.ResourceConflictException:
            # Function exists, update it
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"Lambda function {function_name} updated successfully!")
        
        return response
        
    except Exception as e:
        print(f"Error deploying Lambda function: {str(e)}")
        return None

if __name__ == "__main__":
    print("Creating Lambda deployment package...")
    create_lambda_deployment_package()
    
    print("\nDeploying Lambda function...")
    print("Note: Make sure to update the IAM role ARN in the script before running!")
    
    # Uncomment the line below after updating the IAM role ARN
    # deploy_lambda_function()