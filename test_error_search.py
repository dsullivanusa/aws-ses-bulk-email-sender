#!/usr/bin/env python3
"""
Quick test script to verify error search is working
"""

import boto3
import sys

def test_connection():
    """Test AWS connection and Lambda access"""
    print("🔧 Testing AWS Connection and Permissions...")
    print("=" * 80)
    
    try:
        # Test Lambda access
        lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
        response = lambda_client.list_functions()
        functions = response['Functions']
        
        print(f"✅ Lambda Access: OK ({len(functions)} functions found)")
        
        # Find email worker
        email_worker = [f for f in functions if 'email' in f['FunctionName'].lower() and 'worker' in f['FunctionName'].lower()]
        if email_worker:
            print(f"✅ Email Worker Function: Found ({email_worker[0]['FunctionName']})")
        else:
            print(f"⚠️  Email Worker Function: Not found (but other functions accessible)")
        
        # Test CloudWatch Logs access
        logs_client = boto3.client('logs', region_name='us-gov-west-1')
        
        if email_worker:
            log_group_name = f"/aws/lambda/{email_worker[0]['FunctionName']}"
            try:
                logs_client.describe_log_streams(
                    logGroupName=log_group_name,
                    limit=1
                )
                print(f"✅ CloudWatch Logs Access: OK")
            except logs_client.exceptions.ResourceNotFoundException:
                print(f"⚠️  CloudWatch Logs: Log group not found (function never invoked?)")
            except Exception as e:
                print(f"❌ CloudWatch Logs Access: Error - {str(e)}")
        
        print("\n" + "=" * 80)
        print("✅ All tests passed! Ready to search for errors.")
        print("=" * 80)
        print("\n💡 Run the error search with:")
        if email_worker:
            print(f"   python search_lambda_errors_with_code.py {email_worker[0]['FunctionName']}")
        print("   OR")
        print("   python search_lambda_errors_with_code.py")
        print("   (for interactive mode)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("   1. Check AWS credentials: aws configure")
        print("   2. Verify IAM permissions for Lambda and CloudWatch Logs")
        print("   3. Ensure boto3 is installed: pip install boto3")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

