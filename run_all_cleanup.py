#!/usr/bin/env python3
"""
Master Cleanup Script
Runs all database cleanup operations in sequence
"""

import subprocess
import sys

def run_script(script_name, description):
    """Run a cleanup script"""
    print("\n" + "="*80)
    print(f"🔄 Running: {description}")
    print("="*80)
    
    try:
        result = subprocess.run([sys.executable, script_name], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script_name}: {str(e)}")
        return False

def main():
    """Run all cleanup operations"""
    
    print("\n" + "="*80)
    print("🧹 DATABASE CLEANUP - MASTER SCRIPT")
    print("="*80)
    print()
    print("This will run the following cleanup operations:")
    print("  1. Remove 'emails_per_minute' from EmailConfig table")
    print("  2. Remove 7 redundant columns from EmailCampaigns table")
    print("  3. Delete SMTPConfig table")
    print()
    print("Each script will ask for confirmation.")
    print("="*80)
    print()
    
    response = input("Continue with all cleanup operations? (yes/no): ").strip()
    if response.lower() != 'yes':
        print("\n❌ Cleanup cancelled.")
        return 1
    
    results = {}
    
    # 1. Cleanup EmailConfig
    results['email_config'] = run_script(
        'cleanup_email_config.py',
        'EmailConfig - Remove emails_per_minute'
    )
    
    # 2. Cleanup EmailCampaigns
    results['campaigns'] = run_script(
        'cleanup_campaign_columns.py',
        'EmailCampaigns - Remove redundant columns'
    )
    
    # 3. Delete SMTPConfig
    results['smtp_config'] = run_script(
        'delete_smtp_config_table.py',
        'SMTPConfig - Delete table'
    )
    
    # Summary
    print("\n" + "="*80)
    print("🎯 CLEANUP SUMMARY")
    print("="*80)
    print()
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for task, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {task.replace('_', ' ').title()}")
    
    print()
    print(f"Completed: {success_count}/{total_count} tasks")
    print()
    
    if success_count == total_count:
        print("="*80)
        print("✅ ALL CLEANUP OPERATIONS COMPLETE!")
        print("="*80)
        print()
        print("Next step: Deploy updated Lambda")
        print("  python update_lambda.py")
        print()
        print("Your database schema is now streamlined!")
        print("="*80)
        return 0
    else:
        print("⚠️  Some operations failed or were cancelled.")
        print("Review the output above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())


