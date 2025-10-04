#!/usr/bin/env python3
"""
Get Campaign Recipients
Shows who received emails from a specific campaign
"""

import boto3
import json
from datetime import datetime

REGION = 'us-gov-west-1'

def get_campaign_recipients(campaign_id=None):
    """Get recipients for a campaign"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    campaigns_table = dynamodb.Table('EmailCampaigns')
    contacts_table = dynamodb.Table('EmailContacts')
    
    print("="*70)
    print("CAMPAIGN RECIPIENTS")
    print("="*70)
    print()
    
    # If no campaign_id provided, show recent campaigns
    if not campaign_id:
        print("📋 Recent Campaigns:")
        print("-" * 70)
        
        response = campaigns_table.scan(Limit=20)
        campaigns = sorted(response['Items'], 
                          key=lambda x: x.get('created_at', ''), 
                          reverse=True)
        
        if not campaigns:
            print("No campaigns found.")
            return
        
        for idx, campaign in enumerate(campaigns[:10], 1):
            created = campaign.get('created_at', 'Unknown')
            total = campaign.get('total_contacts', 0)
            sent = campaign.get('sent_count', 0)
            failed = campaign.get('failed_count', 0)
            filter_desc = campaign.get('filter_description', 'All Contacts')
            
            print(f"{idx}. {campaign.get('campaign_name', 'Unnamed')}")
            print(f"   ID: {campaign.get('campaign_id')}")
            print(f"   Created: {created}")
            print(f"   Filter: {filter_desc}")
            print(f"   Total: {total} | Sent: {sent} | Failed: {failed}")
            print()
        
        # Ask user to run again with specific campaign_id
        print("To see recipients for a specific campaign, run:")
        print(f"  python get_campaign_recipients.py CAMPAIGN_ID")
        print("\nExample:")
        if campaigns:
            example_id = campaigns[0].get('campaign_id')
            print(f"  python get_campaign_recipients.py {example_id}")
        
        return
    
    # Get specific campaign
    print(f"🔍 Looking up campaign: {campaign_id}")
    print("-" * 70)
    
    try:
        response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
        
        if 'Item' not in response:
            print(f"❌ Campaign not found: {campaign_id}")
            return
        
        campaign = response['Item']
        
        # Display campaign details
        print(f"\n📧 Campaign Details:")
        print(f"  Name: {campaign.get('campaign_name', 'Unnamed')}")
        print(f"  Subject: {campaign.get('subject', '')}")
        print(f"  Created: {campaign.get('created_at', 'Unknown')}")
        print(f"  Status: {campaign.get('status', 'Unknown')}")
        print(f"  Filter: {campaign.get('filter_description', 'All Contacts')}")
        
        # Check if campaign has target_contacts list
        if 'target_contacts' in campaign:
            # Campaign stores recipient list
            recipients = campaign['target_contacts']
            print(f"\n📋 Recipients ({len(recipients)} contacts):")
            print("-" * 70)
            
            for idx, email in enumerate(recipients, 1):
                # Get contact details
                try:
                    contact_response = contacts_table.get_item(Key={'email': email})
                    if 'Item' in contact_response:
                        contact = contact_response['Item']
                        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                        group = contact.get('group', '')
                        state = contact.get('state', '')
                        print(f"{idx:4}. {email:40} | {name:25} | {state:3} | {group}")
                    else:
                        print(f"{idx:4}. {email:40} | (Contact not found)")
                except Exception as e:
                    print(f"{idx:4}. {email:40} | Error: {str(e)}")
        else:
            # Campaign doesn't store recipient list - reconstruct from filter
            print(f"\n⚠️  Campaign doesn't store recipient list.")
            print(f"  Reconstructing based on filter criteria...")
            
            filter_type = campaign.get('filter_type')
            filter_values = campaign.get('filter_values', [])
            
            if not filter_type or not filter_values:
                print(f"\n  Filter: All Contacts")
                print(f"  Retrieving all contacts from DynamoDB...")
                
                contacts_response = contacts_table.scan()
                all_contacts = contacts_response['Items']
            else:
                print(f"\n  Filter Type: {filter_type}")
                print(f"  Filter Values: {', '.join(filter_values)}")
                print(f"  Retrieving matching contacts from DynamoDB...")
                
                # Scan and filter
                contacts_response = contacts_table.scan()
                all_contacts = [
                    c for c in contacts_response['Items']
                    if c.get(filter_type) in filter_values
                ]
            
            print(f"\n📋 Reconstructed Recipients ({len(all_contacts)} contacts):")
            print("-" * 70)
            
            for idx, contact in enumerate(all_contacts, 1):
                email = contact.get('email', '')
                name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                group = contact.get('group', '')
                state = contact.get('state', '')
                print(f"{idx:4}. {email:40} | {name:25} | {state:3} | {group}")
        
        # Stats
        print("\n" + "="*70)
        print("STATISTICS:")
        print("="*70)
        print(f"Total Targeted: {campaign.get('total_contacts', 0)}")
        print(f"Successfully Sent: {campaign.get('sent_count', 0)}")
        print(f"Failed: {campaign.get('failed_count', 0)}")
        print(f"Queued: {campaign.get('queued_count', 0)}")
        
        # Attachments
        if 'attachments' in campaign and campaign['attachments']:
            print(f"\n📎 Attachments: {len(campaign['attachments'])}")
            for idx, att in enumerate(campaign['attachments'], 1):
                size_kb = att.get('size', 0) / 1024
                print(f"  {idx}. {att.get('filename')} ({size_kb:.1f} KB)")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import sys
    
    campaign_id = sys.argv[1] if len(sys.argv) > 1 else None
    get_campaign_recipients(campaign_id)

