#!/usr/bin/env python3
"""
Search VPC Flow Logs by IP Address
Simpler script if you already know the VPCE endpoint IPs
"""

import boto3
from datetime import datetime, timedelta
import sys

REGION = 'us-gov-west-1'

def search_by_ip(log_group_name, target_ip, hours=1, action='REJECT'):
    """Search flow logs for specific IP and action"""
    
    logs_client = boto3.client('logs', region_name=REGION)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    print("=" * 80)
    print(f"🔍 VPC Flow Log Search")
    print("=" * 80)
    print(f"\n📋 Log Group: {log_group_name}")
    print(f"🎯 Target IP: {target_ip}")
    print(f"🚫 Action: {action}")
    print(f"⏰ Time Range: Last {hours} hour(s)")
    print(f"   From: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   To: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Search for flow logs with REJECT and target IP
        filter_pattern = f'{action}'
        
        print(f"\n🔍 Searching...")
        
        events = []
        next_token = None
        page = 0
        
        while True:
            page += 1
            params = {
                'logGroupName': log_group_name,
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'filterPattern': filter_pattern
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            response = logs_client.filter_log_events(**params)
            
            page_events = response.get('events', [])
            events.extend(page_events)
            
            print(f"   Page {page}: {len(page_events)} events")
            
            next_token = response.get('nextToken')
            if not next_token:
                break
        
        print(f"\n✅ Retrieved {len(events)} {action} events total")
        
        # Filter for our target IP
        matching_events = []
        for event in events:
            message = event['message']
            if target_ip in message:
                matching_events.append(event)
        
        print(f"🎯 {len(matching_events)} events involve IP {target_ip}\n")
        
        if not matching_events:
            print("✅ No REJECT events found for this IP!")
            return
        
        # Display results
        print("=" * 80)
        print(f"📊 REJECT EVENTS FOR {target_ip}")
        print("=" * 80)
        
        for idx, event in enumerate(matching_events[:20], 1):  # Show first 20
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            fields = event['message'].split()
            
            if len(fields) >= 13:
                src_addr = fields[3]
                dst_addr = fields[4]
                src_port = fields[5]
                dst_port = fields[6]
                protocol = fields[7]
                interface_id = fields[2]
                
                protocol_name = {
                    '6': 'TCP',
                    '17': 'UDP',
                    '1': 'ICMP'
                }.get(protocol, f'Protocol {protocol}')
                
                port_name = {
                    '443': 'HTTPS',
                    '80': 'HTTP',
                    '22': 'SSH'
                }.get(dst_port, dst_port)
                
                print(f"\n[{idx}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    From: {src_addr}:{src_port}")
                print(f"    To:   {dst_addr}:{dst_port} ({port_name})")
                print(f"    Protocol: {protocol_name}")
                print(f"    Interface: {interface_id}")
        
        if len(matching_events) > 20:
            print(f"\n... and {len(matching_events) - 20} more events")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def list_log_groups():
    """List all CloudWatch Log Groups for VPC Flow Logs"""
    logs_client = boto3.client('logs', region_name=REGION)
    
    print("📋 Available VPC Flow Log Groups:")
    print("=" * 80)
    
    try:
        response = logs_client.describe_log_groups()
        
        flow_log_groups = [lg for lg in response.get('logGroups', []) 
                           if 'flow' in lg['logGroupName'].lower() or 'vpc' in lg['logGroupName'].lower()]
        
        if not flow_log_groups:
            print("⚠️  No VPC Flow Log groups found")
            print("💡 Make sure VPC Flow Logs are enabled and logging to CloudWatch")
            return
        
        for idx, lg in enumerate(flow_log_groups, 1):
            name = lg['logGroupName']
            size = lg.get('storedBytes', 0)
            print(f"{idx}. {name}")
            print(f"   Size: {size / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python search_flow_logs_by_ip.py <log-group-name> <target-ip> [hours] [action]")
        print("\nExamples:")
        print("  python search_flow_logs_by_ip.py /aws/vpc/flowlogs 10.0.1.50 1 REJECT")
        print("  python search_flow_logs_by_ip.py /aws/vpc/flowlogs 10.0.1.50 24")
        print("\nTo list available log groups:")
        print("  python search_flow_logs_by_ip.py --list")
        sys.exit(1)
    
    if sys.argv[1] == '--list':
        list_log_groups()
        sys.exit(0)
    
    log_group = sys.argv[1]
    target_ip = sys.argv[2]
    hours = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    action = sys.argv[4] if len(sys.argv) > 4 else 'REJECT'
    
    search_by_ip(log_group, target_ip, hours, action)

