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
    
    # Define allowed IP address blocks only
    allowed_ip_blocks = [
        "10.0.0.0/16",      # VPC CIDR
        "192.168.1.0/24",   # Office network
        "203.0.113.0/24",   # Additional network
        "198.51.100.0/24",  # Another network
        "172.16.0.0/12",    # Private network range
        "10.1.0.0/16",      # Additional VPC
        "10.2.0.0/16"       # Another VPC
    ]
    
    # Update policy to allow only IP address blocks
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": f"arn:aws-us-gov:execute-api:us-gov-west-1:*:{api_id}/*",
                "Condition": {
                    "IpAddress": {
                        "aws:sourceIp": allowed_ip_blocks
                    }
                }
            }
        ]
    }
    
    apigateway.update_rest_api(
        restApiId=api_id,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/policy',
                'value': json.dumps(policy)
            }
        ]
    )
    
    print(f"Updated API Gateway policy for {api_id}")
    print(f"Allowed IP blocks: {', '.join(allowed_ip_blocks)}")
    print(f"Access URL: https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod/web")

if __name__ == "__main__":
    fix_api_policy()