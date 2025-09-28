import boto3

def fix_vpc_dns():
    """Enable private DNS for VPC endpoint and modify DHCP options"""
    
    ec2 = boto3.client('ec2', region_name='us-gov-west-1')
    
    # Get VPC
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:SES', 'Values': ['ses-email-vpc']}])
    if not vpcs['Vpcs']:
        print("VPC not found")
        return
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    
    # Enable DNS hostnames and resolution for VPC
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    print(f"Enabled DNS for VPC: {vpc_id}")
    
    # Get VPC endpoint
    vpc_endpoints = ec2.describe_vpc_endpoints(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'service-name', 'Values': ['com.amazonaws.us-gov-west-1.execute-api']}
    ])
    
    if vpc_endpoints['VpcEndpoints']:
        endpoint_id = vpc_endpoints['VpcEndpoints'][0]['VpcEndpointId']
        
        # Modify VPC endpoint to enable private DNS
        ec2.modify_vpc_endpoint(
            VpcEndpointId=endpoint_id,
            PrivateDnsEnabled=True
        )
        print(f"Enabled private DNS for VPC endpoint: {endpoint_id}")
        
        # Get the private DNS name
        endpoint = vpc_endpoints['VpcEndpoints'][0]
        if endpoint['DnsEntries']:
            dns_name = endpoint['DnsEntries'][0]['DnsName']
            print(f"VPC Endpoint DNS: {dns_name}")
            
            # Get API Gateway ID from deployment
            api_gateways = boto3.client('apigateway', region_name='us-gov-west-1').get_rest_apis()
            for api in api_gateways['items']:
                if api['name'] == 'vpc-smtp-bulk-email-api':
                    api_id = api['id']
                    print(f"Use this URL from within VPC: https://{api_id}.execute-api.us-gov-west-1.amazonaws.com/prod/web")
                    break
    else:
        print("No VPC endpoint found")

if __name__ == "__main__":
    fix_vpc_dns()