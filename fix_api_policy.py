import boto3
import json

def fix_api_policy():
    """Update API Gateway policy to allow VPC access"""
    
    apigateway = boto3.client('apigateway', region_name='us-gov-west-1')
    ec2 = boto3.client('ec2', region_name='us-gov-west-1')
    
    # Get API Gateway
    apis = apigateway.get_rest_apis()
    api_id = None
    for api in apis['items']:
        if api['name'] == 'vpc-smtp-bulk-email-api':
            api_id = api['id']
            break
    
    if not api_id:
        print("API Gateway not found")
        return
    
    # Get VPC ID
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:SES', 'Values': ['ses-email-vpc']}])
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    
    # Get VPC endpoint ID
    vpc_endpoints = ec2.describe_vpc_endpoints(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'service-name', 'Values': ['com.amazonaws.us-gov-west-1.execute-api']}
    ])
    vpc_endpoint_id = vpc_endpoints['VpcEndpoints'][0]['VpcEndpointId']
    
    # Update policy to allow VPC access
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": f"arn:aws-us-gov:execute-api:us-gov-west-1:*:{api_id}/*",
                "Condition": {
                    "StringEquals": {
                        "aws:sourceVpce": vpc_endpoint_id
                    }
                }
            }
        ]
    }
    
    apigateway.update_rest_api(
        restApiId=api_id,
        patchOps=[
            {
                'op': 'replace',
                'path': '/policy',
                'value': json.dumps(policy)
            }
        ]
    )
    
    print(f"Updated API Gateway policy for {api_id}")
    print(f"Access URL: https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod/web")

if __name__ == "__main__":
    fix_api_policy()