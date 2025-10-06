#!/usr/bin/env python3
"""
Fix and Deploy Script for AWS SES Email System
Applies fixes and optionally deploys the Lambda function
"""

import os
import sys
import subprocess
from automated_fix_script import EmailSystemFixer

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {str(e)}")
        return False

def check_prerequisites():
    """Check if required files and tools are available"""
    print("🔍 Checking prerequisites...")
    
    # Check if bulk_email_api_lambda.py exists
    if not os.path.exists('bulk_email_api_lambda.py'):
        print("❌ bulk_email_api_lambda.py not found")
        return False
    
    # Check if AWS CLI is available
    if not run_command('aws --version', 'Checking AWS CLI'):
        print("⚠️ AWS CLI not found - deployment will be skipped")
        return False
    
    # Check if Python deployment script exists
    if not os.path.exists('deploy_email_worker.py'):
        print("⚠️ deploy_email_worker.py not found - will try alternative deployment")
    
    print("✅ Prerequisites check completed")
    return True

def main():
    """Main function"""
    print("🚀 AWS SES Email System - Fix and Deploy Script")
    print("="*60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed")
        return False
    
    # Step 1: Apply fixes
    print("\n📝 Step 1: Applying fixes...")
    fixer = EmailSystemFixer()
    
    try:
        if not fixer.apply_all_fixes():
            print("\n❌ Fix application failed")
            return False
    except Exception as e:
        print(f"\n❌ Error applying fixes: {str(e)}")
        return False
    
    # Print fix summary
    fixer.print_summary()
    
    # Step 2: Ask about deployment
    print("\n" + "="*60)
    deploy = input("\n🚀 Do you want to deploy the updated Lambda function now? (y/n): ").lower().strip()
    
    if deploy in ['y', 'yes']:
        print("\n📦 Step 2: Deploying Lambda function...")
        
        # Try different deployment methods
        deployment_success = False
        
        # Method 1: Try the standard deployment script
        if os.path.exists('deploy_email_worker.py'):
            if run_command('python deploy_email_worker.py', 'Deploying with deploy_email_worker.py'):
                deployment_success = True
        
        # Method 2: Try alternative deployment scripts
        if not deployment_success:
            deployment_scripts = [
                'deploy_lambda.py',
                'update_lambda.py',
                'deploy_bulk_email_api.py'
            ]
            
            for script in deployment_scripts:
                if os.path.exists(script):
                    if run_command(f'python {script}', f'Deploying with {script}'):
                        deployment_success = True
                        break
        
        # Method 3: Manual AWS CLI deployment
        if not deployment_success:
            print("\n⚠️ Standard deployment scripts not found")
            print("You can manually deploy using AWS CLI:")
            print("aws lambda update-function-code --function-name email-worker-function --zip-file fileb://lambda-deployment.zip")
        
        if deployment_success:
            print("\n🎉 Deployment completed successfully!")
        else:
            print("\n⚠️ Deployment may have failed - please check manually")
    
    else:
        print("\n⏭️ Deployment skipped")
        print("You can deploy later using: python deploy_email_worker.py")
    
    # Step 3: Testing instructions
    print("\n" + "="*60)
    print("🧪 TESTING INSTRUCTIONS")
    print("="*60)
    print("\n1. **Test Pagination Fix (Contacts Tab):**")
    print("   • Go to the Contacts tab")
    print("   • Try changing page size from 25 to 50")
    print("   • Verify more contacts load and dropdown still works")
    print("   • Try changing back to 25")
    
    print("\n2. **Test Campaign Filtering Fix (Send Campaign Tab):**")
    print("   • Go to the Send Campaign tab")
    print("   • Apply a filter (e.g., by state or company)")
    print("   • Click 'Send Campaign'")
    print("   • Verify campaign sends successfully")
    print("   • Check browser console for debug messages")
    
    print("\n3. **Check for Errors:**")
    print("   • Open browser console (F12)")
    print("   • Look for any JavaScript errors")
    print("   • Check CloudWatch logs for Lambda function errors")
    
    # Final summary
    print("\n" + "="*60)
    print("✅ FIX AND DEPLOY SUMMARY")
    print("="*60)
    print(f"📁 Backup Created: {fixer.backup_file}")
    print(f"🔧 Fixes Applied: {len(fixer.fixes_applied)}")
    
    if fixer.errors:
        print(f"⚠️ Errors: {len(fixer.errors)}")
    
    print(f"\n💾 Rollback (if needed):")
    print(f"   cp {fixer.backup_file} bulk_email_api_lambda.py")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        if success:
            print("\n🎉 Fix and deploy process completed!")
        else:
            print("\n❌ Fix and deploy process failed!")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
