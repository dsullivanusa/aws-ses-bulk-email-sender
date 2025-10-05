#!/usr/bin/env python3
"""
Check what fields exist in the EmailContacts DynamoDB table
"""
import boto3
from decimal import Decimal

def check_fields():
    """Check fields in DynamoDB table"""
    
    dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
    table = dynamodb.Table('EmailContacts')
    
    try:
        print("="*60)
        print("Checking EmailContacts Table Fields")
        print("="*60)
        
        # Get a few sample items to see what fields exist
        response = table.scan(Limit=5)
        items = response.get('Items', [])
        
        if not items:
            print("\n❌ No items found in table!")
            return
        
        print(f"\n✓ Found {len(items)} sample items")
        print("\n" + "="*60)
        
        # Collect all unique field names from sample items
        all_fields = set()
        for item in items:
            all_fields.update(item.keys())
        
        print(f"Fields found in table ({len(all_fields)} total):")
        print("-"*60)
        for field in sorted(all_fields):
            print(f"  • {field}")
        
        # Check specifically for state and region fields
        print("\n" + "="*60)
        print("Checking for 'state' and 'region' fields:")
        print("-"*60)
        
        state_fields = [f for f in all_fields if 'state' in f.lower()]
        region_fields = [f for f in all_fields if 'region' in f.lower()]
        
        if state_fields:
            print(f"✓ State-related fields: {', '.join(state_fields)}")
        else:
            print("❌ No 'state' field found!")
        
        if region_fields:
            print(f"✓ Region-related fields: {', '.join(region_fields)}")
        else:
            print("❌ No 'region' field found!")
        
        # Show sample values for state and region
        print("\n" + "="*60)
        print("Sample values:")
        print("-"*60)
        
        for i, item in enumerate(items, 1):
            print(f"\nItem {i}:")
            
            # Check for state
            for field in state_fields:
                value = item.get(field, 'N/A')
                print(f"  {field}: {value}")
            
            # Check for region
            for field in region_fields:
                value = item.get(field, 'N/A')
                print(f"  {field}: {value}")
            
            # Show a few other fields
            if 'email' in item:
                print(f"  email: {item['email']}")
            if 'agency_name' in item:
                print(f"  agency_name: {item['agency_name']}")
        
        # Get distinct values for state
        print("\n" + "="*60)
        print("Scanning for distinct values...")
        print("-"*60)
        
        for field in state_fields:
            distinct_values = set()
            
            # Scan table for this field
            scan_response = table.scan(
                ProjectionExpression=field,
                Select='SPECIFIC_ATTRIBUTES'
            )
            
            for item in scan_response.get('Items', []):
                if field in item and item[field]:
                    distinct_values.add(str(item[field]))
            
            print(f"\n{field}: {len(distinct_values)} distinct values")
            if distinct_values:
                print(f"  Sample: {', '.join(sorted(list(distinct_values))[:10])}")
        
        for field in region_fields:
            distinct_values = set()
            
            # Scan table for this field
            scan_response = table.scan(
                ProjectionExpression=field,
                Select='SPECIFIC_ATTRIBUTES'
            )
            
            for item in scan_response.get('Items', []):
                if field in item and item[field]:
                    distinct_values.add(str(item[field]))
            
            print(f"\n{field}: {len(distinct_values)} distinct values")
            if distinct_values:
                print(f"  Sample: {', '.join(sorted(list(distinct_values))[:10])}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_fields()

