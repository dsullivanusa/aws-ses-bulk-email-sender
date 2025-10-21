#!/usr/bin/env python3
"""
List all Lambda functions in us-gov-west-1 region
"""

import boto3
import json

def list_lambdas():
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    print("=" * 80)
    print("Lambda Functions in us-gov-west-1")
    print("=" * 80)
    print()
    
    try:
        response = lambda_client.list_functions(MaxItems=100)
        
        if not response['Functions']:
            print("❌ No Lambda functions found in us-gov-west-1")
            return
        
        print(f"Found {len(response['Functions'])} Lambda function(s):\n")
        
        for idx, func in enumerate(response['Functions'], 1):
            print(f"{idx}. {func['FunctionName']}")
            print(f"   Runtime: {func['Runtime']}")
            print(f"   Handler: {func.get('Handler', 'N/A')}")
            print(f"   Last Modified: {func['LastModified']}")
            print(f"   ARN: {func['FunctionArn']}")
            print(f"   Memory: {func['MemorySize']}MB | Timeout: {func['Timeout']}s")
            
            # Check environment variables for clues
            if 'Environment' in func and 'Variables' in func['Environment']:
                env_vars = func['Environment']['Variables']
                if any(key in env_vars for key in ['CONTACTS_TABLE', 'CAMPAIGNS_TABLE', 'ATTACHMENTS_BUCKET']):
                    print(f"   ⭐ Contains Email/Contacts configuration - LIKELY THIS ONE!")
            
            print()
        
        print("=" * 80)
        print("\n💡 RECOMMENDATION:")
        print("   Look for a Lambda function with:")
        print("   - 'bulk', 'email', 'api', or similar in the name")
        print("   - Handler like 'bulk_email_api_lambda.lambda_handler'")
        print("   - Environment variables: CONTACTS_TABLE, CAMPAIGNS_TABLE, etc.")
        print()
        
    except Exception as e:
        print(f"❌ Error listing Lambda functions: {str(e)}")
        print("\nPossible issues:")
        print("1. AWS credentials not configured - run: aws configure")
        print("2. Wrong region - check if your Lambda is in us-gov-west-1")
        print("3. Insufficient IAM permissions - need lambda:ListFunctions")

if __name__ == '__main__':
    list_lambdas()
