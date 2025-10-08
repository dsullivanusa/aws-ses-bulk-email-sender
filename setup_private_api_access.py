#!/usr/bin/env python3
"""
Setup Private API Gateway Access
Configures VPC endpoints and API Gateway policies to allow access to private API Gateway

This script will:
1. Check if VPC endpoint exists for execute-api service
2. Create VPC endpoint if missing
3. Update API Gateway resource policy to allow VPC endpoint access
4. Enable private DNS resolution
5. Provide access URLs and testing instructions
"""

import boto3
import json
import time

REGION = 'us-gov-west-1'

def get_current_setup():
    """Check current VPC and API Gateway setup"""
    
    print("="*80)
    print("🔍 CHECKING CURRENT SETUP")
    print("="*80)
    
    ec2 = boto3.client('ec2', region_name=REGION)
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    # Find VPC
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['ses-email-vpc']}])
    if not vpcs['Vpcs']:
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:SES', 'Values': ['ses-email-vpc']}])
    
    if not vpcs['Vpcs']:
        print("❌ No VPC found with tag 'ses-email-vpc'")
        return None, None, None
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    print(f"✅ Found VPC: {vpc_id}")
    
    # Find API Gateway
    apis = apigateway.get_rest_apis()['items']
    api_id = None
    api_name = None
    
    for api in apis:
        if 'bulk-email' in api['name'].lower() or 'vpc-smtp' in api['name'].lower():
            api_id = api['id']
            api_name = api['name']
            break
    
    if not api_id:
        print("❌ No bulk email API Gateway found")
        return vpc_id, None, None
    
    print(f"✅ Found API Gateway: {api_name} ({api_id})")
    
    # Check if it's private
    endpoint_config = apigateway.get_rest_api(restApiId=api_id).get('endpointConfiguration', {})
    if 'PRIVATE' in endpoint_config.get('types', []):
        print("✅ API Gateway is configured as PRIVATE")
    else:
        print("⚠️  API Gateway is not configured as PRIVATE")
    
    # Find VPC endpoint for execute-api
    vpc_endpoints = ec2.describe_vpc_endpoints(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'service-name', 'Values': [f'com.amazonaws.{REGION}.execute-api']}
    ])
    
    vpc_endpoint_id = None
    if vpc_endpoints['VpcEndpoints']:
        vpc_endpoint_id = vpc_endpoints['VpcEndpoints'][0]['VpcEndpointId']
        print(f"✅ Found VPC Endpoint: {vpc_endpoint_id}")
    else:
        print("❌ No VPC endpoint found for execute-api service")
    
    return vpc_id, api_id, vpc_endpoint_id

def create_vpc_endpoint(vpc_id):
    """Create VPC endpoint for execute-api service"""
    
    print(f"\n" + "="*80)
    print(f"🔧 CREATING VPC ENDPOINT")
    print("="*80)
    
    ec2 = boto3.client('ec2', region_name=REGION)
    
    try:
        # Get subnets in the VPC
        subnets = ec2.describe_subnets(Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'tag:Name', 'Values': ['ses-private-subnet']}
        ])
        
        if not subnets['Subnets']:
            # Try alternative naming
            subnets = ec2.describe_subnets(Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ])
        
        if not subnets['Subnets']:
            print("❌ No subnets found in VPC")
            return None
        
        subnet_id = subnets['Subnets'][0]['SubnetId']
        print(f"✅ Using subnet: {subnet_id}")
        
        # Get or create security group
        security_groups = ec2.describe_security_groups(Filters=[
            {'Name': 'vpc-id', 'Values': [vpc_id]},
            {'Name': 'group-name', 'Values': ['ses-lambda-sg']}
        ])
        
        if not security_groups['SecurityGroups']:
            # Create security group
            sg_response = ec2.create_security_group(
                GroupName='ses-lambda-sg',
                Description='Security group for SES Lambda in VPC',
                VpcId=vpc_id
            )
            sg_id = sg_response['GroupId']
            
            # Add outbound HTTPS rule
            ec2.authorize_security_group_egress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }]
            )
            print(f"✅ Created security group: {sg_id}")
        else:
            sg_id = security_groups['SecurityGroups'][0]['GroupId']
            print(f"✅ Using security group: {sg_id}")
        
        # Create VPC endpoint
        endpoint_response = ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName=f'com.amazonaws.{REGION}.execute-api',
            VpcEndpointType='Interface',
            SubnetIds=[subnet_id],
            SecurityGroupIds=[sg_id],
            PrivateDnsEnabled=True,
            TagSpecifications=[{
                'ResourceType': 'vpc-endpoint',
                'Tags': [
                    {'Key': 'Name', 'Value': 'ses-api-gateway-endpoint'},
                    {'Key': 'Purpose', 'Value': 'Private API Gateway Access'}
                ]
            }]
        )
        
        vpc_endpoint_id = endpoint_response['VpcEndpoint']['VpcEndpointId']
        print(f"✅ Created VPC Endpoint: {vpc_endpoint_id}")
        
        return vpc_endpoint_id
        
    except Exception as e:
        print(f"❌ Error creating VPC endpoint: {e}")
        return None

def update_api_gateway_policy(api_id, vpc_endpoint_id):
    """Update API Gateway resource policy to allow VPC endpoint access"""
    
    print(f"\n" + "="*80)
    print(f"🔧 UPDATING API GATEWAY POLICY")
    print("="*80)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        # Create resource policy that allows VPC endpoint access
        resource_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "execute-api:Invoke",
                    "Resource": f"arn:aws-us-gov:execute-api:{REGION}:*:{api_id}/*",
                    "Condition": {
                        "StringEquals": {
                            "aws:sourceVpce": vpc_endpoint_id
                        }
                    }
                }
            ]
        }
        
        # Update API Gateway with resource policy
        apigateway.update_rest_api(
            restApiId=api_id,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/policy',
                    'value': json.dumps(resource_policy)
                }
            ]
        )
        
        print(f"✅ Updated API Gateway resource policy")
        print(f"   Allows access from VPC endpoint: {vpc_endpoint_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating API Gateway policy: {e}")
        return False

def redeploy_api(api_id):
    """Redeploy API Gateway to apply changes"""
    
    print(f"\n" + "="*80)
    print(f"🔧 REDEPLOYING API GATEWAY")
    print("="*80)
    
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Enable VPC endpoint access'
        )
        
        print(f"✅ API Gateway redeployed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error redeploying API Gateway: {e}")
        return False

def get_access_urls(api_id, vpc_endpoint_id):
    """Get access URLs and instructions"""
    
    print(f"\n" + "="*80)
    print(f"🌐 ACCESS INFORMATION")
    print("="*80)
    
    # Standard API Gateway URL (works from within VPC with private DNS)
    standard_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/prod"
    
    # VPC endpoint URL (works from anywhere with VPC endpoint access)
    vpc_endpoint_url = f"https://{api_id}-{vpc_endpoint_id}.execute-api.{REGION}.vpce.amazonaws.com/prod"
    
    print(f"📋 Access URLs:")
    print(f"   1. From within VPC (with private DNS):")
    print(f"      {standard_url}")
    print(f"   2. From anywhere (via VPC endpoint):")
    print(f"      {vpc_endpoint_url}")
    
    print(f"\n📋 Web UI URLs:")
    print(f"   1. From within VPC:")
    print(f"      {standard_url}/")
    print(f"   2. From anywhere:")
    print(f"      {vpc_endpoint_url}/")
    
    print(f"\n📋 Testing Commands:")
    print(f"   # Test from within VPC:")
    print(f"   curl -I {standard_url}/")
    print(f"   curl {standard_url}/contacts?limit=1")
    print(f"")
    print(f"   # Test from anywhere (if you have VPC endpoint access):")
    print(f"   curl -I {vpc_endpoint_url}/")
    print(f"   curl {vpc_endpoint_url}/contacts?limit=1")
    
    return standard_url, vpc_endpoint_url

def main():
    """Main function"""
    
    print("🚀 SETTING UP PRIVATE API GATEWAY ACCESS")
    print("="*80)
    print()
    print("This script will configure VPC endpoints and policies to allow")
    print("access to your private API Gateway from within the VPC.")
    print()
    
    # Step 1: Check current setup
    vpc_id, api_id, vpc_endpoint_id = get_current_setup()
    
    if not vpc_id or not api_id:
        print("\n❌ Cannot proceed - missing VPC or API Gateway")
        return
    
    # Step 2: Create VPC endpoint if missing
    if not vpc_endpoint_id:
        print(f"\n🔧 Creating VPC endpoint for API Gateway access...")
        vpc_endpoint_id = create_vpc_endpoint(vpc_id)
        
        if not vpc_endpoint_id:
            print("\n❌ Failed to create VPC endpoint")
            return
    
    # Step 3: Update API Gateway policy
    print(f"\n🔧 Updating API Gateway resource policy...")
    policy_success = update_api_gateway_policy(api_id, vpc_endpoint_id)
    
    if not policy_success:
        print("\n❌ Failed to update API Gateway policy")
        return
    
    # Step 4: Redeploy API
    print(f"\n🔧 Redeploying API Gateway...")
    deploy_success = redeploy_api(api_id)
    
    if not deploy_success:
        print("\n❌ Failed to redeploy API Gateway")
        return
    
    # Step 5: Provide access information
    time.sleep(5)  # Wait for deployment to complete
    standard_url, vpc_endpoint_url = get_access_urls(api_id, vpc_endpoint_id)
    
    print(f"\n✅ SETUP COMPLETE!")
    print(f"="*80)
    print(f"Your private API Gateway is now configured for VPC access.")
    print(f"")
    print(f"To access the web UI:")
    print(f"1. From within the VPC: {standard_url}/")
    print(f"2. From anywhere with VPC endpoint access: {vpc_endpoint_url}/")
    print(f"")
    print(f"Note: You'll need to be connected to the VPC or have")
    print(f"VPC endpoint access to use these URLs.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


