#!/usr/bin/env python3
"""
Update the Bulk Email API Lambda function
"""
import boto3
import zipfile
import os

def update_bulk_email_lambda():
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        # Get all Lambda functions
        print("Fetching Lambda functions...")
        functions = lambda_client.list_functions()
        function_names = [f['FunctionName'] for f in functions['Functions']]
        
        print("\nAvailable Lambda functions:")
        for i, name in enumerate(function_names, 1):
            print(f"{i}. {name}")
        
        # Try multiple patterns to find the bulk email API function
        patterns = [
            'bulk-email',
            'BulkEmail',
            'bulk_email',
            'email-api'
        ]
        
        bulk_email_function = None
        
        for pattern in patterns:
            matches = [name for name in function_names if pattern.lower() in name.lower()]
            if matches:
                bulk_email_function = matches[0]
                print(f"\n✓ Found function matching pattern '{pattern}': {bulk_email_function}")
                break
        
        if not bulk_email_function:
            print("\n❌ Could not find bulk email Lambda function automatically.")
            print("\nPlease enter the exact function name from the list above:")
            bulk_email_function = input("Function name: ").strip()
            
            if bulk_email_function not in function_names:
                print(f"❌ Function '{bulk_email_function}' not found!")
                return
        
        print(f"\n📦 Preparing to update function: {bulk_email_function}")
        
        # Create zip file
        zip_filename = 'bulk_email_api_lambda.zip'
        
        # Delete old zip file if exists
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
            print(f"✓ Deleted old {zip_filename}")
        
        print("✓ Creating zip file...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write('bulk_email_api_lambda.py', 'lambda_function.py')
        
        print(f"✓ Created {zip_filename}")
        
        # Get file size
        file_size = os.path.getsize(zip_filename)
        file_size_mb = file_size / (1024 * 1024)
        print(f"✓ Zip file size: {file_size_mb:.2f} MB")
        
        # Update Lambda function
        print(f"\n🚀 Updating Lambda function: {bulk_email_function}...")
        
        with open(zip_filename, 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName=bulk_email_function,
                ZipFile=zip_file.read()
            )
        
        print(f"\n✅ Successfully updated {bulk_email_function}!")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        # Clean up
        os.remove(zip_filename)
        print(f"\n✓ Cleaned up {zip_filename}")
        
        print("\n" + "="*60)
        print("✅ DEPLOYMENT COMPLETE!")
        print("="*60)
        print("\nYou can now test the updated function in your web UI.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Clean up zip file on error
        if os.path.exists('bulk_email_api_lambda.zip'):
            os.remove('bulk_email_api_lambda.zip')

if __name__ == "__main__":
    print("="*60)
    print("Update Bulk Email API Lambda Function")
    print("="*60)
    print("\nThis will update the Lambda function with bulk_email_api_lambda.py")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        update_bulk_email_lambda()
    else:
        print("Cancelled")

