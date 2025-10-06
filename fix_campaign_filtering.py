#!/usr/bin/env python3
"""
Fix for campaign filtering issues
1. Fix pagination dropdown issue
2. Fix campaign filtering "No valid contacts found" issue
"""

import re
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

def fix_campaign_filtering():
    """Fix the campaign filtering issues"""
    print("🔧 Fixing Campaign Filtering Issues")
    print("=" * 40)
    
    # Read the current file
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {str(e)}")
        return False
    
    # Fix 1: Fix the changePageSize function for pagination
    old_change_page_size = '''        async function changePageSize() {{
            const newPageSize = parseInt(document.getElementById('pageSize').value);
            paginationState.pageSize = newPageSize;
            
            // Reset to first page with new page size
            await loadContacts(true);
        }}'''
    
    new_change_page_size = '''        async function changePageSize() {{
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
    
    # Apply pagination fix
    if old_change_page_size in content:
        content = content.replace(old_change_page_size, new_change_page_size)
        print("✅ Fixed pagination changePageSize function")
    else:
        print("⚠️ Pagination changePageSize function not found - may already be fixed")
    
    # Fix 2: Improve campaign filtering logic
    old_campaign_logic = '''            // Determine target contacts based on filter
            let targetContacts = [];
            let filterDescription = 'All Contacts';
            
            // If user has applied a filter, use the filtered contacts
            if (campaignFilteredContacts.length > 0) {{
                targetContacts = campaignFilteredContacts;
                const filterTags = Object.entries(selectedCampaignFilterValues)
                    .map(([field, values]) => `${{field}}: ${{values.join(', ')}}`)
                    .join('; ');
                filterDescription = filterTags;
            }} else if (Object.keys(selectedCampaignFilterValues).length > 0) {{
                // User has selected filters but hasn't clicked "Apply Filter"
                throw new Error('Please click "Apply Filter" button before sending the campaign.');
            }} else {{
                // No filters - need to load all contacts from DynamoDB
                console.log('No filters applied, fetching all contacts...');
                const response = await fetch(`${{API_URL}}/contacts?limit=10000`);
                if (!response.ok) {{
                    throw new Error(`Failed to load contacts: HTTP ${{response.status}}`);
                }}
                const data = await response.json();
                targetContacts = data.contacts || [];
                filterDescription = 'All Contacts';
            }}'''
    
    new_campaign_logic = '''            // Determine target contacts based on filter
            let targetContacts = [];
            let filterDescription = 'All Contacts';
            
            console.log('Campaign filter debug:', {{
                campaignFilteredContactsLength: campaignFilteredContacts?.length || 0,
                selectedCampaignFilterValuesKeys: Object.keys(selectedCampaignFilterValues || {{}}).length,
                selectedCampaignFilterValues: selectedCampaignFilterValues
            }});
            
            // If user has applied a filter, use the filtered contacts
            if (campaignFilteredContacts && campaignFilteredContacts.length > 0) {{
                targetContacts = campaignFilteredContacts;
                const filterTags = Object.entries(selectedCampaignFilterValues || {{}})
                    .map(([field, values]) => `${{field}}: ${{values.join(', ')}}`)
                    .join('; ');
                filterDescription = filterTags || 'Filtered Contacts';
                console.log(`Using ${{targetContacts.length}} filtered contacts: ${{filterDescription}}`);
            }} else if (Object.keys(selectedCampaignFilterValues || {{}}).length > 0) {{
                // User has selected filters but hasn't clicked "Apply Filter"
                console.log('Filters selected but not applied. Attempting to apply filter automatically...');
                
                try {{
                    // Try to apply the filter automatically
                    await applyCampaignFilter();
                    
                    // Check if we now have filtered contacts
                    if (campaignFilteredContacts && campaignFilteredContacts.length > 0) {{
                        targetContacts = campaignFilteredContacts;
                        const filterTags = Object.entries(selectedCampaignFilterValues)
                            .map(([field, values]) => `${{field}}: ${{values.join(', ')}}`)
                            .join('; ');
                        filterDescription = filterTags;
                        console.log(`Auto-applied filter: ${{targetContacts.length}} contacts found`);
                    }} else {{
                        throw new Error('No contacts match the selected filter criteria. Please adjust your filter or click "Apply Filter" to see results.');
                    }}
                }} catch (filterError) {{
                    console.error('Auto-apply filter failed:', filterError);
                    throw new Error('Please click "Apply Filter" button to see which contacts match your criteria before sending the campaign.');
                }}
            }} else {{
                // No filters - need to load all contacts from DynamoDB
                console.log('No filters applied, fetching all contacts...');
                try {{
                    const response = await fetch(`${{API_URL}}/contacts?limit=10000`);
                    if (!response.ok) {{
                        throw new Error(`Failed to load contacts: HTTP ${{response.status}}`);
                    }}
                    const data = await response.json();
                    targetContacts = data.contacts || [];
                    filterDescription = 'All Contacts';
                    console.log(`Loaded ${{targetContacts.length}} contacts from database`);
                }} catch (loadError) {{
                    console.error('Failed to load contacts:', loadError);
                    throw new Error(`Failed to load contacts: ${{loadError.message}}`);
                }}
            }}'''
    
    # Apply campaign filtering fix
    if old_campaign_logic in content:
        content = content.replace(old_campaign_logic, new_campaign_logic)
        print("✅ Fixed campaign filtering logic")
    else:
        print("⚠️ Campaign filtering logic not found exactly - trying regex approach")
        # Try with regex for more flexible matching
        pattern = r'// Determine target contacts based on filter[\s\S]*?filterDescription = \'All Contacts\';'
        if re.search(pattern, content):
            content = re.sub(pattern, new_campaign_logic, content)
            print("✅ Fixed campaign filtering logic using regex")
        else:
            print("❌ Could not find campaign filtering logic to fix")
    
    # Fix 3: Add better error handling for target_contacts extraction
    old_target_contacts = '''                target_contacts: targetContacts.map(c => c.email),  // Send email list to backend'''
    
    new_target_contacts = '''                target_contacts: targetContacts.map(c => c?.email).filter(email => email),  // Send email list to backend'''
    
    if old_target_contacts in content:
        content = content.replace(old_target_contacts, new_target_contacts)
        print("✅ Fixed target_contacts extraction")
    else:
        print("⚠️ Target contacts extraction not found - may already be fixed")
    
    # Fix 4: Add validation for empty target contacts
    old_validation = '''            if (targetContacts.length === 0) {{
                throw new Error('No contacts found. Please add contacts or adjust your filter.');
            }}'''
    
    new_validation = '''            if (!targetContacts || targetContacts.length === 0) {{
                throw new Error('No contacts found. Please add contacts or adjust your filter.');
            }}
            
            // Additional validation - check if emails are valid
            const validEmails = targetContacts.map(c => c?.email).filter(email => email && email.includes('@'));
            if (validEmails.length === 0) {{
                throw new Error('No valid email addresses found in the selected contacts. Please check your contact data.');
            }}
            
            console.log(`Valid emails found: ${{validEmails.length}} out of ${{targetContacts.length}} contacts`);'''
    
    if old_validation in content:
        content = content.replace(old_validation, new_validation)
        print("✅ Added email validation")
    else:
        print("⚠️ Contact validation not found - may already be fixed")
    
    # Write the fixed content back
    try:
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ File updated successfully")
        return True
    except Exception as e:
        print(f"❌ Error writing file: {str(e)}")
        return False

def verify_fixes():
    """Verify the fixes were applied correctly"""
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        fixes_applied = []
        
        # Check if fixes are present
        if 'pageSizeSelect.disabled = true;' in content:
            fixes_applied.append("✅ Pagination fix applied")
        else:
            fixes_applied.append("❌ Pagination fix not found")
        
        if 'campaignFilteredContactsLength:' in content:
            fixes_applied.append("✅ Campaign filtering debug added")
        else:
            fixes_applied.append("❌ Campaign filtering debug not found")
        
        if 'validEmails.length === 0' in content:
            fixes_applied.append("✅ Email validation added")
        else:
            fixes_applied.append("❌ Email validation not found")
        
        if 'filter(email => email)' in content:
            fixes_applied.append("✅ Target contacts filtering added")
        else:
            fixes_applied.append("❌ Target contacts filtering not found")
        
        print("\n🔍 Verification Results:")
        for fix in fixes_applied:
            print(f"  {fix}")
        
        return all("✅" in fix for fix in fixes_applied)
        
    except Exception as e:
        print(f"❌ Error verifying fixes: {str(e)}")
        return False

def main():
    """Main function to apply all fixes"""
    print("🚀 Campaign Filtering & Pagination Fix")
    print("=" * 50)
    
    # Check if file exists
    import os
    if not os.path.exists('bulk_email_api_lambda.py'):
        print("❌ bulk_email_api_lambda.py not found")
        print("Make sure you're running this from the correct directory")
        return False
    
    try:
        # Create backup
        backup_file = create_backup()
        
        # Apply fixes
        if fix_campaign_filtering():
            # Verify fixes
            if verify_fixes():
                print("\n🎉 All fixes applied successfully!")
                print("\n📋 What was fixed:")
                print("  1. ✅ Page size dropdown pagination issue")
                print("  2. ✅ Campaign filtering 'No valid contacts found' issue")
                print("  3. ✅ Added better error handling and debugging")
                print("  4. ✅ Added email validation")
                print("  5. ✅ Auto-apply filter functionality")
                
                print("\n🚀 Next steps:")
                print("  1. Deploy the updated Lambda function:")
                print("     python deploy_email_worker.py")
                print("  2. Test the page size dropdown in Contacts tab")
                print("  3. Test campaign filtering in Send Campaign tab")
                print("  4. Verify both issues are resolved")
                
                if backup_file:
                    print(f"\n💾 Backup created: {backup_file}")
                
                return True
            else:
                print("\n❌ Fix verification failed")
                return False
        else:
            print("\n❌ Fix application failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error applying fixes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("\n✅ All fixes completed successfully!")
        print("\n🔍 The issues were:")
        print("  • Pagination: changePageSize() wasn't properly resetting state")
        print("  • Campaign Filtering: campaignFilteredContacts was empty/undefined")
        print("  • Missing validation for email addresses in contacts")
    else:
        print("\n❌ Fix application failed!")
