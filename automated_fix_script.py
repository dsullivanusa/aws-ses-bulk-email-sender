#!/usr/bin/env python3
"""
Automated Fix Script for AWS SES Email System
Fixes:
1. Contacts page pagination dropdown issue
2. Send Campaign tab filtering "No valid contacts found" issue
"""

import os
import re
import shutil
import sys
from datetime import datetime

class EmailSystemFixer:
    def __init__(self):
        self.backup_file = None
        self.fixes_applied = []
        self.errors = []
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def create_backup(self):
        """Create a backup of the original file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_file = f"bulk_email_api_lambda_backup_{timestamp}.py"
            
            if not os.path.exists('bulk_email_api_lambda.py'):
                raise FileNotFoundError("bulk_email_api_lambda.py not found")
                
            shutil.copy2('bulk_email_api_lambda.py', self.backup_file)
            self.log(f"Created backup: {self.backup_file}")
            return True
            
        except Exception as e:
            self.log(f"Failed to create backup: {str(e)}", "ERROR")
            self.errors.append(f"Backup failed: {str(e)}")
            return False
    
    def read_file(self):
        """Read the current file content"""
        try:
            with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.log(f"Error reading file: {str(e)}", "ERROR")
            self.errors.append(f"File read failed: {str(e)}")
            return None
    
    def write_file(self, content):
        """Write content back to file"""
        try:
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            self.log("File updated successfully")
            return True
        except Exception as e:
            self.log(f"Error writing file: {str(e)}", "ERROR")
            self.errors.append(f"File write failed: {str(e)}")
            return False
    
    def fix_pagination_changePageSize(self, content):
        """Fix the changePageSize function for pagination"""
        self.log("Applying pagination fix...")
        
        # The old problematic function
        old_function = '''        async function changePageSize() {{
            const newPageSize = parseInt(document.getElementById('pageSize').value);
            paginationState.pageSize = newPageSize;
            
            // Reset to first page with new page size
            await loadContacts(true);
        }}'''
        
        # The new fixed function
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
        
        if old_function in content:
            content = content.replace(old_function, new_function)
            self.fixes_applied.append("✅ Fixed pagination changePageSize function")
            self.log("Pagination fix applied successfully")
            return content
        else:
            self.log("Pagination function not found - may already be fixed", "WARNING")
            return content
    
    def fix_campaign_filtering_logic(self, content):
        """Fix the campaign filtering logic"""
        self.log("Applying campaign filtering fix...")
        
        # The old problematic logic
        old_logic = '''            // Determine target contacts based on filter
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
        
        # The new improved logic
        new_logic = '''            // Determine target contacts based on filter
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
        
        if old_logic in content:
            content = content.replace(old_logic, new_logic)
            self.fixes_applied.append("✅ Fixed campaign filtering logic")
            self.log("Campaign filtering fix applied successfully")
            return content
        else:
            self.log("Campaign filtering logic not found - trying regex approach", "WARNING")
            # Try with regex for more flexible matching
            pattern = r'// Determine target contacts based on filter[\s\S]*?filterDescription = \'All Contacts\';'
            if re.search(pattern, content):
                content = re.sub(pattern, new_logic, content)
                self.fixes_applied.append("✅ Fixed campaign filtering logic (regex)")
                self.log("Campaign filtering fix applied using regex")
                return content
            else:
                self.log("Could not find campaign filtering logic to fix", "ERROR")
                self.errors.append("Campaign filtering logic not found")
                return content
    
    def fix_contact_validation(self, content):
        """Add better contact validation"""
        self.log("Applying contact validation fix...")
        
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
            self.fixes_applied.append("✅ Added email validation")
            self.log("Contact validation fix applied successfully")
            return content
        else:
            self.log("Contact validation not found - may already be fixed", "WARNING")
            return content
    
    def fix_target_contacts_extraction(self, content):
        """Fix target contacts extraction"""
        self.log("Applying target contacts extraction fix...")
        
        old_extraction = '''                target_contacts: targetContacts.map(c => c.email),  // Send email list to backend'''
        
        new_extraction = '''                target_contacts: targetContacts.map(c => c?.email).filter(email => email),  // Send email list to backend'''
        
        if old_extraction in content:
            content = content.replace(old_extraction, new_extraction)
            self.fixes_applied.append("✅ Fixed target contacts extraction")
            self.log("Target contacts extraction fix applied successfully")
            return content
        else:
            self.log("Target contacts extraction not found - may already be fixed", "WARNING")
            return content
    
    def verify_fixes(self, content):
        """Verify that fixes were applied correctly"""
        self.log("Verifying fixes...")
        
        verification_results = []
        
        # Check if fixes are present
        if 'pageSizeSelect.disabled = true;' in content:
            verification_results.append("✅ Pagination fix verified")
        else:
            verification_results.append("❌ Pagination fix not found")
        
        if 'campaignFilteredContactsLength:' in content:
            verification_results.append("✅ Campaign filtering debug verified")
        else:
            verification_results.append("❌ Campaign filtering debug not found")
        
        if 'validEmails.length === 0' in content:
            verification_results.append("✅ Email validation verified")
        else:
            verification_results.append("❌ Email validation not found")
        
        if 'filter(email => email)' in content:
            verification_results.append("✅ Target contacts filtering verified")
        else:
            verification_results.append("❌ Target contacts filtering not found")
        
        self.log("Verification Results:")
        for result in verification_results:
            self.log(f"  {result}")
        
        return all("✅" in result for result in verification_results)
    
    def apply_all_fixes(self):
        """Apply all fixes to the file"""
        self.log("🚀 Starting automated fix process...")
        
        # Step 1: Create backup
        if not self.create_backup():
            return False
        
        # Step 2: Read file
        content = self.read_file()
        if content is None:
            return False
        
        # Step 3: Apply fixes
        original_content = content
        
        content = self.fix_pagination_changePageSize(content)
        content = self.fix_campaign_filtering_logic(content)
        content = self.fix_contact_validation(content)
        content = self.fix_target_contacts_extraction(content)
        
        # Step 4: Write file if changes were made
        if content != original_content:
            if not self.write_file(content):
                return False
        else:
            self.log("No changes needed - file may already be fixed", "WARNING")
        
        # Step 5: Verify fixes
        if not self.verify_fixes(content):
            self.log("Fix verification failed", "ERROR")
            return False
        
        return True
    
    def print_summary(self):
        """Print summary of fixes applied"""
        print("\n" + "="*60)
        print("🎉 AUTOMATED FIX SUMMARY")
        print("="*60)
        
        print(f"\n📁 Backup Created: {self.backup_file}")
        
        print(f"\n✅ Fixes Applied ({len(self.fixes_applied)}):")
        for fix in self.fixes_applied:
            print(f"  {fix}")
        
        if self.errors:
            print(f"\n❌ Errors Encountered ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
        
        print(f"\n🚀 Next Steps:")
        print(f"  1. Deploy the updated Lambda function:")
        print(f"     python deploy_email_worker.py")
        print(f"  2. Test the fixes:")
        print(f"     • Contacts Tab: Try changing page size from 25 to 50")
        print(f"     • Send Campaign Tab: Apply a filter and send a campaign")
        print(f"  3. Verify both issues are resolved")
        
        if self.backup_file:
            print(f"\n💾 Rollback Command (if needed):")
            print(f"     cp {self.backup_file} bulk_email_api_lambda.py")

def main():
    """Main function"""
    print("🔧 AWS SES Email System - Automated Fix Script")
    print("="*60)
    print("This script will fix:")
    print("  1. Contacts page pagination dropdown issue")
    print("  2. Send Campaign tab filtering issue")
    print("="*60)
    
    # Check if we're in the right directory
    if not os.path.exists('bulk_email_api_lambda.py'):
        print("❌ Error: bulk_email_api_lambda.py not found")
        print("Please run this script from the directory containing bulk_email_api_lambda.py")
        return False
    
    # Create fixer instance and apply fixes
    fixer = EmailSystemFixer()
    
    try:
        success = fixer.apply_all_fixes()
        
        if success:
            fixer.print_summary()
            print("\n✅ Automated fix completed successfully!")
            return True
        else:
            print("\n❌ Automated fix failed!")
            print("\nErrors encountered:")
            for error in fixer.errors:
                print(f"  • {error}")
            return False
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
