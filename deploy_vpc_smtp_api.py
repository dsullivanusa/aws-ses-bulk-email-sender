import boto3
import json
import zipfile

def deploy_vpc_smtp_api():
    """Deploy SMTP Lambda and private API Gateway in VPC"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    apigateway_client = boto3.client('apigateway', region_name='us-gov-west-1')
    ec2 = boto3.client('ec2', region_name='us-gov-west-1')
    
    function_name = 'vpc-smtp-email-api-function'
    
    # Get VPC configuration
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['ses-email-vpc']}])
    if not vpcs['Vpcs']:
        print("VPC not found. Run vpc_infrastructure.py first.")
        return None
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    
    subnets = ec2.describe_subnets(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'tag:Name', 'Values': ['ses-private-subnet']}
    ])
    subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
    
    security_groups = ec2.describe_security_groups(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'group-name', 'Values': ['ses-lambda-sg']}
    ])
    sg_ids = [sg['GroupId'] for sg in security_groups['SecurityGroups']]
    
    # Create deployment package
    with zipfile.ZipFile('vpc_smtp_lambda_function.zip', 'w') as zip_file:
        zip_file.write('vpc_smtp_lambda_function.py', 'lambda_function.py')
    
    try:
        # Deploy Lambda function in VPC
        with open('vpc_smtp_lambda_function.zip', 'rb') as zip_file:
            zip_content = zip_file.read()
        
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws-us-gov:iam::YOUR_ACCOUNT_ID:role/lambda-email-sender-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='VPC SMTP API Gateway Lambda for secure bulk email sender',
                Timeout=900,
                MemorySize=512,
                VpcConfig={
                    'SubnetIds': subnet_ids,
                    'SecurityGroupIds': sg_ids
                },
                Environment={
                    'Variables': {
                        'VPC_ENABLED': 'true',
                        'SMTP_SERVER': 'smtp.gmail.com',
                        'SMTP_PORT': '587',
                        'SMTP_USE_TLS': 'true'
                    }
                }
            )
            print(f"Lambda function {function_name} created in VPC!")
            
        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                VpcConfig={
                    'SubnetIds': subnet_ids,
                    'SecurityGroupIds': sg_ids
                }
            )
            print(f"Lambda function {function_name} updated in VPC!")
        
        # Create private API Gateway
        api_response = apigateway_client.create_rest_api(
            name='vpc-smtp-bulk-email-api',
            description='Private VPC SMTP Bulk Email Sender API',
            endpointConfiguration={
                'types': ['PRIVATE'],
                'vpcEndpointIds': get_vpc_endpoint_ids(ec2, vpc_id)
            },
            policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "execute-api:Invoke",
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {
                                "aws:sourceVpce": get_vpc_endpoint_ids(ec2, vpc_id)
                            }
                        }
                    }
                ]
            })
        )
        
        api_id = api_response['id']
        print(f"Private SMTP API Gateway created: {api_id}")
        
        # Get root resource
        resources = apigateway_client.get_resources(restApiId=api_id)
        root_id = resources['items'][0]['id']
        
        # Create resources
        contacts_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='contacts'
        )
        
        smtp_campaign_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='smtp-campaign'
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
            (smtp_campaign_resource['id'], ['POST', 'OPTIONS']),
            (campaign_id_resource['id'], ['GET', 'OPTIONS'])
        ]
        
        for resource_id, methods in resources_methods:
            for method in methods:
                apigateway_client.put_method(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod=method,
                    authorizationType='NONE'
                )
                
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
        
        # Add Lambda permission
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='vpc-smtp-api-gateway-invoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws-us-gov:execute-api:us-gov-west-1:YOUR_ACCOUNT_ID:{api_id}/*/*"
        )
        
        # Get VPC endpoint DNS
        vpc_endpoints = ec2.describe_vpc_endpoints(Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'service-name', 'Values': ['com.amazonaws.us-gov-west-1.execute-api']}
        ])
        
        if vpc_endpoints['VpcEndpoints']:
            vpc_endpoint_dns = vpc_endpoints['VpcEndpoints'][0]['DnsEntries'][0]['DnsName']
            api_url = f"https://{api_id}-{vpc_endpoint_dns}/prod"
        else:
            api_url = f"https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod"
        
        print(f"VPC SMTP API Gateway URL: {api_url}")
        print(f"VPC ID: {vpc_id}")
        print("SMTP API is accessible only from within the VPC")
        
        return {
            'api_id': api_id,
            'api_url': api_url,
            'vpc_id': vpc_id,
            'function_name': function_name
        }
        
    except Exception as e:
        print(f"Error deploying VPC SMTP API Gateway: {str(e)}")
        return None

def get_vpc_endpoint_ids(ec2, vpc_id):
    """Get VPC endpoint IDs for API Gateway"""
    vpc_endpoints = ec2.describe_vpc_endpoints(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'service-name', 'Values': ['com.amazonaws.us-gov-west-1.execute-api']}
    ])
    
    return [endpoint['VpcEndpointId'] for endpoint in vpc_endpoints['VpcEndpoints']]

if __name__ == "__main__":
    print("Deploying VPC SMTP API Gateway and Lambda...")
    print("Note: Update YOUR_ACCOUNT_ID in the script before running!")
    print("Ensure VPC infrastructure is created first!")
    
    # Uncomment after updating account ID and creating VPC
    # result = deploy_vpc_smtp_api()
    
    # if result:
    #     print("\nVPC SMTP API deployed successfully!")
    #     print("Access is restricted to VPC endpoints only")
    # else:
    #     print("Failed to deploy VPC SMTP API")