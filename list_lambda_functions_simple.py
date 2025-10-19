#!/usr/bin/env python3
"""
Simple Lambda Function Lister
Quickly shows all Lambda functions in your AWS account
"""

import boto3
import sys

def list_functions():
    """List all Lambda functions with key details"""
    print("=" * 80)
    print("AWS Lambda Functions")
    print("=" * 80)
    
    try:
        # Get region info
        session = boto3.session.Session()
        region = session.region_name or 'default'
        print(f"Region: {region}\n")
        
        lambda_client = boto3.client('lambda')
        
        # Get all functions
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        if not functions:
            print("No Lambda functions found in this account/region")
            print("\nPossible reasons:")
            print("  - Wrong AWS region selected")
            print("  - No Lambda functions deployed yet")
            print("  - Insufficient permissions to list functions")
            return
        
        print(f"Found {len(functions)} function(s):\n")
        print("-" * 80)
        
        # Sort by name
        functions.sort(key=lambda x: x['FunctionName'])
        
        for idx, func in enumerate(functions, 1):
            print(f"\n{idx}. {func['FunctionName']}")
            print(f"   Runtime:      {func['Runtime']}")
            print(f"   Memory:       {func['MemorySize']} MB")
            print(f"   Timeout:      {func['Timeout']} seconds")
            print(f"   Last Modified: {func['LastModified']}")
            
            # Show if function has errors recently
            try:
                cw = boto3.client('cloudwatch')
                from datetime import datetime, timedelta
                
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=1)
                
                response = cw.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Errors',
                    Dimensions=[{'Name': 'FunctionName', 'Value': func['FunctionName']}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                
                datapoints = response.get('Datapoints', [])
                if datapoints and any(d.get('Sum', 0) > 0 for d in datapoints):
                    total_errors = sum(d.get('Sum', 0) for d in datapoints)
                    print(f"   *** ERRORS:    {int(total_errors)} in last hour ***")
            except:
                pass  # Skip error check if CloudWatch access fails
        
        print("\n" + "-" * 80)
        print(f"\nTotal: {len(functions)} function(s)")
        
        # Check for email-related functions
        email_functions = [f for f in functions if any(keyword in f['FunctionName'].lower() 
                          for keyword in ['email', 'worker', 'ses', 'mail', 'smtp'])]
        
        if email_functions:
            print("\n" + "=" * 80)
            print("Email-Related Functions:")
            print("=" * 80)
            for func in email_functions:
                print(f"  - {func['FunctionName']}")
            
            if len(email_functions) == 1:
                print(f"\nTo diagnose EmailWorker errors, run:")
                print(f"  python diagnose_emailworker_errors.py 24 {email_functions[0]['FunctionName']}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Check AWS credentials are configured: aws sts get-caller-identity")
        print("  2. Verify you have Lambda read permissions")
        print("  3. Check you're in the correct region: aws configure get region")
        sys.exit(1)


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("Usage: python list_lambda_functions_simple.py")
        print("\nLists all Lambda functions in your AWS account/region")
        print("Shows function names, runtime, memory, and recent errors")
        return
    
    list_functions()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

