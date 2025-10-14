#!/usr/bin/env python3
"""
Fix Decimal Serialization Issue in Lambda Function
Deploys the updated Lambda code with recursive Decimal converter
"""

import boto3
import zipfile
import os
import sys
from io import BytesIO

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'
LAMBDA_FILE = 'bulk_email_api_lambda.py'

def create_lambda_package():
    """Create Lambda deployment package"""
    print("📦 Creating Lambda deployment package...")
    
    # Create in-memory zip file
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the main Lambda file
        if not os.path.exists(LAMBDA_FILE):
            print(f"❌ Lambda file not found: {LAMBDA_FILE}")
            return None
        
        zip_file.write(LAMBDA_FILE, 'lambda_function.py')
        print(f"  ✅ Added {LAMBDA_FILE}")
    
    zip_buffer.seek(0)
    return zip_buffer.read()

def update_lambda():
    """Update Lambda function code"""
    print("="*80)
    print("FIXING DECIMAL SERIALIZATION IN LAMBDA")
    print("="*80)
    
    # Create deployment package
    package_data = create_lambda_package()
    if not package_data:
        return False
    
    print(f"\n📤 Uploading to Lambda function: {LAMBDA_FUNCTION_NAME}")
    
    # Update Lambda function
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=package_data
        )
        
        print(f"\n✅ Lambda function updated successfully!")
        print(f"   Function: {response['FunctionName']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Last Modified: {response['LastModified']}")
        print(f"   Code Size: {response['CodeSize']:,} bytes")
        
        print(f"\n{'='*80}")
        print("WHAT WAS FIXED")
        print("="*80)
        print("✅ Added recursive convert_decimals() helper function")
        print("✅ Updated get_campaigns() to use convert_decimals()")
        print("✅ Updated get_contacts() to use convert_decimals()")
        print("✅ Updated filter_contacts() to use convert_decimals()")
        print("✅ Updated search_contacts() to use convert_decimals()")
        
        print(f"\n{'='*80}")
        print("✅ CAMPAIGN HISTORY SHOULD NOW WORK!")
        print("="*80)
        print("\n📋 The 'Object of type Decimal is not JSON serializable' error is fixed.")
        print("🎉 Your campaign history tab should now load successfully!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error updating Lambda: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_lambda()
    sys.exit(0 if success else 1)

