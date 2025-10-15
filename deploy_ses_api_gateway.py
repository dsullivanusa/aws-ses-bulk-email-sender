import boto3
import json
import zipfile

def deploy_ses_api_gateway():
    """Deploy SES Lambda function and API Gateway"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')
    
    function_name = 'ses-email-api-function'
    
    # Create deployment package
    with zipfile.ZipFile('ses_lambda_function.zip', 'w') as zip_file:
        zip_file.write('ses_lambda_function.py', 'lambda_function.py')
    
    try:
        # Deploy Lambda function
        with open('ses_lambda_function.zip', 'rb') as zip_file:
            zip_content = zip_file.read()
        
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.13',
                Role='arn:aws-us-gov:iam::YOUR_ACCOUNT_ID:role/lambda-email-sender-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='SES API Gateway Lambda for bulk email sender with attachments',
                Timeout=900,  # 15 minutes for bulk sending
                MemorySize=512
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
            name='ses-bulk-email-api',
            description='AWS SES Bulk Email Sender API with Attachments'
        )
        
        api_id = api_response['id']
        print(f"API Gateway created: {api_id}")
        
        # Get root resource
        resources = apigateway_client.get_resources(restApiId=api_id)
        root_id = resources['items'][0]['id']
        
        # Create resources
        contacts_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='contacts'
        )
        
        ses_campaign_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='ses-campaign'
        )
        
        campaign_status_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='campaign-status'
        )
        
        campaign_id_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=campaign_status_resource['id'],
            pathPart='{campaign_id}'
        )
        
        # Add methods and integrations
        resources_methods = [
            (contacts_resource['id'], ['GET', 'POST', 'OPTIONS']),
            (ses_campaign_resource['id'], ['POST', 'OPTIONS']),
            (campaign_id_resource['id'], ['GET', 'OPTIONS'])
        ]
        
        for resource_id, methods in resources_methods:
            for method in methods:
                # Create method
                apigateway_client.put_method(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod=method,
                    authorizationType='NONE'
                )
                
                # Add integration
                apigateway_client.put_integration(
                    restApiId=api_id,
                    resourceId=resource_id,
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
            StatementId='ses-api-gateway-invoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws-us-gov:execute-api:us-gov-west-1:YOUR_ACCOUNT_ID:{api_id}/*/*"
        )
        
        api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        print(f"SES API Gateway URL: {api_url}")
        print(f"Update the API_BASE_URL in ses_web_ui_api.html to: {api_url}")
        
        return api_url
        
    except Exception as e:
        print(f"Error deploying SES API Gateway: {str(e)}")
        return None

if __name__ == "__main__":
    print("Deploying SES API Gateway and Lambda...")
    print("Note: Update YOUR_ACCOUNT_ID in the script before running!")
    print("Ensure your sender email is verified in AWS SES console!")
    
    # Uncomment after updating account ID
    # deploy_ses_api_gateway()