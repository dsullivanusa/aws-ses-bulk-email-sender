#!/usr/bin/env python3
"""
Apply the contacts pagination patch to fix the page size dropdown issue
"""

import os
import shutil
from datetime import datetime

def create_backup():
    """Create a backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"bulk_email_api_lambda_backup_{timestamp}.py"
    
    try:
        shutil.copy2('bulk_email_api_lambda.py', backup_filename)
        print(f"✅ Created backup: {backup_filename}")
        return backup_filename
    except Exception as e:
        print(f"❌ Failed to create backup: {str(e)}")
        return None

def apply_patch():
    """Apply the pagination patch"""
    print("🔧 Applying Contacts Pagination Patch")
    print("=" * 40)
    
    # Read the current file
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {str(e)}")
        return False
    
    # Find the problematic changePageSize function
    old_function = '''        async function changePageSize() {{
            const newPageSize = parseInt(document.getElementById('pageSize').value);
            paginationState.pageSize = newPageSize;
            
            // Reset to first page with new page size
            await loadContacts(true);
        }}'''
    
    new_function = '''        async function changePageSize() {{
            try {{
                const pageSizeSelect = document.getElementById('pageSize');
                if (!pageSizeSelect) {{
                    console.error('Page size select not found');
                    return;
                }}
                
                const newPageSize = parseInt(pageSizeSelect.value);
                console.log('Changing page size to:', newPageSize);
                
                // Disable dropdown during loading to prevent multiple clicks
                pageSizeSelect.disabled = true;
                
                // Reset pagination state completely
                paginationState = {{
                    currentPage: 1,
                    pageSize: newPageSize,
                    paginationKeys: [null],
                    hasNextPage: false,
                    displayedContacts: []
                }};
                
                // Reload contacts with new page size
                await loadContacts(false);
                
                // Re-enable dropdown after loading
                pageSizeSelect.disabled = false;
                
            }} catch (error) {{
                console.error('Error changing page size:', error);
                // Re-enable dropdown on error
                const pageSizeSelect = document.getElementById('pageSize');
                if (pageSizeSelect) {{
                    pageSizeSelect.disabled = false;
                }}
            }}
        }}'''
    
    # Apply the patch
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("✅ Patch applied successfully")
    else:
        print("⚠️ Original function not found exactly as expected")
        print("Looking for alternative patterns...")
        
        # Try a more flexible approach
        import re
        pattern = r'async function changePageSize\(\) \{\{[^}]*\}\}'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_function, content, flags=re.DOTALL)
            print("✅ Patch applied using regex pattern")
        else:
            print("❌ Could not find changePageSize function to patch")
            return False
    
    # Write the patched content back
    try:
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ File updated successfully")
        return True
    except Exception as e:
        print(f"❌ Error writing file: {str(e)}")
        return False

def verify_patch():
    """Verify the patch was applied correctly"""
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the new code is present
        if 'pageSizeSelect.disabled = true;' in content and 'pageSizeSelect.disabled = false;' in content:
            print("✅ Patch verification successful")
            return True
        else:
            print("❌ Patch verification failed")
            return False
    except Exception as e:
        print(f"❌ Error verifying patch: {str(e)}")
        return False

def main():
    """Main function to apply the patch"""
    print("🚀 Contacts Pagination Patch Application")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists('bulk_email_api_lambda.py'):
        print("❌ bulk_email_api_lambda.py not found")
        print("Make sure you're running this from the correct directory")
        return False
    
    try:
        # Create backup
        backup_file = create_backup()
        
        # Apply patch
        if apply_patch():
            # Verify patch
            if verify_patch():
                print("\n🎉 Patch applied successfully!")
                print("\n📋 What was fixed:")
                print("  ✅ Page size dropdown now properly resets pagination")
                print("  ✅ Dropdown is disabled during loading to prevent multiple clicks")
                print("  ✅ Proper error handling added")
                print("  ✅ Pagination state is completely reset when page size changes")
                
                print("\n🚀 Next steps:")
                print("  1. Deploy the updated Lambda function:")
                print("     python deploy_email_worker.py")
                print("  2. Test the page size dropdown")
                print("  3. Verify pagination works correctly")
                
                if backup_file:
                    print(f"\n💾 Backup created: {backup_file}")
                
                return True
            else:
                print("\n❌ Patch verification failed")
                return False
        else:
            print("\n❌ Patch application failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error applying patch: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("\n✅ Patch application completed successfully!")
    else:
        print("\n❌ Patch application failed!")
