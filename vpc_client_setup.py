import boto3
import json

def create_vpc_client_resources():
    """Create EC2 instance and resources to access private API Gateway"""
    
    ec2 = boto3.client('ec2', region_name='us-gov-west-1')
    
    # Get VPC info
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'tag:Name', 'Values': ['ses-email-vpc']}])
    if not vpcs['Vpcs']:
        print("VPC not found. Run vpc_infrastructure.py first.")
        return None
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    
    try:
        # Create public subnet for client access
        public_subnet = ec2.create_subnet(
            VpcId=vpc_id,
            CidrBlock='10.0.2.0/24',
            AvailabilityZone='us-gov-west-1a',
            TagSpecifications=[
                {
                    'ResourceType': 'subnet',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-public-subnet'},
                        {'Key': 'Type', 'Value': 'Public'}
                    ]
                }
            ]
        )
        public_subnet_id = public_subnet['Subnet']['SubnetId']
        print(f"Created Public Subnet: {public_subnet_id}")
        
        # Create Internet Gateway
        igw = ec2.create_internet_gateway(
            TagSpecifications=[
                {
                    'ResourceType': 'internet-gateway',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-igw'}
                    ]
                }
            ]
        )
        igw_id = igw['InternetGateway']['InternetGatewayId']
        
        # Attach IGW to VPC
        ec2.attach_internet_gateway(
            InternetGatewayId=igw_id,
            VpcId=vpc_id
        )
        print(f"Created and attached Internet Gateway: {igw_id}")
        
        # Create route table for public subnet
        route_table = ec2.create_route_table(
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    'ResourceType': 'route-table',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-public-rt'}
                    ]
                }
            ]
        )
        rt_id = route_table['RouteTable']['RouteTableId']
        
        # Add route to Internet Gateway
        ec2.create_route(
            RouteTableId=rt_id,
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=igw_id
        )
        
        # Associate route table with public subnet
        ec2.associate_route_table(
            RouteTableId=rt_id,
            SubnetId=public_subnet_id
        )
        print(f"Created route table and associated with public subnet: {rt_id}")
        
        # Create security group for client EC2
        client_sg = ec2.create_security_group(
            GroupName='ses-client-sg',
            Description='Security group for SES API client',
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'ses-client-sg'}
                    ]
                }
            ]
        )
        client_sg_id = client_sg['GroupId']
        
        # Add inbound SSH rule
        ec2.authorize_security_group_ingress(
            GroupId=client_sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Restrict this in production
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        print(f"Created client security group: {client_sg_id}")
        
        # Create user data script for web server
        user_data = f"""#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd

# Create simple web interface
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>VPC SES Email Sender</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .alert {{ padding: 15px; background: #e7f3ff; border-left: 4px solid #2196F3; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>VPC SES Email Sender</h1>
        <div class="alert">
            <strong>Private API Access:</strong> This instance can access the private SES API Gateway within the VPC.
        </div>
        <p><strong>VPC ID:</strong> {vpc_id}</p>
        <p><strong>API Endpoint:</strong> Private VPC endpoint only</p>
        <p><strong>Access Method:</strong> Use VPC endpoint DNS names</p>
        
        <h2>Next Steps:</h2>
        <ol>
            <li>Upload the SES web UI to this server</li>
            <li>Configure API Gateway VPC endpoint URL</li>
            <li>Access the email sender interface</li>
        </ol>
        
        <h2>VPC Endpoint Information:</h2>
        <p>The API Gateway is accessible only through VPC endpoints. Use the VPC endpoint DNS name in your API calls.</p>
    </div>
</body>
</html>
EOF

# Set permissions
chown apache:apache /var/www/html/index.html
"""
        
        print("\nVPC Client Resources Summary:")
        print(f"- Public Subnet: {public_subnet_id}")
        print(f"- Internet Gateway: {igw_id}")
        print(f"- Route Table: {rt_id}")
        print(f"- Client Security Group: {client_sg_id}")
        print("\nTo create a client EC2 instance:")
        print(f"aws ec2 run-instances --image-id ami-xxxxxxxxx --instance-type t3.micro --subnet-id {public_subnet_id} --security-group-ids {client_sg_id} --associate-public-ip-address --user-data '{user_data}'")
        
        return {
            'vpc_id': vpc_id,
            'public_subnet_id': public_subnet_id,
            'igw_id': igw_id,
            'route_table_id': rt_id,
            'client_sg_id': client_sg_id,
            'user_data': user_data
        }
        
    except Exception as e:
        print(f"Error creating VPC client resources: {str(e)}")
        return None

if __name__ == "__main__":
    print("Creating VPC client access resources...")
    
    result = create_vpc_client_resources()
    
    if result:
        print("\nVPC client resources created successfully!")
        print("You can now launch an EC2 instance in the public subnet to access the private API Gateway.")
    else:
        print("Failed to create VPC client resources")