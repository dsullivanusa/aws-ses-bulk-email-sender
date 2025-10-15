#!/usr/bin/env python3
"""
Deploy the updated email worker Lambda function with adaptive rate control
"""

import boto3
import zipfile
import os
import json
import sys
from datetime import datetime

def create_lambda_package():
    """Create a zip package for the Lambda function"""
    print("📦 Creating Lambda deployment package...")
    
    # Files to include in the package
    files_to_include = [
        'email_worker_lambda.py'
    ]
    
    # Create zip file
    zip_filename = f'email_worker_adaptive_{int(datetime.now().timestamp())}.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_include:
            if os.path.exists(file):
                zipf.write(file, file)
                print(f"  ✓ Added {file}")
            else:
                print(f"  ✗ File not found: {file}")
    
    print(f"  ✓ Created package: {zip_filename}")
    return zip_filename

def update_lambda_function(zip_filename):
    """Update the Lambda function with the new code"""
    print("🚀 Updating Lambda function...")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        # Find the email worker function
        functions = lambda_client.list_functions()
        function_name = None
        
        patterns = [
            'email-worker-function',
            'email-worker',
            'EmailWorker',
            'email_worker'
        ]
        
        for pattern in patterns:
            matches = [f for f in functions['Functions'] if pattern.lower() in f['FunctionName'].lower()]
            if matches:
                function_name = matches[0]['FunctionName']
                break
        
        if not function_name:
            print("❌ Could not find email worker Lambda function")
            print("Available functions:")
            for func in functions['Functions']:
                print(f"  - {func['FunctionName']}")
            return False
        
        print(f"✓ Found function: {function_name}")
        
        # Read the zip file
        with open(zip_filename, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        print("  📤 Uploading new code...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"  ✓ Code updated successfully")
        print(f"  ✓ Function ARN: {response['FunctionArn']}")
        print(f"  ✓ Code size: {response['CodeSize']} bytes")
        print(f"  ✓ Last modified: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

def update_lambda_configuration():
    """Update Lambda configuration for optimal performance"""
    print("⚙️ Updating Lambda configuration...")
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        # Find the function
        functions = lambda_client.list_functions()
        function_name = None
        
        for func in functions['Functions']:
            if 'email-worker' in func['FunctionName'].lower():
                function_name = func['FunctionName']
                break
        
        if not function_name:
            print("❌ Could not find email worker function for configuration update")
            return False
        
        # Update configuration
        config_updates = {
            'FunctionName': function_name,
            'Timeout': 900,  # 15 minutes (maximum for Lambda)
            'MemorySize': 1024,  # 1GB memory for better performance with attachments
            'Environment': {
                'Variables': {
                    'BASE_DELAY_SECONDS': '0.2',  # Conservative base delay
                    'MAX_DELAY_SECONDS': '8.0',   # Allow aggressive backoff
                    'MIN_DELAY_SECONDS': '0.05'   # Minimum delay
                }
            }
        }
        
        print("  📝 Updating function configuration...")
        response = lambda_client.update_function_configuration(**config_updates)
        
        print(f"  ✓ Timeout: {response['Timeout']} seconds")
        print(f"  ✓ Memory: {response['MemorySize']} MB")
        print(f"  ✓ Environment variables set:")
        for key, value in response['Environment']['Variables'].items():
            print(f"    - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating configuration: {str(e)}")
        return False

def verify_deployment():
    """Verify the deployment by checking function details"""
    print("🔍 Verifying deployment...")
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        # Find the function
        functions = lambda_client.list_functions()
        function_name = None
        
        for func in functions['Functions']:
            if 'email-worker' in func['FunctionName'].lower():
                function_name = func['FunctionName']
                break
        
        if not function_name:
            print("❌ Could not find function for verification")
            return False
        
        # Get function details
        response = lambda_client.get_function(FunctionName=function_name)
        
        print(f"  ✓ Function: {response['Configuration']['FunctionName']}")
        print(f"  ✓ Runtime: {response['Configuration']['Runtime']}")
        print(f"  ✓ Timeout: {response['Configuration']['Timeout']}s")
        print(f"  ✓ Memory: {response['Configuration']['MemorySize']}MB")
        print(f"  ✓ Last modified: {response['Configuration']['LastModified']}")
        
        # Check environment variables
        env_vars = response['Configuration'].get('Environment', {}).get('Variables', {})
        if env_vars:
            print("  ✓ Environment variables:")
            for key, value in env_vars.items():
                print(f"    - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying deployment: {str(e)}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Deploying Adaptive Rate Control to Email Worker Lambda")
    print("=" * 60)
    
    # Check if email_worker_lambda.py exists
    if not os.path.exists('email_worker_lambda.py'):
        print("❌ email_worker_lambda.py not found in current directory")
        print("Make sure you're running this script from the AWS-SES directory")
        return False
    
    try:
        # Step 1: Create deployment package
        zip_filename = create_lambda_package()
        
        # Step 2: Update Lambda function
        if not update_lambda_function(zip_filename):
            return False
        
        # Step 3: Update configuration
        if not update_lambda_configuration():
            return False
        
        # Step 4: Verify deployment
        if not verify_deployment():
            return False
        
        # Clean up
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
            print(f"  🗑️ Cleaned up: {zip_filename}")
        
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print("\nThe email worker Lambda function now includes:")
        print("  🎯 Adaptive rate control based on attachment sizes")
        print("  🚨 Automatic throttle detection and handling")
        print("  📊 Detailed rate control logging and statistics")
        print("  ⚙️ Configurable delay settings via environment variables")
        
        print("\n📋 Next Steps:")
        print("  1. Monitor CloudWatch logs for rate control behavior")
        print("  2. Test with campaigns containing attachments")
        print("  3. Adjust environment variables if needed")
        
        print("\n🔍 Monitoring Commands:")
        print("  # View recent logs:")
        print("  aws logs tail /aws/lambda/email-worker-function --follow --region us-gov-west-1")
        
        print("\n  # Test rate control:")
        print("  python test_adaptive_rate_control.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
