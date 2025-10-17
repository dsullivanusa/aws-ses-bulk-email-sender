import boto3
import json

def create_vpc_infrastructure():
    """Create VPC infrastructure for private API Gateway"""
    
    ec2 = boto3.client('ec2', region_name='us-gov-west-1')
    
    try:
        # Create VPC
        vpc_response = ec2.create_vpc(
            CidrBlock='10.0.0.0/16',
            TagSpecifications=[
                {
                    'ResourceType': 'vpc',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-email-vpc'},
                        {'Key': 'Purpose', 'Value': 'SES Email API'}
                    ]
                }
            ]
        )
        vpc_id = vpc_response['Vpc']['VpcId']
        print(f"Created VPC: {vpc_id}")
        
        # Create private subnet
        subnet_response = ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock='10.0.1.0/24',
            AvailabilityZone='us-gov-west-1a',
            TagSpecifications=[
                {
                    'ResourceType': 'subnet',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-private-subnet'},
                        {'Key': 'Type', 'Value': 'Private'}
                    ]
                }
            ]
        )
        subnet_id = subnet_response['Subnet']['SubnetId']
        print(f"Created Private Subnet: {subnet_id}")
        
        # Create security group for Lambda
        sg_response = ec2.create_security_group(
            GroupName='ses-lambda-sg',
            Description='Security group for SES Lambda in VPC',
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-lambda-sg'}
                    ]
                }
            ]
        )
        sg_id = sg_response['GroupId']
        print(f"Created Security Group: {sg_id}")
        
        # Add outbound rules for HTTPS (SES, DynamoDB)
        ec2.authorize_security_group_egress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        
        # Create VPC endpoints for AWS services
        
        # DynamoDB VPC Endpoint
        dynamodb_endpoint = ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName='com.amazonaws.us-gov-west-1.dynamodb',
            VpcEndpointType='Gateway',
            RouteTableIds=[],  # Will be updated after route table creation
            TagSpecifications=[
                {
                    'ResourceType': 'vpc-endpoint',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-dynamodb-endpoint'}
                    ]
                }
            ]
        )
        print(f"Created DynamoDB VPC Endpoint: {dynamodb_endpoint['VpcEndpoint']['VpcEndpointId']}")
        
        # SES VPC Endpoint (Interface)
        ses_endpoint = ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName='com.amazonaws.us-gov-west-1.email-smtp',
            VpcEndpointType='Interface',
            SubnetIds=[subnet_id],
            SecurityGroupIds=[sg_id],
            TagSpecifications=[
                {
                    'ResourceType': 'vpc-endpoint',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-smtp-endpoint'}
                    ]
                }
            ]
        )
        print(f"Created SES VPC Endpoint: {ses_endpoint['VpcEndpoint']['VpcEndpointId']}")
        
        return {
            'vpc_id': vpc_id,
            'subnet_id': subnet_id,
            'security_group_id': sg_id,
            'dynamodb_endpoint_id': dynamodb_endpoint['VpcEndpoint']['VpcEndpointId'],
            'ses_endpoint_id': ses_endpoint['VpcEndpoint']['VpcEndpointId']
        }
        
    except Exception as e:
        print(f"Error creating VPC infrastructure: {str(e)}")
        return None

def create_api_gateway_vpc_endpoint():
    """Create VPC endpoint for API Gateway"""
    
    ec2 = boto3.client('ec2', region_name='us-gov-west-1')
    
    # Get existing VPC info (run after create_vpc_infrastructure)
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['ses-email-vpc']}])
    if not vpcs['Vpcs']:
        print("VPC not found. Run create_vpc_infrastructure first.")
        return None
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    
    subnets = ec2.describe_subnets(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'tag:Name', 'Values': ['ses-private-subnet']}
    ])
    subnet_id = subnets['Subnets'][0]['SubnetId']
    
    security_groups = ec2.describe_security_groups(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'group-name', 'Values': ['ses-lambda-sg']}
    ])
    sg_id = security_groups['SecurityGroups'][0]['GroupId']
    
    try:
        # Create API Gateway VPC Endpoint
        api_endpoint = ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName='com.amazonaws.us-gov-west-1.execute-api',
            VpcEndpointType='Interface',
            SubnetIds=[subnet_id],
            SecurityGroupIds=[sg_id],
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": [
                            "execute-api:Invoke"
                        ],
                        "Resource": "*"
                    }
                ]
            }),
            TagSpecifications=[
                {
                    'ResourceType': 'vpc-endpoint',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-api-gateway-endpoint'}
                    ]
                }
            ]
        )
        
        endpoint_id = api_endpoint['VpcEndpoint']['VpcEndpointId']
        print(f"Created API Gateway VPC Endpoint: {endpoint_id}")
        
        return endpoint_id
        
    except Exception as e:
        print(f"Error creating API Gateway VPC endpoint: {str(e)}")
        return None

if __name__ == "__main__":
    print("Creating VPC infrastructure for SES API...")
    
    # Create VPC and related resources
    vpc_info = create_vpc_infrastructure()
    
    if vpc_info:
        print("\nVPC Infrastructure created successfully!")
        print(f"VPC ID: {vpc_info['vpc_id']}")
        print(f"Subnet ID: {vpc_info['subnet_id']}")
        print(f"Security Group ID: {vpc_info['security_group_id']}")
        
        # Create API Gateway VPC endpoint
        print("\nCreating API Gateway VPC endpoint...")
        api_endpoint_id = create_api_gateway_vpc_endpoint()
        
        if api_endpoint_id:
            print(f"API Gateway VPC Endpoint ID: {api_endpoint_id}")
            
            print("\nVPC Infrastructure Summary:")
            print("- Private VPC with isolated subnets")
            print("- VPC endpoints for DynamoDB, SES, and API Gateway")
            print("- Security groups configured for HTTPS traffic")
            print("- Ready for private API Gateway deployment")
        else:
            print("Failed to create API Gateway VPC endpoint")
    else:
        print("Failed to create VPC infrastructure")