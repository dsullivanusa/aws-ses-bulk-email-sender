#!/usr/bin/env python3
"""
Set Lambda Reserved Concurrency for Email Processing
Optimizes concurrency for 20,000 email campaigns
"""

import boto3
import sys

REGION = 'us-gov-west-1'

def set_concurrency(function_name, reserved_concurrency):
    """Set reserved concurrency for Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    print("=" * 80)
    print("🔧 Lambda Concurrency Configuration")
    print("=" * 80)
    
    try:
        # Get current configuration
        current_config = lambda_client.get_function_configuration(FunctionName=function_name)
        current_reserved = current_config.get('ReservedConcurrentExecutions', 'Unreserved')
        
        print(f"\n📋 Current Configuration:")
        print(f"   Function: {function_name}")
        print(f"   Current Reserved Concurrency: {current_reserved}")
        print(f"   Memory: {current_config.get('MemorySize', 'N/A')} MB")
        print(f"   Timeout: {current_config.get('Timeout', 'N/A')} seconds")
        
        # Set new concurrency
        print(f"\n🔧 Setting Reserved Concurrency to {reserved_concurrency}...")
        
        lambda_client.put_provisioned_concurrency_config(
            FunctionName=function_name,
            ReservedConcurrencyConfig={
                'ReservedConcurrencyCount': reserved_concurrency
            }
        )
        
        print(f"✅ Successfully set reserved concurrency to {reserved_concurrency}")
        
        # Calculate performance expectations
        print(f"\n📊 Performance Expectations for 20,000 Emails:")
        print(f"   Batch Size: 10 emails per execution")
        print(f"   Total Executions Needed: 2,000")
        print(f"   Reserved Concurrency: {reserved_concurrency}")
        print(f"   Estimated Processing Time: {2000 / reserved_concurrency * 0.5:.1f} - {2000 / reserved_concurrency * 1.0:.1f} minutes")
        
        # Show concurrency recommendations
        print(f"\n💡 Concurrency Recommendations:")
        print(f"   Conservative (200): 10-20 minutes, very stable")
        print(f"   Balanced (400): 5-10 minutes, good balance")
        print(f"   Aggressive (600): 3-7 minutes, faster but higher risk")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def remove_reserved_concurrency(function_name):
    """Remove reserved concurrency (use account limit)"""
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    print("=" * 80)
    print("🔧 Removing Reserved Concurrency")
    print("=" * 80)
    
    try:
        # Get current configuration
        current_config = lambda_client.get_function_configuration(FunctionName=function_name)
        current_reserved = current_config.get('ReservedConcurrentExecutions', 'Unreserved')
        
        if current_reserved == 'Unreserved':
            print(f"✅ Function already uses unreserved concurrency (account limit)")
            return True
        
        print(f"\n📋 Current Reserved Concurrency: {current_reserved}")
        print(f"🔧 Removing reserved concurrency...")
        
        lambda_client.delete_provisioned_concurrency_config(
            FunctionName=function_name
        )
        
        print(f"✅ Successfully removed reserved concurrency")
        print(f"💡 Function now uses account-level concurrency (typically 1,000)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def show_recommendations():
    """Show concurrency recommendations"""
    
    print("=" * 80)
    print("📊 Lambda Concurrency Recommendations for 20,000 Emails")
    print("=" * 80)
    
    print(f"\n🎯 Current System Analysis:")
    print(f"   Batch Size: 10 emails per Lambda execution")
    print(f"   Total Executions Needed: 2,000")
    print(f"   Processing Time per Batch: 20-60 seconds")
    print(f"   Account Concurrency Limit: 1,000 (default)")
    
    print(f"\n📈 Recommended Settings:")
    
    scenarios = [
        (200, "Conservative", "15-20 minutes", "Very stable, low SES rate risk"),
        (400, "Balanced", "8-12 minutes", "Good balance of speed vs. stability"),
        (600, "Aggressive", "5-8 minutes", "Fast processing, higher SES rate risk"),
        (1000, "Maximum", "3-5 minutes", "Fastest, but may hit SES rate limits")
    ]
    
    for concurrency, name, time, description in scenarios:
        print(f"\n   {name} ({concurrency}):")
        print(f"      Processing Time: {time}")
        print(f"      Description: {description}")
        print(f"      Command: python set_lambda_concurrency.py {concurrency}")
    
    print(f"\n💡 My Recommendation: 400 (Balanced)")
    print(f"   - Good processing speed (8-12 minutes)")
    print(f"   - Stable and reliable")
    print(f"   - Low risk of SES throttling")
    print(f"   - Cost-effective")

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        show_recommendations()
        print(f"\n" + "=" * 80)
        print(f"Usage:")
        print(f"  python set_lambda_concurrency.py <concurrency>")
        print(f"  python set_lambda_concurrency.py remove")
        print(f"  python set_lambda_concurrency.py recommendations")
        print(f"\nExamples:")
        print(f"  python set_lambda_concurrency.py 400    # Set to 400")
        print(f"  python set_lambda_concurrency.py remove # Remove reserved concurrency")
        print(f"  python set_lambda_concurrency.py recommendations # Show recommendations")
        return
    
    function_name = 'email-worker-function'
    arg = sys.argv[1].lower()
    
    if arg == 'remove':
        success = remove_reserved_concurrency(function_name)
    elif arg == 'recommendations':
        show_recommendations()
        return
    else:
        try:
            concurrency = int(arg)
            if concurrency < 1 or concurrency > 1000:
                print(f"❌ Concurrency must be between 1 and 1,000")
                return
            success = set_concurrency(function_name, concurrency)
        except ValueError:
            print(f"❌ Invalid concurrency value: {arg}")
            print(f"💡 Use a number between 1-1000, 'remove', or 'recommendations'")
            return
    
    if success:
        print(f"\n" + "=" * 80)
        print(f"✅ Configuration Complete!")
        print(f"=" * 80)
        print(f"\n💡 Next Steps:")
        print(f"   1. Test with a small campaign first")
        print(f"   2. Monitor CloudWatch metrics")
        print(f"   3. Check for SES throttling")
        print(f"   4. Adjust if needed")
    else:
        print(f"\n❌ Configuration Failed!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
