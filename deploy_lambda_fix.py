#!/usr/bin/env python3
"""
Deploy Updated Lambda Function with Decimal Fix
Alternative deployment method
"""

import boto3
import zipfile
import os
import sys

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'
LAMBDA_FILE = 'bulk_email_api_lambda.py'
ZIP_FILE = 'lambda_deployment.zip'

def create_deployment_package():
    """Create Lambda deployment package as a file"""
    print("📦 Creating Lambda deployment package...")
    
    if not os.path.exists(LAMBDA_FILE):
        print(f"❌ Error: {LAMBDA_FILE} not found!")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Files in directory: {os.listdir('.')[:10]}")
        return False
    
    # Create zip file
    with zipfile.ZipFile(ZIP_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(LAMBDA_FILE, 'lambda_function.py')
        print(f"  ✅ Added {LAMBDA_FILE} as lambda_function.py")
    
    file_size = os.path.getsize(ZIP_FILE)
    print(f"  ✅ Created {ZIP_FILE} ({file_size:,} bytes)")
    
    return True

def deploy_to_lambda():
    """Deploy the package to Lambda"""
    print(f"\n📤 Deploying to Lambda: {LAMBDA_FUNCTION_NAME}")
    print(f"   Region: {REGION}")
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        # Read the zip file
        with open(ZIP_FILE, 'rb') as f:
            zip_data = f.read()
        
        print(f"   Upload size: {len(zip_data):,} bytes")
        
        # Update Lambda function
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_data
        )
        
        print(f"\n✅ Lambda function updated successfully!")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Last Modified: {response['LastModified']}")
        print(f"   Code Size: {response['CodeSize']:,} bytes")
        print(f"   Code SHA-256: {response['CodeSha256'][:16]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_deployment():
    """Verify the deployment by checking the function"""
    print(f"\n🔍 Verifying deployment...")
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        response = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        
        config = response['Configuration']
        print(f"\n📋 Current Lambda Configuration:")
        print(f"   Function: {config['FunctionName']}")
        print(f"   Runtime: {config['Runtime']}")
        print(f"   Handler: {config['Handler']}")
        print(f"   Code Size: {config['CodeSize']:,} bytes")
        print(f"   Last Modified: {config['LastModified']}")
        print(f"   Memory: {config['MemorySize']} MB")
        print(f"   Timeout: {config['Timeout']} seconds")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def cleanup():
    """Remove temporary zip file"""
    if os.path.exists(ZIP_FILE):
        os.remove(ZIP_FILE)
        print(f"\n🧹 Cleaned up: {ZIP_FILE}")

def main():
    print("="*80)
    print("DEPLOY LAMBDA FUNCTION - DECIMAL FIX")
    print("="*80)
    print(f"\nThis will update: {LAMBDA_FUNCTION_NAME}")
    print(f"With the convert_decimals() fix from: {LAMBDA_FILE}")
    print()
    
    # Step 1: Create package
    if not create_deployment_package():
        print("\n❌ Failed to create deployment package")
        sys.exit(1)
    
    # Step 2: Deploy
    if not deploy_to_lambda():
        cleanup()
        print("\n❌ Deployment failed")
        sys.exit(1)
    
    # Step 3: Verify
    verify_deployment()
    
    # Step 4: Cleanup
    cleanup()
    
    print("\n" + "="*80)
    print("✅ DEPLOYMENT COMPLETE!")
    print("="*80)
    print("\n🎉 The Decimal serialization fix is now deployed to AWS Lambda!")
    print("📝 Your campaign history should now work without errors.")
    print()
    print("Next steps:")
    print("  1. Open your bulk email UI")
    print("  2. Go to the History tab")
    print("  3. It should load successfully!")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment cancelled by user")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        sys.exit(1)


