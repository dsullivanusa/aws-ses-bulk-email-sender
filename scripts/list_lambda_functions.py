#!/usr/bin/env python3
"""
List all Lambda functions to find the correct name
"""
import boto3

def list_functions():
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        print("="*60)
        print("Lambda Functions in us-gov-west-1")
        print("="*60)
        
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])
        
        if not functions:
            print("\nNo Lambda functions found!")
            return
        
        print(f"\nFound {len(functions)} function(s):\n")
        
        for i, func in enumerate(functions, 1):
            name = func['FunctionName']
            runtime = func.get('Runtime', 'Unknown')
            size = func.get('CodeSize', 0) / (1024 * 1024)  # Convert to MB
            
            print(f"{i}. {name}")
            print(f"   Runtime: {runtime}")
            print(f"   Code Size: {size:.2f} MB")
            print(f"   Last Modified: {func.get('LastModified', 'Unknown')}")
            print()
        
        print("="*60)
        print("\nCopy the exact function name for your scripts.")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    list_functions()

