#!/usr/bin/env python3
"""
Remove emails_per_minute column from EmailConfig table
"""

import boto3
from botocore.exceptions import ClientError

REGION = 'us-gov-west-1'
TABLE_NAME = 'EmailConfig'
ATTRIBUTE_TO_REMOVE = 'emails_per_minute'

def cleanup_email_config():
    """Remove emails_per_minute from all EmailConfig records"""
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    
    print("\n" + "="*80)
    print("🧹 CLEANUP EMAILCONFIG TABLE")
    print("="*80)
    print()
    print(f"Table: {TABLE_NAME}")
    print(f"Attribute to remove: {ATTRIBUTE_TO_REMOVE}")
    print()
    
    # Step 1: Scan table
    print("Step 1: Scanning EmailConfig table...")
    
    try:
        response = table.scan()
        configs = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            configs.extend(response.get('Items', []))
        
        print(f"✅ Found {len(configs)} config records")
        
        if not configs:
            print("\n✓ No config records found. Nothing to clean up.")
            return True
        
        # Check which configs have the attribute
        configs_to_update = []
        for config in configs:
            if ATTRIBUTE_TO_REMOVE in config:
                configs_to_update.append(config)
        
        print(f"✅ Found {len(configs_to_update)} configs with '{ATTRIBUTE_TO_REMOVE}'")
        
        if not configs_to_update:
            print(f"\n✓ No configs have the '{ATTRIBUTE_TO_REMOVE}' attribute. Nothing to clean up.")
            return True
        
        # Show details
        print()
        print("Configs to update:")
        for config in configs_to_update:
            config_id = config.get('config_id', 'unknown')
            value = config.get(ATTRIBUTE_TO_REMOVE, 'N/A')
            print(f"  • config_id: {config_id}, {ATTRIBUTE_TO_REMOVE}: {value}")
        print()
        
        # Confirmation
        response = input(f"Remove '{ATTRIBUTE_TO_REMOVE}' from {len(configs_to_update)} configs? (yes/no): ").strip()
        if response.lower() != 'yes':
            print("\n❌ Cleanup cancelled.")
            return False
        
        # Step 2: Remove attribute from each config
        print()
        print(f"Step 2: Removing '{ATTRIBUTE_TO_REMOVE}' attribute...")
        
        updated_count = 0
        error_count = 0
        
        for config in configs_to_update:
            config_id = config.get('config_id', 'unknown')
            
            try:
                table.update_item(
                    Key={'config_id': config_id},
                    UpdateExpression=f"REMOVE #attr",
                    ExpressionAttributeNames={'#attr': ATTRIBUTE_TO_REMOVE}
                )
                updated_count += 1
                print(f"  ✓ Updated config_id: {config_id}")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ Error updating {config_id}: {str(e)}")
        
        # Summary
        print()
        print("="*80)
        print("✅ CLEANUP COMPLETE")
        print("="*80)
        print(f"Configs Updated: {updated_count}")
        print(f"Errors: {error_count}")
        print()
        print(f"Removed attribute: {ATTRIBUTE_TO_REMOVE}")
        print()
        print("Remaining attributes in EmailConfig:")
        print("  ✓ config_id (Primary Key)")
        print("  ✓ from_email")
        print("  ✓ from_name")
        print("  ✓ reply_to")
        print("  ✓ created_at")
        print("  ✓ (any other custom fields)")
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
        result = cleanup_email_config()
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup cancelled by user (Ctrl+C)")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())


