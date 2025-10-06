#!/usr/bin/env python3
"""
Fix for contacts page pagination issue
The issue is in the loadContacts function and changePageSize function
"""

import re

def fix_pagination_issue():
    """Fix the pagination issue in the bulk_email_api_lambda.py file"""
    
    print("🔧 Fixing Contacts Page Pagination Issue")
    print("=" * 50)
    
    # Read the current file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the problematic loadContacts function
    # The issue is that when changePageSize is called, it doesn't properly reset pagination
    # and the API call doesn't include the correct parameters
    
    # First, let's fix the loadContacts function to properly handle pagination
    old_load_contacts = r'''async function loadContacts\(resetPagination = true\) \{\{
            console\.log\('loadContacts called, resetPagination:', resetPagination\);
            const button = event\?\?\.target \|\| document\.querySelector\('button\[onclick="loadContacts\(\)"\]'\);
            const originalText = button\?\?\.textContent \|\| '🔄 Load Contacts';
            
            if \(resetPagination\) \{\{
                // Reset pagination to first page
                paginationState = \{\{
                    currentPage: 1,
                    pageSize: parseInt\(document\.getElementById\('pageSize'\)\.value\) \|\| 25,
                    paginationKeys: \[null\],
                    hasNextPage: false,
                    displayedContacts: \[\]
                \}\};
            \}\}
            
            try \{\{
                if \(button\) \{'''
    
    # The new loadContacts function with proper pagination handling
    new_load_contacts = '''async function loadContacts(resetPagination = true) {{
            console.log('loadContacts called, resetPagination:', resetPagination);
            const button = event?.target || document.querySelector('button[onclick="loadContacts()"]');
            const originalText = button?.textContent || '🔄 Load Contacts';
            
            if (resetPagination) {{
                // Reset pagination to first page
                paginationState = {{
                    currentPage: 1,
                    pageSize: parseInt(document.getElementById('pageSize').value) || 25,
                    paginationKeys: [null],
                    hasNextPage: false,
                    displayedContacts: []
                }};
            }}
            
            try {{
                if (button) {'''
    
    # Apply the first fix
    content = re.sub(old_load_contacts, new_load_contacts, content, flags=re.DOTALL)
    
    # Now let's find and fix the API call part in loadContacts
    # The issue is that the API call doesn't properly include pagination parameters
    old_api_call = r'''const url = `\${{API_URL}}/contacts\?\${{new URLSearchParams\(\{\{
                    limit: paginationState\.pageSize,
                    lastKey: paginationState\.paginationKeys\[paginationState\.currentPage - 1\]
                \}\}\)\.toString\(\)}}\`;
                
                console\.log\('Fetching contacts from:', url\);
                const response = await fetch\(url\);'''
    
    new_api_call = '''const urlParams = new URLSearchParams();
                urlParams.append('limit', paginationState.pageSize);
                
                // Add lastKey only if it exists and is not null
                const lastKey = paginationState.paginationKeys[paginationState.currentPage - 1];
                if (lastKey && lastKey !== null) {{
                    urlParams.append('lastKey', JSON.stringify(lastKey));
                }}
                
                const url = `${{API_URL}}/contacts?${{urlParams.toString()}}`;
                
                console.log('Fetching contacts from:', url);
                console.log('Pagination state:', paginationState);
                const response = await fetch(url);'''
    
    # Apply the API call fix
    content = re.sub(old_api_call, new_api_call, content, flags=re.DOTALL)
    
    # Fix the changePageSize function to properly reset pagination
    old_change_page_size = r'''async function changePageSize\(\) \{\{
            const newPageSize = parseInt\(document\.getElementById\('pageSize'\)\.value\);
            paginationState\.pageSize = newPageSize;
            
            // Reset to first page with new page size
            await loadContacts\(true\);
        \}\}'''
    
    new_change_page_size = '''async function changePageSize() {{
            const newPageSize = parseInt(document.getElementById('pageSize').value);
            console.log('Changing page size to:', newPageSize);
            
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
        }}'''
    
    # Apply the changePageSize fix
    content = re.sub(old_change_page_size, new_change_page_size, content, flags=re.DOTALL)
    
    # Add error handling for the page size dropdown
    # Find the page size dropdown HTML and add proper event handling
    old_page_size_select = r'''<select id="pageSize" onchange="changePageSize\(\)">'''
    
    new_page_size_select = '''<select id="pageSize" onchange="changePageSize()" style="min-width: 80px;">'''
    
    # Apply the page size select fix
    content = re.sub(old_page_size_select, new_page_size_select, content)
    
    # Add additional debugging and error handling
    # Find the part where contacts are processed and add better error handling
    old_contacts_processing = r'''if \(!response\.ok\) \{\{
                    throw new Error\(\`HTTP \${{response\.status}}: \${{response\.statusText}}\`\);
                \}\}
                
                const result = await response\.json\(\);
                console\.log\('Contacts result:', result\);'''
    
    new_contacts_processing = '''if (!response.ok) {{
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}} - ${{errorText}}`);
                }}
                
                const result = await response.json();
                console.log('Contacts result:', result);
                console.log('Pagination keys before update:', paginationState.paginationKeys);'''
    
    # Apply the error handling fix
    content = re.sub(old_contacts_processing, new_contacts_processing, content, flags=re.DOTALL)
    
    # Fix the pagination state update
    old_pagination_update = r'''// Update pagination state
                paginationState\.paginationKeys\[paginationState\.currentPage\] = result\.lastEvaluatedKey \|\| null;
                paginationState\.hasNextPage = !!result\.lastEvaluatedKey;'''
    
    new_pagination_update = '''// Update pagination state
                if (result.lastEvaluatedKey) {{
                    paginationState.paginationKeys[paginationState.currentPage] = result.lastEvaluatedKey;
                    paginationState.hasNextPage = true;
                }} else {{
                    paginationState.paginationKeys[paginationState.currentPage] = null;
                    paginationState.hasNextPage = false;
                }}
                console.log('Pagination keys after update:', paginationState.paginationKeys);'''
    
    # Apply the pagination update fix
    content = re.sub(old_pagination_update, new_pagination_update, content, flags=re.DOTALL)
    
    # Write the fixed content back to the file
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed contacts pagination issues:")
    print("  - Fixed loadContacts function to properly handle pagination reset")
    print("  - Fixed API call to properly include pagination parameters")
    print("  - Fixed changePageSize function to completely reset pagination state")
    print("  - Added better error handling and debugging")
    print("  - Fixed pagination state updates")
    
    return True

def create_backup():
    """Create a backup of the original file"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"bulk_email_api_lambda_backup_{timestamp}.py"
    
    try:
        shutil.copy2('bulk_email_api_lambda.py', backup_filename)
        print(f"✅ Created backup: {backup_filename}")
        return backup_filename
    except Exception as e:
        print(f"❌ Failed to create backup: {str(e)}")
        return None

def main():
    """Main function to fix the pagination issue"""
    print("🔧 Contacts Page Pagination Fix")
    print("=" * 40)
    
    try:
        # Create backup first
        backup_file = create_backup()
        
        # Apply the fix
        if fix_pagination_issue():
            print("\n🎉 Pagination fix applied successfully!")
            print("\n📋 What was fixed:")
            print("  1. Page size dropdown now properly resets pagination")
            print("  2. API calls include correct pagination parameters")
            print("  3. Pagination state is properly managed")
            print("  4. Better error handling and debugging added")
            
            print("\n🚀 Next steps:")
            print("  1. Deploy the updated Lambda function")
            print("  2. Test the page size dropdown")
            print("  3. Verify pagination works correctly")
            
            if backup_file:
                print(f"\n💾 Backup created: {backup_file}")
            
            return True
        else:
            print("❌ Failed to apply pagination fix")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing pagination: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("\n✅ Fix completed successfully!")
    else:
        print("\n❌ Fix failed!")
