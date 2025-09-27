# VPC Private SMTP API Gateway Email Sender

Secure SMTP email sending solution with private API Gateway in VPC, Lambda, DynamoDB, and attachment support with enhanced network security.

## Architecture

- **Private VPC**: Isolated network environment for SMTP operations
- **Private API Gateway**: Accessible only through VPC endpoints
- **Lambda in VPC**: SMTP email processing with VPC security
- **VPC Endpoints**: Secure access to DynamoDB service
- **SMTP Relay**: External SMTP servers (Gmail, Outlook, custom)
- **Security Groups**: Network-level access control

## Security Features

### Network Isolation
- Private API Gateway with VPC endpoint access only
- Lambda functions deployed in private subnets
- No direct internet access to API endpoints
- Secure SMTP communication through VPC

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
- VPC endpoints for DynamoDB and API Gateway

### 2. Create DynamoDB Tables
```bash
python dynamodb_table_setup.py      # EmailContacts table
python dynamodb_campaigns_table.py  # EmailCampaigns table
```

### 3. Deploy Private SMTP API Gateway
1. Update `YOUR_ACCOUNT_ID` in `deploy_vpc_smtp_api.py`
2. Create IAM role with VPC and DynamoDB permissions
3. Run: `python deploy_vpc_smtp_api.py`

### 4. Setup Client Access
```bash
python vpc_client_setup.py
```

Creates public subnet and EC2 access for the private API.

## VPC Configuration

### Network Layout
```
VPC (10.0.0.0/16)
├── Private Subnet (10.0.1.0/24)
│   ├── Lambda Functions (SMTP)
│   └── VPC Endpoints
└── Public Subnet (10.0.2.0/24)
    └── Client EC2 Instance
```

### VPC Endpoints
- **DynamoDB**: Gateway endpoint for contact storage
- **API Gateway**: Interface endpoint for private API access

### Security Groups
- **Lambda SG**: Outbound HTTPS (443) for DynamoDB, SMTP (587/465) for email
- **Client SG**: Inbound SSH (22), HTTP (80), HTTPS (443)

## SMTP Configuration

### Supported SMTP Servers
- **Gmail**: smtp.gmail.com:587 (TLS)
- **Outlook**: smtp-mail.outlook.com:587 (TLS)
- **Custom SMTP**: Any SMTP server accessible from VPC

### Environment Variables
```python
Environment={
    'Variables': {
        'VPC_ENABLED': 'true',
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SMTP_USE_TLS': 'true'
    }
}
```

### SMTP Security
- TLS encryption for SMTP connections
- App passwords for Gmail authentication
- Secure credential storage in Lambda environment
- Network isolation for SMTP traffic

## API Endpoints

### POST /smtp-campaign
Send bulk SMTP email campaign with attachments
```json
{
  "subject": "VPC Secure Email",
  "body": "<h1>Hello {{first_name}}</h1>",
  "campaign_name": "VPC SMTP Campaign",
  "from_email": "sender@domain.com",
  "smtp_server": "smtp.gmail.com",
  "smtp_username": "user@gmail.com",
  "smtp_password": "app-password",
  "attachments": [...]
}
```

### GET /campaign-status/{campaign_id}
Get real-time campaign progress with VPC indicators

### GET /contacts
Retrieve contacts from DynamoDB via VPC endpoint

### POST /contacts
Add contacts to DynamoDB via VPC endpoint

## Lambda VPC Configuration

### VPC Settings
```python
VpcConfig={
    'SubnetIds': ['subnet-private-smtp'],
    'SecurityGroupIds': ['sg-lambda-smtp-vpc']
}
```

### Security Group Rules
```bash
# Outbound rules for Lambda
- HTTPS (443) to 0.0.0.0/0  # DynamoDB VPC endpoint
- SMTP (587) to 0.0.0.0/0   # SMTP servers
- SMTPS (465) to 0.0.0.0/0  # SMTP SSL
```

## Attachment Handling

### VPC SMTP Attachments
- Base64 encoding for file transfer
- MIME multipart message construction
- Support for any file type
- Size limits based on SMTP server (typically 25MB)

### Security Considerations
- Files processed within VPC boundaries
- No external file storage required
- Encrypted transmission via SMTP TLS
- Memory-based attachment processing

## Real-Time Progress Tracking

### Campaign Status Flow
1. **Pending**: Campaign created in VPC
2. **In Progress**: SMTP emails being sent from VPC
3. **Completed**: All emails processed
4. **Failed**: Campaign encountered errors

### VPC-Specific Tracking
- VPC endpoint usage indicators
- SMTP server connectivity status
- Network isolation confirmation
- DynamoDB VPC endpoint metrics

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
- **VPC Isolation**: Complete network isolation for email operations
- **Encrypted SMTP**: TLS encryption for all SMTP communications
- **Private Endpoints**: VPC endpoints for AWS service access

### Data Security
- **In-Transit Encryption**: HTTPS/TLS for all communications
- **At-Rest Encryption**: DynamoDB encryption enabled
- **Secure SMTP**: App passwords and TLS for email sending
- **Network Monitoring**: VPC Flow Logs and CloudWatch

## Monitoring and Logging

### VPC-Specific Monitoring
- VPC Flow Logs for network traffic
- Lambda execution metrics in VPC
- SMTP connection success/failure rates
- DynamoDB VPC endpoint usage

### SMTP Monitoring
- Email delivery success rates
- SMTP server response times
- Authentication failure tracking
- Attachment processing metrics

## Cost Optimization

### VPC Costs
- Interface endpoints: $0.01/hour per endpoint
- NAT Gateway: Not required (no internet access needed)
- Data processing charges for VPC endpoints

### SMTP Costs
- No AWS SES charges (using external SMTP)
- SMTP server costs (if using paid service)
- Lambda execution time in VPC

## Troubleshooting

### VPC Connectivity Issues
**Lambda Timeout in VPC:**
- Check VPC endpoint connectivity
- Verify security group rules for SMTP ports
- Ensure DynamoDB VPC endpoint is accessible

**SMTP Connection Failures:**
- Verify SMTP server accessibility from VPC
- Check security group outbound rules (587, 465)
- Validate SMTP credentials and authentication

**API Gateway Access Denied:**
- Confirm VPC endpoint policy configuration
- Verify request originates from VPC
- Check resource policy restrictions

### Network Testing
```bash
# Test SMTP connectivity from VPC
telnet smtp.gmail.com 587

# Test DynamoDB VPC endpoint
aws dynamodb list-tables --endpoint-url https://dynamodb.us-gov-west-1.amazonaws.com

# Test API Gateway VPC endpoint
curl -v https://api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts
```

## Compliance and Governance

### Network Compliance
- Private network architecture for sensitive email operations
- No internet gateway for Lambda subnets
- Encrypted communication channels (HTTPS, TLS)
- Complete network access logging

### Email Compliance
- SMTP authentication and encryption
- Audit trail for all email operations
- Contact data protection in VPC
- Secure attachment handling

## Advantages over Public SMTP

- **Enhanced Security**: Complete network isolation
- **Compliance Ready**: Meets strict security requirements
- **Audit Trail**: Complete logging and monitoring
- **Flexible SMTP**: Use any SMTP provider securely
- **Cost Control**: No AWS SES dependency
- **Attachment Support**: Full file attachment capability

This VPC-based SMTP solution provides maximum security for email operations while maintaining flexibility to use any SMTP provider with full attachment support and real-time progress tracking.