#!/usr/bin/env python3
"""
Simple Lambda Concurrency Setting Script
Uses AWS CLI commands for reliable concurrency configuration
"""

import subprocess
import sys
import json

REGION = 'us-gov-west-1'
FUNCTION_NAME = 'email-worker-function'

def run_aws_command(command):
    """Run AWS CLI command and return result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def get_current_concurrency():
    """Get current reserved concurrency setting"""
    command = f"aws lambda get-function-configuration --function-name {FUNCTION_NAME} --region {REGION} --query 'ReservedConcurrentExecutions' --output text"
    
    success, output = run_aws_command(command)
    if success:
        return output.strip()
    else:
        print(f"❌ Error getting current concurrency: {output}")
        return None

def set_concurrency(concurrency):
    """Set reserved concurrency"""
    print(f"🔧 Setting reserved concurrency to {concurrency}...")
    
    command = f"aws lambda put-function-concurrency --function-name {FUNCTION_NAME} --reserved-concurrency-count {concurrency} --region {REGION}"
    
    success, output = run_aws_command(command)
    if success:
        print(f"✅ Successfully set reserved concurrency to {concurrency}")
        return True
    else:
        print(f"❌ Error setting concurrency: {output}")
        return False

def remove_concurrency():
    """Remove reserved concurrency"""
    print(f"🔧 Removing reserved concurrency...")
    
    command = f"aws lambda delete-function-concurrency --function-name {FUNCTION_NAME} --region {REGION}"
    
    success, output = run_aws_command(command)
    if success:
        print(f"✅ Successfully removed reserved concurrency")
        return True
    else:
        print(f"❌ Error removing concurrency: {output}")
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
        print(f"      Command: python set_concurrency_simple.py {concurrency}")
    
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
        print(f"  python set_concurrency_simple.py <concurrency>")
        print(f"  python set_concurrency_simple.py remove")
        print(f"  python set_concurrency_simple.py recommendations")
        print(f"\nExamples:")
        print(f"  python set_concurrency_simple.py 400    # Set to 400")
        print(f"  python set_concurrency_simple.py remove # Remove reserved concurrency")
        print(f"  python set_concurrency_simple.py recommendations # Show recommendations")
        return
    
    # Get current concurrency
    current = get_current_concurrency()
    if current:
        print(f"📋 Current Reserved Concurrency: {current}")
    
    arg = sys.argv[1].lower()
    
    if arg == 'remove':
        success = remove_concurrency()
    elif arg == 'recommendations':
        show_recommendations()
        return
    else:
        try:
            concurrency = int(arg)
            if concurrency < 1 or concurrency > 1000:
                print(f"❌ Concurrency must be between 1 and 1,000")
                return
            success = set_concurrency(concurrency)
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
        
        # Show performance expectations
        if arg.isdigit():
            concurrency = int(arg)
            print(f"\n📊 Performance Expectations:")
            print(f"   Processing Time: {2000 / concurrency * 0.5:.1f} - {2000 / concurrency * 1.0:.1f} minutes")
            print(f"   Concurrent Executions: {concurrency}")
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
