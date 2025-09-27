import boto3
import json
import zipfile

def deploy_api_gateway_lambda():
    """Deploy Lambda function for API Gateway"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')
    
    function_name = 'email-api-function'
    
    # Create deployment package
    with zipfile.ZipFile('api_lambda_function.zip', 'w') as zip_file:
        zip_file.write('api_gateway_lambda.py', 'lambda_function.py')
    
    try:
        # Deploy Lambda function
        with open('api_lambda_function.zip', 'rb') as zip_file:
            zip_content = zip_file.read()
        
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws-us-gov:iam::YOUR_ACCOUNT_ID:role/lambda-email-sender-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='API Gateway Lambda for bulk email sender',
                Timeout=300,
                MemorySize=256
            )
            print(f"Lambda function {function_name} created!")
            
        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            print(f"Lambda function {function_name} updated!")
        
        # Create API Gateway
        api_response = apigateway_client.create_rest_api(
            name='bulk-email-api',
            description='Bulk Email Sender API'
        )
        
        api_id = api_response['id']
        print(f"API Gateway created: {api_id}")
        
        # Get root resource
        resources = apigateway_client.get_resources(restApiId=api_id)
        root_id = resources['items'][0]['id']
        
        # Create /contacts resource
        contacts_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='contacts'
        )
        
        # Create /campaign resource
        campaign_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='campaign'
        )
        
        # Add methods to /contacts
        for method in ['GET', 'POST', 'OPTIONS']:
            apigateway_client.put_method(
                restApiId=api_id,
                resourceId=contacts_resource['id'],
                httpMethod=method,
                authorizationType='NONE'
            )
            
            # Add integration
            apigateway_client.put_integration(
                restApiId=api_id,
                resourceId=contacts_resource['id'],
                httpMethod=method,
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/arn:aws-us-gov:lambda:us-gov-west-1:YOUR_ACCOUNT_ID:function:{function_name}/invocations"
            )
        
        # Add methods to /campaign
        for method in ['POST', 'OPTIONS']:
            apigateway_client.put_method(
                restApiId=api_id,
                resourceId=campaign_resource['id'],
                httpMethod=method,
                authorizationType='NONE'
            )
            
            # Add integration
            apigateway_client.put_integration(
                restApiId=api_id,
                resourceId=campaign_resource['id'],
                httpMethod=method,
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f"arn:aws-us-gov:apigateway:us-gov-west-1:lambda:path/2015-03-31/functions/arn:aws-us-gov:lambda:us-gov-west-1:YOUR_ACCOUNT_ID:function:{function_name}/invocations"
            )
        
        # Deploy API
        deployment = apigateway_client.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )
        
        # Add Lambda permission for API Gateway
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='api-gateway-invoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws-us-gov:execute-api:us-gov-west-1:YOUR_ACCOUNT_ID:{api_id}/*/*"
        )
        
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"API Gateway URL: {api_url}")
        print(f"Update the API_BASE_URL in web_ui.html to: {api_url}")
        
        return api_url
        
    except Exception as e:
        print(f"Error deploying API Gateway: {str(e)}")
        return None

if __name__ == "__main__":
    print("Deploying API Gateway and Lambda...")
    print("Note: Update YOUR_ACCOUNT_ID in the script before running!")
    
    # Uncomment after updating account ID
    # deploy_api_gateway_lambda()