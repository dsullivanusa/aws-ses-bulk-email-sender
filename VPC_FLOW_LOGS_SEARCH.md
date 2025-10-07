# 🔍 VPC Flow Logs Search for API Gateway VPCE

Search VPC Flow Logs to find denied traffic to API Gateway VPC Endpoints.

---

## 🚀 Quick Start

### Option 1: Automatic Search (Recommended)
Finds VPCE endpoints automatically and searches for denies:

```bash
python search_vpce_denies.py
```

Search last 24 hours:
```bash
python search_vpce_denies.py 24
```

### Option 2: Search by Specific IP
If you know the VPCE endpoint IP address:

```bash
# List available log groups first
python search_flow_logs_by_ip.py --list

# Search for denies to specific IP
python search_flow_logs_by_ip.py /aws/vpc/flowlogs 10.0.1.50 1 REJECT
```

---

## 📊 What You'll See

### If No Denies:
```
✅ No REJECT events found for API Gateway VPCE endpoints!
💡 This means traffic is being ACCEPTED (good!)
```

### If Denies Found:
```
⚠️  Found 15 REJECT events to API Gateway VPCE

📊 SUMMARY:
   Total Denies: 15
   Unique Source IPs: 3
   Most Targeted Port: 443

📡 By Protocol:
   TCP: 15 denies

🔌 By Destination Port:
   HTTPS (443): 12 denies
   HTTP (80): 3 denies

🌐 Top Source IPs:
   10.0.2.100: 8 denies
   10.0.3.50: 5 denies
   10.0.4.25: 2 denies

📋 Recent REJECT Events:

⏰ 2025-10-07 14:23:45
   Source: 10.0.2.100:54321
   Destination: 10.0.1.50:443 (HTTPS)
   Protocol: TCP
   Interface: eni-abc123

💡 RECOMMENDATIONS:
⚠️  HTTPS/HTTP traffic is being REJECTED!
   Check:
   1. Security Group on VPCE allows inbound on port 443
   2. Network ACLs allow traffic
   3. Route tables are configured correctly
```

---

## 🔧 Prerequisites

### 1. VPC Flow Logs Must Be Enabled
Enable VPC Flow Logs to CloudWatch:

```bash
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxxxx \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs \
  --deliver-logs-permission-arn arn:aws-us-gov:iam::ACCOUNT:role/flowlogsRole
```

### 2. CloudWatch Logs Permissions
Your AWS credentials need:
- `ec2:DescribeVpcEndpoints`
- `ec2:DescribeFlowLogs`
- `ec2:DescribeNetworkInterfaces`
- `logs:FilterLogEvents`
- `logs:DescribeLogGroups`

---

## 🎯 Common Use Cases

### Use Case 1: Lambda Can't Reach API Gateway
**Problem:** Lambda function getting connection timeout to private API

**Steps:**
1. Run: `python search_vpce_denies.py 1`
2. Look for denies from Lambda subnet IPs
3. Fix security group rules

### Use Case 2: Application Not Working
**Problem:** Application intermittently fails to call API

**Steps:**
1. Note application server IP
2. Run: `python search_flow_logs_by_ip.py /aws/vpc/flowlogs <app-server-ip> 24 REJECT`
3. Check if security groups blocking traffic

### Use Case 3: New VPCE Not Working
**Problem:** Just created VPCE, nothing can connect

**Steps:**
1. Run: `python search_vpce_denies.py 1`
2. Check all source IPs being denied
3. Update security group to allow those sources

---

## 🔍 Understanding VPC Flow Log Fields

Flow log format:
```
<version> <account-id> <interface-id> <srcaddr> <dstaddr> <srcport> <dstport> <protocol> <packets> <bytes> <start> <end> <action> <log-status>
```

Example:
```
2 123456789012 eni-abc123 10.0.2.100 10.0.1.50 54321 443 6 10 5000 1696680000 1696680060 REJECT OK
```

**Fields:**
- `srcaddr`: Source IP (who's trying to connect)
- `dstaddr`: Destination IP (VPCE endpoint IP)
- `srcport`: Source port
- `dstport`: Destination port (usually 443 for API Gateway)
- `protocol`: 6=TCP, 17=UDP, 1=ICMP
- `action`: ACCEPT or REJECT

---

## 📋 Troubleshooting

### "No API Gateway VPC Endpoints found"
**Cause:** You're using public API Gateway, not private VPCE

**Solution:** 
- This is normal! Your API URL `https://yi6ss4dsoe...` is public
- VPC Flow Logs don't apply to public API Gateway
- No action needed

### "No VPC Flow Logs configured"
**Cause:** Flow logs not enabled for the VPC

**Solution:** Enable VPC Flow Logs:
```bash
# Via Python
python enable_vpc_flow_logs.py

# Via AWS CLI
aws ec2 create-flow-logs --resource-type VPC --resource-ids vpc-xxxxx ...
```

### "Access Denied"
**Cause:** Missing IAM permissions

**Solution:** Add these permissions to your IAM user/role:
```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeVpcEndpoints",
    "ec2:DescribeFlowLogs",
    "ec2:DescribeNetworkInterfaces",
    "logs:FilterLogEvents",
    "logs:DescribeLogGroups"
  ],
  "Resource": "*"
}
```

---

## 💡 Quick Reference

### Find VPCE IPs:
```bash
aws ec2 describe-vpc-endpoints --filters "Name=service-name,Values=com.amazonaws.us-gov-west-1.execute-api"
```

### List Flow Log Groups:
```bash
python search_flow_logs_by_ip.py --list
```

### Search for ACCEPTS (successful connections):
```bash
python search_flow_logs_by_ip.py /aws/vpc/flowlogs 10.0.1.50 1 ACCEPT
```

### Search longer time period:
```bash
python search_vpce_denies.py 24  # Last 24 hours
python search_vpce_denies.py 168  # Last week
```

---

## 🎯 Your API Gateway

**URL:** `https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod`

**Type:** Public API Gateway (not VPC Endpoint)

**Note:** VPC Flow Logs only apply to **private** API Gateway with VPC Endpoints. Your API is public, so:
- ✅ Accessible from internet
- ✅ No VPC Flow Logs needed
- ✅ No VPCE required
- ✅ Security controlled by API Gateway resource policies

If you want to make it private with VPCE, you'd need to:
1. Create VPC Endpoint for execute-api
2. Update API Gateway to be PRIVATE
3. Add resource policy
4. Then these scripts would be useful!

---

**For now, your API is public and these scripts are not needed unless you create a private VPCE setup.**
