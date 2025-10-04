#!/usr/bin/env python3
"""
Remove unwanted attributes from EmailCampaigns table
Removes: aws_region, aws_secret_name, email_service, filter_description,
         filter_type, smtp_port, smtp_server
"""

import boto3
from botocore.exceptions import ClientError
import time

REGION = 'us-gov-west-1'
TABLE_NAME = 'EmailCampaigns'

# Attributes to remove
ATTRIBUTES_TO_REMOVE = [
    'aws_region',
    'aws_secret_name',
    'email_service',
    'filter_description',
    'filter_type',
    'smtp_port',
    'smtp_server'
]

def cleanup_campaign_attributes():
    """Remove specified attributes from all campaign records"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("\n" + "="*80)
    print("🧹 CLEANUP EMAILCAMPAIGNS TABLE ATTRIBUTES")
    print("="*80)
    print()
    print(f"Table: {TABLE_NAME}")
    print(f"Region: {REGION}")
    print()
    print("Attributes to remove:")
    for attr in ATTRIBUTES_TO_REMOVE:
        print(f"  ✗ {attr}")
    print()
    
    # Step 1: Scan table to get all campaigns
    print("Step 1: Scanning table for all campaigns...")
    
    try:
        response = table.scan()
        campaigns = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            campaigns.extend(response.get('Items', []))
        
        print(f"✅ Found {len(campaigns)} campaign records")
        
        if not campaigns:
            print("\n✓ No campaigns found. Nothing to clean up.")
            return True
        
        # Step 2: Check which campaigns have these attributes
        campaigns_to_update = []
        for campaign in campaigns:
            has_attrs = [attr for attr in ATTRIBUTES_TO_REMOVE if attr in campaign]
            if has_attrs:
                campaigns_to_update.append({
                    'campaign': campaign,
                    'attrs_to_remove': has_attrs
                })
        
        print(f"✅ Found {len(campaigns_to_update)} campaigns with attributes to remove")
        
        if not campaigns_to_update:
            print("\n✓ No campaigns have the unwanted attributes. Nothing to clean up.")
            return True
        
        # Show sample
        print()
        print("Sample campaign to be updated:")
        sample = campaigns_to_update[0]
        print(f"  Campaign ID: {sample['campaign']['campaign_id']}")
        print(f"  Attributes to remove: {', '.join(sample['attrs_to_remove'])}")
        print()
        
        # Confirmation
        response = input(f"⚠️  Update {len(campaigns_to_update)} campaigns? (yes/no): ").strip()
        if response.lower() != 'yes':
            print("\n❌ Cleanup cancelled.")
            return False
        
        # Step 3: Update each campaign
        print()
        print(f"Step 2: Removing attributes from {len(campaigns_to_update)} campaigns...")
        
        updated_count = 0
        error_count = 0
        
        for idx, item in enumerate(campaigns_to_update, 1):
            campaign = item['campaign']
            attrs = item['attrs_to_remove']
            campaign_id = campaign.get('campaign_id', 'unknown')
            
            try:
                # Build REMOVE expression
                remove_expressions = [f"#{attr}" for attr in attrs]
                update_expression = "REMOVE " + ", ".join(remove_expressions)
                
                # Build attribute names mapping
                expression_attr_names = {f"#{attr}": attr for attr in attrs}
                
                # Update item
                table.update_item(
                    Key={'campaign_id': campaign_id},
                    UpdateExpression=update_expression,
                    ExpressionAttributeNames=expression_attr_names
                )
                
                updated_count += 1
                
                # Progress indicator
                if idx % 10 == 0 or idx == len(campaigns_to_update):
                    print(f"  Progress: {idx}/{len(campaigns_to_update)} "
                          f"({idx/len(campaigns_to_update)*100:.1f}%)")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error updating {campaign_id}: {str(e)}")
        
        # Summary
        print()
        print("="*80)
        print("✅ CLEANUP COMPLETE")
        print("="*80)
        print(f"Campaigns Updated: {updated_count}")
        print(f"Errors: {error_count}")
        print()
        print("Removed attributes:")
        for attr in ATTRIBUTES_TO_REMOVE:
            print(f"  ✗ {attr}")
        print()
        print("Remaining attributes in campaigns:")
        print("  ✓ campaign_id, campaign_name, subject, body")
        print("  ✓ from_email, status, launched_by")
        print("  ✓ created_at, sent_at")
        print("  ✓ total_contacts, sent_count, failed_count, queued_count")
        print("  ✓ target_contacts (email addresses)")
        print("  ✓ attachments, filter_values")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    try:
        result = cleanup_campaign_attributes()
        
        if result:
            print("\n✅ Next steps:")
            print("  1. Deploy updated Lambda (if needed):")
            print("     python update_lambda.py")
            print()
            print("  2. Verify in DynamoDB Manager:")
            print("     python dynamodb_manager_gui.py")
            print()
        
        return 0 if result else 1
        
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup cancelled by user (Ctrl+C)")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())

