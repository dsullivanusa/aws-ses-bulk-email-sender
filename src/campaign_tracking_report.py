#!/usr/bin/env python3
"""
Campaign Tracking Report Generator
Query and display detailed campaign tracking information including:
- Campaign ID
- Campaign Name
- User who launched
- Date emails were sent
- Email addresses who received emails
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from datetime import datetime
from decimal import Decimal
import csv

class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types in JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_all_campaigns(region='us-gov-west-1'):
    """Retrieve all campaigns from DynamoDB"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    campaigns_table = dynamodb.Table('EmailCampaigns')
    
    print("🔍 Scanning EmailCampaigns table...")
    response = campaigns_table.scan()
    campaigns = response.get('Items', [])
    
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = campaigns_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        campaigns.extend(response.get('Items', []))
    
    print(f"✅ Found {len(campaigns)} campaigns\n")
    return campaigns

def get_campaign_by_id(campaign_id, region='us-gov-west-1'):
    """Get specific campaign by ID"""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    campaigns_table = dynamodb.Table('EmailCampaigns')
    
    response = campaigns_table.get_item(Key={'campaign_id': campaign_id})
    return response.get('Item')

def format_campaign_summary(campaign):
    """Format campaign data for display"""
    campaign_id = campaign.get('campaign_id', 'N/A')
    campaign_name = campaign.get('campaign_name', 'N/A')
    launched_by = campaign.get('launched_by', 'Unknown')
    created_at = campaign.get('created_at', 'N/A')
    sent_at = campaign.get('sent_at', 'Not yet sent')
    status = campaign.get('status', 'unknown')
    
    total_contacts = campaign.get('total_contacts', 0)
    sent_count = campaign.get('sent_count', 0)
    failed_count = campaign.get('failed_count', 0)
    
    target_contacts = campaign.get('target_contacts', [])
    filter_description = campaign.get('filter_description', 'No filter')
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign_name,
        'launched_by': launched_by,
        'created_at': created_at,
        'sent_at': sent_at,
        'status': status,
        'total_contacts': total_contacts,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'target_emails': target_contacts,
        'filter_description': filter_description
    }

def display_campaign_table(campaigns):
    """Display campaigns in table format"""
    if not campaigns:
        print("No campaigns found.")
        return
    
    print("="*120)
    print(f"{'ID':<20} {'Campaign Name':<30} {'Launched By':<25} {'Status':<12} {'Sent':<8} {'Total':<8}")
    print("="*120)
    
    for campaign in sorted(campaigns, key=lambda x: x.get('created_at', ''), reverse=True):
        cid = campaign.get('campaign_id', 'N/A')[:18]
        name = campaign.get('campaign_name', 'N/A')[:28]
        user = campaign.get('launched_by', 'Unknown')[:23]
        status = campaign.get('status', 'unknown')[:10]
        sent = campaign.get('sent_count', 0)
        total = campaign.get('total_contacts', 0)
        
        print(f"{cid:<20} {name:<30} {user:<25} {status:<12} {sent:<8} {total:<8}")
    
    print("="*120)

def display_campaign_detail(campaign):
    """Display detailed campaign information"""
    if not campaign:
        print("Campaign not found.")
        return
    
    summary = format_campaign_summary(campaign)
    
    print("\n" + "="*80)
    print("📊 CAMPAIGN DETAILS")
    print("="*80)
    print(f"Campaign ID:       {summary['campaign_id']}")
    print(f"Campaign Name:     {summary['campaign_name']}")
    print(f"Launched By:       {summary['launched_by']}")
    print(f"Created At:        {summary['created_at']}")
    print(f"Sent At:           {summary['sent_at']}")
    print(f"Status:            {summary['status']}")
    print(f"-"*80)
    print(f"Target Filter:     {summary['filter_description']}")
    print(f"Total Contacts:    {summary['total_contacts']}")
    print(f"Successfully Sent: {summary['sent_count']}")
    print(f"Failed:            {summary['failed_count']}")
    print(f"-"*80)
    
    print(f"\n📧 RECIPIENT EMAIL ADDRESSES ({len(summary['target_emails'])} total):")
    print("-"*80)
    
    if summary['target_emails']:
        for idx, email in enumerate(summary['target_emails'][:50], 1):  # Show first 50
            print(f"  {idx:3d}. {email}")
        
        if len(summary['target_emails']) > 50:
            print(f"\n  ... and {len(summary['target_emails']) - 50} more")
    else:
        print("  No email addresses recorded")
    
    print("="*80 + "\n")

def export_campaign_to_csv(campaign, filename=None):
    """Export campaign recipient list to CSV"""
    if not campaign:
        print("Campaign not found.")
        return
    
    if not filename:
        campaign_id = campaign.get('campaign_id', 'unknown')
        filename = f"campaign_{campaign_id}_recipients.csv"
    
    summary = format_campaign_summary(campaign)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header with metadata
        writer.writerow(['Campaign Report'])
        writer.writerow(['Campaign ID', summary['campaign_id']])
        writer.writerow(['Campaign Name', summary['campaign_name']])
        writer.writerow(['Launched By', summary['launched_by']])
        writer.writerow(['Created At', summary['created_at']])
        writer.writerow(['Sent At', summary['sent_at']])
        writer.writerow(['Status', summary['status']])
        writer.writerow(['Total Recipients', summary['total_contacts']])
        writer.writerow(['Successfully Sent', summary['sent_count']])
        writer.writerow(['Failed', summary['failed_count']])
        writer.writerow([])
        
        # Recipient list
        writer.writerow(['Recipient Email Addresses'])
        writer.writerow(['#', 'Email Address'])
        
        for idx, email in enumerate(summary['target_emails'], 1):
            writer.writerow([idx, email])
    
    print(f"✅ Exported to: {filename}")
    return filename

def export_email_list_only(campaign, filename=None):
    """Export just the email addresses list to CSV"""
    if not campaign:
        print("Campaign not found.")
        return None
    
    if not filename:
        campaign_id = campaign.get('campaign_id', 'unknown')
        filename = f"campaign_{campaign_id}_email_list.csv"
    
    summary = format_campaign_summary(campaign)
    recipients = summary['target_emails']
    
    if not recipients:
        print("⚠️  No email addresses recorded for this campaign")
        return None
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Simple header
        writer.writerow([f"Email Addresses for Campaign: {summary['campaign_name']}"])
        writer.writerow([f"Campaign ID: {summary['campaign_id']}"])
        writer.writerow([f"Total Recipients: {len(recipients)}"])
        writer.writerow([f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        writer.writerow([])  # Blank row
        
        # Column header
        writer.writerow(['Email Address'])
        
        # Email addresses only (one per row)
        for email in recipients:
            writer.writerow([email])
    
    print(f"✅ Exported {len(recipients)} email addresses to: {filename}")
    return filename

def export_all_campaigns_to_csv(campaigns, filename='all_campaigns_summary.csv'):
    """Export all campaigns summary to CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Campaign ID',
            'Campaign Name',
            'Launched By',
            'Created At',
            'Sent At',
            'Status',
            'Filter Description',
            'Total Contacts',
            'Successfully Sent',
            'Failed',
            'Recipient Count'
        ])
        
        # Data
        for campaign in sorted(campaigns, key=lambda x: x.get('created_at', ''), reverse=True):
            summary = format_campaign_summary(campaign)
            writer.writerow([
                summary['campaign_id'],
                summary['campaign_name'],
                summary['launched_by'],
                summary['created_at'],
                summary['sent_at'],
                summary['status'],
                summary['filter_description'],
                summary['total_contacts'],
                summary['sent_count'],
                summary['failed_count'],
                len(summary['target_emails'])
            ])
    
    print(f"✅ Exported {len(campaigns)} campaigns to: {filename}")
    return filename

def interactive_menu():
    """Interactive menu for campaign tracking"""
    region = 'us-gov-west-1'
    
    while True:
        print("\n" + "="*80)
        print("📊 CAMPAIGN TRACKING SYSTEM")
        print("="*80)
        print("1. View All Campaigns (Summary)")
        print("2. View Campaign Details (by ID)")
        print("3. View Recent Campaigns (last 10)")
        print("4. Export Campaign Recipients to CSV")
        print("5. Export Email List Only (Just Addresses)")
        print("6. Export All Campaigns Summary to CSV")
        print("7. Search Campaigns by Name")
        print("8. View Campaigns by Status")
        print("9. Change Region")
        print("10. Exit")
        print("="*80)
        
        choice = input("\nEnter your choice (1-10): ").strip()
        
        if choice == '1':
            campaigns = get_all_campaigns(region)
            display_campaign_table(campaigns)
        
        elif choice == '2':
            campaign_id = input("Enter Campaign ID: ").strip()
            campaign = get_campaign_by_id(campaign_id, region)
            display_campaign_detail(campaign)
        
        elif choice == '3':
            campaigns = get_all_campaigns(region)
            recent = sorted(campaigns, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            print("\n📅 10 Most Recent Campaigns:")
            display_campaign_table(recent)
        
        elif choice == '4':
            campaign_id = input("Enter Campaign ID: ").strip()
            campaign = get_campaign_by_id(campaign_id, region)
            if campaign:
                filename = input("Enter filename (or press Enter for default): ").strip()
                export_campaign_to_csv(campaign, filename if filename else None)
        
        elif choice == '5':
            campaign_id = input("Enter Campaign ID: ").strip()
            campaign = get_campaign_by_id(campaign_id, region)
            if campaign:
                filename = input("Enter filename (or press Enter for default): ").strip()
                export_email_list_only(campaign, filename if filename else None)
        
        elif choice == '6':
            campaigns = get_all_campaigns(region)
            filename = input("Enter filename (or press Enter for default): ").strip()
            export_all_campaigns_to_csv(campaigns, filename if filename else 'all_campaigns_summary.csv')
        
        elif choice == '7':
            search_term = input("Enter campaign name (partial match): ").strip().lower()
            campaigns = get_all_campaigns(region)
            matching = [c for c in campaigns if search_term in c.get('campaign_name', '').lower()]
            print(f"\n🔍 Found {len(matching)} matching campaigns:")
            display_campaign_table(matching)
        
        elif choice == '8':
            status = input("Enter status (queued/sending/completed/failed): ").strip().lower()
            campaigns = get_all_campaigns(region)
            filtered = [c for c in campaigns if c.get('status', '').lower() == status]
            print(f"\n📊 Campaigns with status '{status}' ({len(filtered)} found):")
            display_campaign_table(filtered)
        
        elif choice == '9':
            region = input("Enter AWS region (e.g., us-gov-west-1): ").strip()
            print(f"✅ Region changed to: {region}")
        
        elif choice == '10':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")

def main():
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'list':
            campaigns = get_all_campaigns()
            display_campaign_table(campaigns)
        
        elif command == 'detail' and len(sys.argv) > 2:
            campaign_id = sys.argv[2]
            campaign = get_campaign_by_id(campaign_id)
            display_campaign_detail(campaign)
        
        elif command == 'export' and len(sys.argv) > 2:
            campaign_id = sys.argv[2]
            campaign = get_campaign_by_id(campaign_id)
            filename = sys.argv[3] if len(sys.argv) > 3 else None
            export_campaign_to_csv(campaign, filename)
        
        elif command == 'export-emails' and len(sys.argv) > 2:
            campaign_id = sys.argv[2]
            campaign = get_campaign_by_id(campaign_id)
            filename = sys.argv[3] if len(sys.argv) > 3 else None
            export_email_list_only(campaign, filename)
        
        elif command == 'export-all':
            campaigns = get_all_campaigns()
            filename = sys.argv[2] if len(sys.argv) > 2 else 'all_campaigns_summary.csv'
            export_all_campaigns_to_csv(campaigns, filename)
        
        else:
            print("Usage:")
            print("  python campaign_tracking_report.py                          # Interactive menu")
            print("  python campaign_tracking_report.py list                     # List all campaigns")
            print("  python campaign_tracking_report.py detail <id>              # Show campaign details")
            print("  python campaign_tracking_report.py export <id> [file]       # Export campaign recipients")
            print("  python campaign_tracking_report.py export-emails <id> [file]# Export email list only")
            print("  python campaign_tracking_report.py export-all [file]        # Export all campaigns")
    else:
        interactive_menu()

if __name__ == '__main__':
    main()

