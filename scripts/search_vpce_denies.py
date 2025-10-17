#!/usr/bin/env python3
"""
Search VPC Flow Logs for Denies to API Gateway VPCE Endpoints
Helps troubleshoot connectivity issues to private API Gateway endpoints
"""

import boto3
import json
from datetime import datetime, timedelta
import sys
from collections import defaultdict

REGION = 'us-gov-west-1'

def get_api_gateway_vpce():
    """Find API Gateway VPC Endpoints"""
    ec2 = boto3.client('ec2', region_name=REGION)
    
    print("=" * 80)
    print("🔍 Finding API Gateway VPC Endpoints")
    print("=" * 80)
    
    try:
        # Get VPC endpoints for API Gateway
        response = ec2.describe_vpc_endpoints(
            Filters=[
                {
                    'Name': 'service-name',
                    'Values': [f'com.amazonaws.{REGION}.execute-api']
                }
            ]
        )
        
        vpce_list = response.get('VpcEndpoints', [])
        
        if not vpce_list:
            print("⚠️  No API Gateway VPC Endpoints found")
            print("💡 You might be using public API Gateway (not private/VPC)")
            return []
        
        print(f"\n✅ Found {len(vpce_list)} API Gateway VPC Endpoint(s):\n")
        
        vpce_info = []
        for idx, vpce in enumerate(vpce_list, 1):
            vpce_id = vpce['VpcEndpointId']
            vpc_id = vpce['VpcId']
            state = vpce['State']
            subnet_ids = vpce.get('SubnetIds', [])
            network_interfaces = vpce.get('NetworkInterfaceIds', [])
            
            print(f"{idx}. VPC Endpoint ID: {vpce_id}")
            print(f"   VPC ID: {vpc_id}")
            print(f"   State: {state}")
            print(f"   Subnets: {len(subnet_ids)}")
            print(f"   Network Interfaces: {len(network_interfaces)}")
            
            # Get ENI details and IPs
            eni_ips = []
            for eni_id in network_interfaces:
                try:
                    eni_response = ec2.describe_network_interfaces(
                        NetworkInterfaceIds=[eni_id]
                    )
                    for eni in eni_response['NetworkInterfaces']:
                        private_ip = eni.get('PrivateIpAddress')
                        if private_ip:
                            eni_ips.append(private_ip)
                            print(f"   IP: {private_ip} (ENI: {eni_id})")
                except Exception as e:
                    print(f"   ⚠️  Could not get ENI details: {str(e)}")
            
            vpce_info.append({
                'vpce_id': vpce_id,
                'vpc_id': vpc_id,
                'state': state,
                'ips': eni_ips,
                'eni_ids': network_interfaces
            })
            print()
        
        return vpce_info
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def get_flow_log_groups(vpc_id):
    """Get CloudWatch Log Groups for VPC Flow Logs"""
    ec2 = boto3.client('ec2', region_name=REGION)
    
    print("🔍 Finding VPC Flow Logs...")
    
    try:
        response = ec2.describe_flow_logs(
            Filters=[
                {'Name': 'resource-id', 'Values': [vpc_id]}
            ]
        )
        
        flow_logs = response.get('FlowLogs', [])
        
        if not flow_logs:
            print(f"⚠️  No VPC Flow Logs configured for VPC {vpc_id}")
            print("💡 You need to enable VPC Flow Logs to CloudWatch first")
            return []
        
        log_groups = []
        for flow_log in flow_logs:
            if flow_log.get('LogDestinationType') == 'cloud-watch-logs':
                log_group = flow_log.get('LogGroupName')
                if log_group:
                    log_groups.append(log_group)
                    print(f"✅ Found Flow Log: {log_group}")
        
        return log_groups
    
    except Exception as e:
        print(f"❌ Error getting flow logs: {str(e)}")
        return []

def search_flow_logs_for_denies(log_group_name, target_ips, hours=1):
    """Search VPC Flow Logs for REJECT actions to target IPs"""
    logs_client = boto3.client('logs', region_name=REGION)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    print(f"\n🔍 Searching Flow Logs for REJECT actions...")
    print(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Target IPs: {', '.join(target_ips)}")
    
    denies = []
    
    try:
        # Build filter pattern for REJECTs to target IPs
        # VPC Flow Log format: account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
        filter_pattern = 'REJECT'
        
        print(f"\n📊 Querying CloudWatch Logs...")
        
        events = []
        next_token = None
        
        while True:
            params = {
                'logGroupName': log_group_name,
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'filterPattern': filter_pattern
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            response = logs_client.filter_log_events(**params)
            
            events.extend(response.get('events', []))
            next_token = response.get('nextToken')
            
            if not next_token:
                break
        
        print(f"✅ Found {len(events)} REJECT events total")
        
        # Parse flow log entries
        for event in events:
            message = event['message'].strip()
            fields = message.split()
            
            if len(fields) >= 13:
                # Parse VPC Flow Log fields
                # 0:version 1:account-id 2:interface-id 3:srcaddr 4:dstaddr 5:srcport 6:dstport 
                # 7:protocol 8:packets 9:bytes 10:start 11:end 12:action 13:log-status
                
                version = fields[0] if len(fields) > 0 else ''
                interface_id = fields[2] if len(fields) > 2 else ''
                src_addr = fields[3] if len(fields) > 3 else ''
                dst_addr = fields[4] if len(fields) > 4 else ''
                src_port = fields[5] if len(fields) > 5 else ''
                dst_port = fields[6] if len(fields) > 6 else ''
                protocol = fields[7] if len(fields) > 7 else ''
                action = fields[12] if len(fields) > 12 else ''
                
                # Check if destination is one of our VPCE IPs
                if dst_addr in target_ips and action == 'REJECT':
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    
                    denies.append({
                        'timestamp': timestamp,
                        'src_addr': src_addr,
                        'dst_addr': dst_addr,
                        'src_port': src_port,
                        'dst_port': dst_port,
                        'protocol': protocol,
                        'interface_id': interface_id,
                        'message': message
                    })
        
        return denies
    
    except Exception as e:
        print(f"❌ Error searching flow logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def analyze_denies(denies):
    """Analyze and categorize deny events"""
    
    if not denies:
        print("\n✅ No REJECT events found for API Gateway VPCE endpoints!")
        print("💡 This means traffic is being ACCEPTED (good!)")
        return
    
    print(f"\n⚠️  Found {len(denies)} REJECT events to API Gateway VPCE")
    print("=" * 80)
    
    # Group by source IP
    by_source = defaultdict(list)
    by_port = defaultdict(int)
    by_protocol = defaultdict(int)
    
    for deny in denies:
        by_source[deny['src_addr']].append(deny)
        by_port[deny['dst_port']] += 1
        
        protocol_name = {
            '6': 'TCP',
            '17': 'UDP',
            '1': 'ICMP'
        }.get(deny['protocol'], f"Protocol {deny['protocol']}")
        
        by_protocol[protocol_name] += 1
    
    # Print summary
    print(f"\n📊 SUMMARY:")
    print(f"   Total Denies: {len(denies)}")
    print(f"   Unique Source IPs: {len(by_source)}")
    print(f"   Most Targeted Port: {max(by_port, key=by_port.get) if by_port else 'N/A'}")
    
    # Protocol breakdown
    print(f"\n📡 By Protocol:")
    for protocol, count in sorted(by_protocol.items(), key=lambda x: x[1], reverse=True):
        print(f"   {protocol}: {count} denies")
    
    # Port breakdown
    print(f"\n🔌 By Destination Port:")
    for port, count in sorted(by_port.items(), key=lambda x: x[1], reverse=True)[:10]:
        port_name = {
            '443': 'HTTPS',
            '80': 'HTTP',
            '22': 'SSH',
            '3306': 'MySQL',
            '5432': 'PostgreSQL'
        }.get(port, f'Port {port}')
        print(f"   {port_name}: {count} denies")
    
    # Top sources
    print(f"\n🌐 Top Source IPs:")
    for src_ip, events in sorted(by_source.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"   {src_ip}: {len(events)} denies")
    
    # Show recent denies
    print(f"\n📋 Recent REJECT Events (Last 10):")
    print("=" * 80)
    
    for deny in sorted(denies, key=lambda x: x['timestamp'], reverse=True)[:10]:
        print(f"\n⏰ {deny['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Source: {deny['src_addr']}:{deny['src_port']}")
        print(f"   Destination: {deny['dst_addr']}:{deny['dst_port']}")
        
        protocol_name = {
            '6': 'TCP',
            '17': 'UDP',
            '1': 'ICMP'
        }.get(deny['protocol'], f"Protocol {deny['protocol']}")
        
        port_name = {
            '443': 'HTTPS',
            '80': 'HTTP'
        }.get(deny['dst_port'], deny['dst_port'])
        
        print(f"   Protocol: {protocol_name}")
        print(f"   Port: {port_name}")
        print(f"   Interface: {deny['interface_id']}")
    
    # Recommendations
    print(f"\n" + "=" * 80)
    print(f"💡 RECOMMENDATIONS:")
    print(f"=" * 80)
    
    if '443' in by_port or '80' in by_port:
        print(f"⚠️  HTTPS/HTTP traffic is being REJECTED!")
        print(f"   Check:")
        print(f"   1. Security Group on VPCE allows inbound on port 443")
        print(f"   2. Network ACLs allow traffic")
        print(f"   3. Route tables are configured correctly")
    
    if len(by_source) > 0:
        print(f"\n📍 Check these source IPs:")
        for src_ip in list(by_source.keys())[:5]:
            print(f"   - {src_ip}")
        print(f"   Are these your Lambda functions or expected sources?")

def main():
    """Main function"""
    
    hours = 1
    if len(sys.argv) > 1:
        try:
            hours = int(sys.argv[1])
        except ValueError:
            print("⚠️  Invalid hours value, using default (1 hour)")
    
    print(f"⏰ Searching last {hours} hour(s) of VPC Flow Logs\n")
    
    # Get API Gateway VPC Endpoints
    vpce_info = get_api_gateway_vpce()
    
    if not vpce_info:
        print("\n💡 If using public API Gateway, VPC Flow Logs don't apply")
        print("   Your API URL suggests public API Gateway (execute-api endpoint)")
        return
    
    all_denies = []
    
    for vpce in vpce_info:
        vpc_id = vpce['vpc_id']
        vpce_id = vpce['vpce_id']
        target_ips = vpce['ips']
        
        if not target_ips:
            print(f"\n⚠️  No IPs found for {vpce_id}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"Searching Flow Logs for VPC {vpc_id}")
        print(f"{'=' * 80}")
        
        # Get flow log groups for this VPC
        log_groups = get_flow_log_groups(vpc_id)
        
        if not log_groups:
            continue
        
        # Search each log group
        for log_group in log_groups:
            print(f"\n📋 Searching log group: {log_group}")
            denies = search_flow_logs_for_denies(log_group, target_ips, hours)
            all_denies.extend(denies)
    
    # Analyze all denies
    print(f"\n{'=' * 80}")
    print(f"📊 ANALYSIS RESULTS")
    print(f"{'=' * 80}")
    analyze_denies(all_denies)
    
    # Save to file option
    if all_denies:
        print(f"\n{'=' * 80}")
        save = input("\n💾 Save results to file? (y/n): ").strip().lower()
        
        if save == 'y':
            filename = f"vpce_denies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump([{
                    'timestamp': d['timestamp'].isoformat(),
                    'src_addr': d['src_addr'],
                    'dst_addr': d['dst_addr'],
                    'src_port': d['src_port'],
                    'dst_port': d['dst_port'],
                    'protocol': d['protocol'],
                    'interface_id': d['interface_id']
                } for d in all_denies], f, indent=2)
            
            print(f"✅ Saved to {filename}")

if __name__ == '__main__':
    try:
        main()
        print("\n" + "=" * 80)
        print("✅ Search Complete!")
        print("=" * 80)
        print("\n💡 Usage: python search_vpce_denies.py [hours]")
        print("   Example: python search_vpce_denies.py 24")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

