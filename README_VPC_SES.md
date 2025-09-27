# VPC Private AWS SES API Gateway Email Sender

Secure AWS SES email sending solution with private API Gateway in VPC, Lambda, DynamoDB, and attachment support with enhanced security.

## Architecture

- **Private VPC**: Isolated network environment
- **Private API Gateway**: Accessible only through VPC endpoints
- **Lambda in VPC**: SES email processing with VPC security
- **VPC Endpoints**: Secure access to AWS services (SES, DynamoDB)
- **DynamoDB**: Contact storage and campaign tracking
- **Security Groups**: Network-level access control

## Security Features

### Network Isolation
- Private API Gateway with VPC endpoint access only
- Lambda functions deployed in private subnets
- No direct internet access to API endpoints
- VPC endpoints for AWS service communication

### Access Control
- API Gateway resource policies restrict VPC access
- Security groups control network traffic
- IAM roles with minimal required permissions
- VPC endpoint policies for service access

## Setup Instructions

### 1. Create VPC Infrastructure
```bash
python vpc_infrastructure.py
```

Creates:
- Private VPC (10.0.0.0/16)
- Private subnet (10.0.1.0/24)
- Security groups for Lambda
- VPC endpoints for DynamoDB, SES, API Gateway

### 2. Create DynamoDB Tables
```bash
python dynamodb_table_setup.py      # EmailContacts table
python dynamodb_campaigns_table.py  # EmailCampaigns table
```

### 3. Deploy Private API Gateway
1. Update `YOUR_ACCOUNT_ID` in `deploy_vpc_ses_api.py`
2. Create IAM role with VPC and SES permissions
3. Run: `python deploy_vpc_ses_api.py`

### 4. Setup Client Access
```bash
python vpc_client_setup.py
```

Creates:
- Public subnet for client access
- Internet Gateway and routing
- Security groups for client EC2
- Web server setup script

### 5. Launch Client Instance
```bash
aws ec2 run-instances \
  --image-id ami-xxxxxxxxx \
  --instance-type t3.micro \
  --subnet-id subnet-xxxxxxxxx \
  --security-group-ids sg-xxxxxxxxx \
  --associate-public-ip-address \
  --user-data file://user-data.sh
```

## VPC Configuration

### Network Layout
```
VPC (10.0.0.0/16)
├── Private Subnet (10.0.1.0/24)
│   ├── Lambda Functions
│   └── VPC Endpoints
└── Public Subnet (10.0.2.0/24)
    └── Client EC2 Instance
```

### VPC Endpoints
- **DynamoDB**: Gateway endpoint for table access
- **SES**: Interface endpoint for email sending
- **API Gateway**: Interface endpoint for private API access

### Security Groups
- **Lambda SG**: Outbound HTTPS (443) for AWS services
- **Client SG**: Inbound SSH (22), HTTP (80), HTTPS (443)

## API Access Methods

### 1. VPC Endpoint Access
```javascript
// Use VPC endpoint DNS name
const API_BASE_URL = 'https://api-id-vpce-endpoint-id.execute-api.us-gov-west-1.vpce.amazonaws.com/prod';
```

### 2. Private DNS Resolution
```bash
# From within VPC
curl -X GET https://api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts
```

### 3. Client EC2 Access
- Deploy web UI to EC2 instance in public subnet
- Configure VPC endpoint URL in application
- Access through EC2 public IP or domain

## Lambda VPC Configuration

### VPC Settings
```python
VpcConfig={
    'SubnetIds': ['subnet-private-1', 'subnet-private-2'],
    'SecurityGroupIds': ['sg-lambda-vpc']
}
```

### Environment Variables
```python
Environment={
    'Variables': {
        'VPC_ENABLED': 'true'
    }
}
```

## API Gateway Resource Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:sourceVpce": "vpce-xxxxxxxxx"
        }
      }
    }
  ]
}
```

## Security Benefits

### Network Security
- **No Internet Exposure**: API not accessible from internet
- **VPC Isolation**: Complete network isolation
- **Endpoint Security**: Encrypted VPC endpoint communication
- **Traffic Control**: Security group rules control access

### Data Security
- **In-Transit Encryption**: HTTPS/TLS for all communications
- **At-Rest Encryption**: DynamoDB encryption enabled
- **Access Logging**: CloudTrail and VPC Flow Logs
- **Audit Trail**: Complete request/response logging

## Monitoring and Logging

### CloudWatch Metrics
- Lambda execution metrics
- API Gateway request metrics
- VPC endpoint usage metrics
- DynamoDB performance metrics

### VPC Flow Logs
```bash
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxxxxxxxx \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name VPCFlowLogs
```

### API Gateway Logging
- Access logs to CloudWatch
- Execution logs for debugging
- Request/response tracing
- Error rate monitoring

## Cost Optimization

### VPC Endpoints
- Gateway endpoints (DynamoDB): No additional cost
- Interface endpoints (SES, API Gateway): $0.01/hour per endpoint
- Data processing charges apply

### Lambda in VPC
- Cold start latency may be higher
- ENI creation/deletion overhead
- Consider provisioned concurrency for high-traffic

## Troubleshooting

### Common Issues

**Lambda Timeout in VPC:**
- Increase timeout settings
- Check VPC endpoint connectivity
- Verify security group rules

**API Gateway Access Denied:**
- Verify VPC endpoint policy
- Check resource policy configuration
- Confirm request source VPC

**VPC Endpoint Resolution:**
- Enable DNS resolution in VPC
- Check route table configuration
- Verify endpoint service availability

### Connectivity Testing
```bash
# Test VPC endpoint connectivity
nslookup vpce-xxxxxxxxx.execute-api.us-gov-west-1.vpce.amazonaws.com

# Test API access from VPC
curl -v https://api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts
```

## Compliance and Governance

### Network Compliance
- Private network architecture
- No internet gateway for Lambda subnets
- Encrypted communication channels
- Network access logging

### Access Governance
- IAM role-based access control
- VPC endpoint access policies
- Security group rule management
- Regular access reviews

This VPC-based solution provides enterprise-grade security for sensitive email operations while maintaining the scalability and reliability of AWS SES.