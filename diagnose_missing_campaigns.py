#!/usr/bin/env python3
"""Diagnose why campaigns are not showing up in Campaign History"""

import boto3
from decimal import Decimal
import json
from datetime import datetime

def convert_decimal(obj):
    """Convert Decimal to int/float for display"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def diagnose_campaigns():
    """Check all campaigns in DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
    campaigns_table = dynamodb.Table('EmailCampaigns')
    
    print("=" * 80)
    print("CAMPAIGN DIAGNOSIS - Scanning all campaigns")
    print("=" * 80)
    
    # Scan all campaigns
    all_campaigns = []
    last_key = None
    page = 0
    
    while True:
        page += 1
        scan_kwargs = {'Limit': 100}
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key
        
        response = campaigns_table.scan(**scan_kwargs)
        items = response.get('Items', [])
        all_campaigns.extend(items)
        
        print(f"\nPage {page}: Found {len(items)} campaigns")
        
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL CAMPAIGNS IN DATABASE: {len(all_campaigns)}")
    print(f"{'=' * 80}\n")
    
    # Categorize campaigns
    preview_campaigns = []
    missing_created_at = []
    valid_campaigns = []
    
    for campaign in all_campaigns:
        campaign_id = campaign.get('campaign_id', 'unknown')
        status = campaign.get('status', 'unknown')
        ctype = campaign.get('type', '')
        created_at = campaign.get('created_at', '')
        campaign_name = campaign.get('campaign_name', 'Unnamed')
        
        # Check if it's a preview
        if status == 'preview' or ctype == 'preview':
            preview_campaigns.append(campaign)
        # Check if missing created_at
        elif not created_at:
            missing_created_at.append(campaign)
        else:
            valid_campaigns.append(campaign)
    
    print(f"📊 CAMPAIGN BREAKDOWN:")
    print(f"   ✅ Valid campaigns (will show in history): {len(valid_campaigns)}")
    print(f"   ⚠️  Preview campaigns (filtered out): {len(preview_campaigns)}")
    print(f"   ❌ Missing created_at (will sort to end): {len(missing_created_at)}")
    
    # Show the 10 most recent valid campaigns
    print(f"\n{'=' * 80}")
    print(f"TOP 10 MOST RECENT VALID CAMPAIGNS (what should appear in history):")
    print(f"{'=' * 80}\n")
    
    valid_campaigns.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    for i, campaign in enumerate(valid_campaigns[:10], 1):
        campaign_id = campaign.get('campaign_id', 'unknown')
        name = campaign.get('campaign_name', 'Unnamed')
        status = campaign.get('status', 'unknown')
        created_at = campaign.get('created_at', '')
        total_contacts = convert_decimal(campaign.get('total_contacts', 0))
        sent_count = convert_decimal(campaign.get('sent_count', 0))
        
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_date = created_at
        
        print(f"{i:2}. {name[:40]:<40} | Status: {status:<12} | Created: {formatted_date}")
        print(f"    Campaign ID: {campaign_id}")
        print(f"    Recipients: {total_contacts}, Sent: {sent_count}")
        print()
    
    # Show preview campaigns if any
    if preview_campaigns:
        print(f"\n{'=' * 80}")
        print(f"⚠️  PREVIEW CAMPAIGNS (These are FILTERED OUT):")
        print(f"{'=' * 80}\n")
        
        for i, campaign in enumerate(preview_campaigns[:5], 1):
            campaign_id = campaign.get('campaign_id', 'unknown')
            name = campaign.get('campaign_name', 'Unnamed')
            status = campaign.get('status', 'unknown')
            ctype = campaign.get('type', '')
            created_at = campaign.get('created_at', '')
            
            print(f"{i}. {name[:50]} (ID: {campaign_id})")
            print(f"   Status: {status}, Type: {ctype}, Created: {created_at[:19] if created_at else 'N/A'}")
    
    # Show campaigns missing created_at if any
    if missing_created_at:
        print(f"\n{'=' * 80}")
        print(f"❌ CAMPAIGNS MISSING created_at (Will sort to end):")
        print(f"{'=' * 80}\n")
        
        for i, campaign in enumerate(missing_created_at[:5], 1):
            campaign_id = campaign.get('campaign_id', 'unknown')
            name = campaign.get('campaign_name', 'Unnamed')
            status = campaign.get('status', 'unknown')
            
            print(f"{i}. {name[:50]} (ID: {campaign_id})")
            print(f"   Status: {status}, created_at: {campaign.get('created_at', 'MISSING')}")
    
    # Search for campaigns by name/subject
    print(f"\n{'=' * 80}")
    print(f"🔍 SEARCH YOUR CAMPAIGNS:")
    print(f"{'=' * 80}")
    search_term = input("\nEnter campaign name or subject to search (or press Enter to skip): ").strip().lower()
    
    if search_term:
        matches = []
        for campaign in all_campaigns:
            name = str(campaign.get('campaign_name', '')).lower()
            subject = str(campaign.get('subject', '')).lower()
            if search_term in name or search_term in subject:
                matches.append(campaign)
        
        if matches:
            print(f"\n✅ Found {len(matches)} matching campaign(s):\n")
            for campaign in matches:
                campaign_id = campaign.get('campaign_id', 'unknown')
                name = campaign.get('campaign_name', 'Unnamed')
                status = campaign.get('status', 'unknown')
                ctype = campaign.get('type', '')
                created_at = campaign.get('created_at', '')
                
                print(f"Campaign: {name}")
                print(f"  ID: {campaign_id}")
                print(f"  Status: {status}")
                print(f"  Type: {ctype}")
                print(f"  Created: {created_at}")
                print(f"  Will show in history? {('preview' not in status.lower() and 'preview' not in ctype.lower() and bool(created_at))}")
                print()
        else:
            print(f"\n❌ No campaigns found matching '{search_term}'")
    
    print(f"\n{'=' * 80}")
    print("✅ Diagnosis complete!")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    try:
        diagnose_campaigns()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

