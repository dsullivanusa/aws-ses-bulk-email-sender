#!/usr/bin/env python3
"""Update all Lambda functions to Python 3.13 runtime"""

import boto3
import sys

def update_lambda_runtime():
    """Update all Lambda functions to use Python 3.13"""
    
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    # List of your Lambda functions
    function_names = [
        'bulk-email-api-function',
        'email-worker',
        'campaign-monitor',
        # Add any other Lambda function names you have
    ]
    
    print("🔄 Updating Lambda function runtimes to Python 3.13...\n")
    
    for function_name in function_names:
        try:
            # Check current runtime
            response = lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            current_runtime = response.get('Runtime', 'unknown')
            
            print(f"📦 {function_name}")
            print(f"   Current: {current_runtime}")
            
            if current_runtime == 'python3.13':
                print(f"   ✅ Already on Python 3.13\n")
                continue
            
            # Update runtime to Python 3.13
            update_response = lambda_client.update_function_configuration(
                FunctionName=function_name,
                Runtime='python3.13'
            )
            
            new_runtime = update_response.get('Runtime', 'unknown')
            print(f"   ✅ Updated to: {new_runtime}\n")
            
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"   ⚠️  Function not found (may not be deployed yet)\n")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
    
    print("✅ Runtime update complete!")
    print("\n💡 Note: Your Lambda functions will continue running without interruption.")
    print("   The new runtime takes effect immediately for new invocations.")

if __name__ == "__main__":
    try:
        update_lambda_runtime()
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

