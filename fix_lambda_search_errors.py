#!/usr/bin/env python3
"""
Fix Search Errors in bulk_email_api_lambda.py
Applies the same fixes that were made to preview_bulk_ui.html
"""

import sys
from pathlib import Path

def fix_lambda_search_errors():
    """Fix the search functionality errors in the Lambda function"""
    
    lambda_file = Path('bulk_email_api_lambda.py')
    
    if not lambda_file.exists():
        print(f"❌ Error: {lambda_file} not found")
        return False
    
    print("📖 Reading bulk_email_api_lambda.py...")
    content = lambda_file.read_text(encoding='utf-8')
    original_content = content
    
    # Fix 1: loadAllContacts function - replace filterType and filterValueContainer
    print("\n🔧 Fix 1: Updating loadAllContacts() function...")
    old_loadall = """async function loadAllContacts() {{
            await loadContacts();
            document.getElementById('filterType').value = '';
            document.getElementById('filterValueContainer').style.display = 'none';
            document.getElementById('nameSearch').value = '';
            applyContactFilter();
        }}"""
    
    new_loadall = """async function loadAllContacts() {{
            await loadContacts();
            currentFilterType = null;
            document.getElementById('availableValuesArea').style.display = 'none';
            document.getElementById('nameSearch').value = '';
            applyContactFilter();
        }}"""
    
    if old_loadall in content:
        content = content.replace(old_loadall, new_loadall)
        print("   ✅ Fixed loadAllContacts() - replaced filterType and filterValueContainer references")
    else:
        print("   ⚠️  Pattern not found for loadAllContacts() - may already be fixed")
    
    # Fix 2: searchContactsByName function - replace filter logic
    print("\n🔧 Fix 2: Updating searchContactsByName() filter logic...")
    
    old_search_filter = """                    // Apply category filter on search results if active
                    const filterType = document.getElementById('filterType').value;
                    const checkedBoxes = document.querySelectorAll('.filterCheckbox:checked');
                    
                    let finalContacts = searchedContacts;
                    
                    if (filterType && checkedBoxes.length > 0) {{
                        const selectedValues = Array.from(checkedBoxes).map(cb => cb.value);
                        finalContacts = searchedContacts.filter(contact => {{
                            const contactValue = getFieldValue(contact, filterType);
                            return contactValue && selectedValues.includes(contactValue);
                        }});
                        searchResults.textContent = `Found ${{finalContacts.length}} contact(s) matching "${{searchTerm}}" with selected filters`;
                    }} else {{
                        searchResults.textContent = `Found ${{finalContacts.length}} contact(s) matching "${{searchTerm}}"`;
                    }}"""
    
    new_search_filter = """                    // Apply category filters on search results if active
                    let finalContacts = searchedContacts;
                    
                    // Check if any filters are selected
                    const hasFilters = Object.keys(selectedFilterValues).length > 0;
                    
                    if (hasFilters) {{
                        // Apply all active filters to search results
                        finalContacts = searchedContacts.filter(contact => {{
                            // Check all filter types - contact must match ALL selected filters
                            for (const [filterType, values] of Object.entries(selectedFilterValues)) {{
                                if (values && values.length > 0) {{
                                    const contactValue = getFieldValue(contact, filterType);
                                    if (!contactValue || !values.includes(contactValue)) {{
                                        return false;  // Contact doesn't match this filter
                                    }}
                                }}
                            }}
                            return true;  // Contact matches all filters
                        }});
                        const filterCount = Object.values(selectedFilterValues).reduce((sum, vals) => sum + vals.length, 0);
                        searchResults.textContent = `Found ${{finalContacts.length}} contact(s) matching "${{searchTerm}}" with ${{filterCount}} filter(s)`;
                    }} else {{
                        searchResults.textContent = `Found ${{finalContacts.length}} contact(s) matching "${{searchTerm}}"`;
                    }}"""
    
    if old_search_filter in content:
        content = content.replace(old_search_filter, new_search_filter)
        print("   ✅ Fixed searchContactsByName() - replaced with correct filter logic")
    else:
        print("   ⚠️  Pattern not found for searchContactsByName() - may already be fixed")
    
    # Check if any changes were made
    if content == original_content:
        print("\n⚠️  No changes were made - file may already be up to date")
        return True
    
    # Create backup
    backup_file = lambda_file.with_suffix('.py.backup')
    print(f"\n💾 Creating backup: {backup_file}")
    backup_file.write_text(original_content, encoding='utf-8')
    
    # Write updated content
    print(f"\n💾 Writing updated content to {lambda_file}...")
    lambda_file.write_text(content, encoding='utf-8')
    
    print("\n" + "="*70)
    print("✅ SUCCESS! bulk_email_api_lambda.py has been updated")
    print("="*70)
    print("\n📋 Changes applied:")
    print("   1. Fixed loadAllContacts() - removed non-existent DOM element references")
    print("   2. Fixed searchContactsByName() - updated filter logic to use selectedFilterValues")
    print("\n📝 Backup saved as: bulk_email_api_lambda.py.backup")
    print("\n🚀 Next steps:")
    print("   1. Test the changes locally if possible")
    print("   2. Deploy to AWS: python update_lambda.py")
    print("   3. Test the search functionality in production")
    
    return True

if __name__ == '__main__':
    try:
        success = fix_lambda_search_errors()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
