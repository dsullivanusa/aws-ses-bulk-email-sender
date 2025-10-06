#!/usr/bin/env python3
"""
Quick fix for the contacts page pagination issue
Creates a JavaScript patch to fix the page size dropdown and pagination
"""

def create_pagination_fix():
    """Create a JavaScript fix for the pagination issue"""
    
    print("🔧 Creating Pagination Fix")
    print("=" * 30)
    
    # The JavaScript fix to add to the web UI
    js_fix = """
    // PAGINATION FIX - Add this to the web UI
    <script>
    // Fix for page size dropdown and pagination
    document.addEventListener('DOMContentLoaded', function() {
        // Ensure pagination state is properly initialized
        if (typeof paginationState === 'undefined') {
            paginationState = {
                currentPage: 1,
                pageSize: 25,
                paginationKeys: [null],
                hasNextPage: false,
                displayedContacts: []
            };
        }
        
        // Fix the changePageSize function
        window.changePageSize = async function() {
            try {
                const pageSizeSelect = document.getElementById('pageSize');
                if (!pageSizeSelect) {
                    console.error('Page size select not found');
                    return;
                }
                
                const newPageSize = parseInt(pageSizeSelect.value);
                console.log('Changing page size to:', newPageSize);
                
                // Disable dropdown during loading
                pageSizeSelect.disabled = true;
                
                // Reset pagination state completely
                paginationState = {
                    currentPage: 1,
                    pageSize: newPageSize,
                    paginationKeys: [null],
                    hasNextPage: false,
                    displayedContacts: []
                };
                
                // Clear current contacts display
                const tbody = document.getElementById('contactsBody');
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px;">Loading contacts...</td></tr>';
                }
                
                // Reload contacts with new page size
                await loadContacts(false);
                
                // Re-enable dropdown
                pageSizeSelect.disabled = false;
                
            } catch (error) {
                console.error('Error changing page size:', error);
                // Re-enable dropdown on error
                const pageSizeSelect = document.getElementById('pageSize');
                if (pageSizeSelect) {
                    pageSizeSelect.disabled = false;
                }
            }
        };
        
        // Fix the loadContacts function to handle pagination properly
        const originalLoadContacts = window.loadContacts;
        window.loadContacts = async function(resetPagination = true) {
            try {
                console.log('loadContacts called, resetPagination:', resetPagination);
                
                if (resetPagination) {
                    // Reset pagination to first page
                    paginationState = {
                        currentPage: 1,
                        pageSize: parseInt(document.getElementById('pageSize')?.value) || 25,
                        paginationKeys: [null],
                        hasNextPage: false,
                        displayedContacts: []
                    };
                }
                
                // Build API URL with proper parameters
                const urlParams = new URLSearchParams();
                urlParams.append('limit', paginationState.pageSize);
                
                // Add lastKey only if it exists and is not null
                const lastKey = paginationState.paginationKeys[paginationState.currentPage - 1];
                if (lastKey && lastKey !== null) {
                    urlParams.append('lastKey', JSON.stringify(lastKey));
                }
                
                const url = `${API_URL}/contacts?${urlParams.toString()}`;
                console.log('Fetching contacts from:', url);
                console.log('Pagination state:', paginationState);
                
                const response = await fetch(url);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
                }
                
                const result = await response.json();
                console.log('Contacts result:', result);
                
                // Update pagination state
                if (result.lastEvaluatedKey) {
                    paginationState.paginationKeys[paginationState.currentPage] = result.lastEvaluatedKey;
                    paginationState.hasNextPage = true;
                } else {
                    paginationState.paginationKeys[paginationState.currentPage] = null;
                    paginationState.hasNextPage = false;
                }
                
                // Display contacts
                paginationState.displayedContacts = result.contacts || [];
                displayContacts(paginationState.displayedContacts);
                
                // Update pagination controls
                updatePaginationControls();
                
            } catch (error) {
                console.error('Error loading contacts:', error);
                const tbody = document.getElementById('contactsBody');
                if (tbody) {
                    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: red; padding: 20px;">Error loading contacts: ${error.message}</td></tr>`;
                }
            }
        };
        
        // Fix pagination controls
        function updatePaginationControls() {
            // Update page info
            const pageInfo = document.getElementById('pageInfo');
            if (pageInfo) {
                pageInfo.textContent = `Page ${paginationState.currentPage}`;
            }
            
            // Update prev button
            const prevBtn = document.getElementById('prevPageBtn');
            if (prevBtn) {
                prevBtn.disabled = paginationState.currentPage === 1;
                prevBtn.style.background = paginationState.currentPage === 1 ? '#9ca3af' : '#6b7280';
                prevBtn.style.cursor = paginationState.currentPage === 1 ? 'not-allowed' : 'pointer';
            }
            
            // Update next button
            const nextBtn = document.getElementById('nextPageBtn');
            if (nextBtn) {
                nextBtn.disabled = !paginationState.hasNextPage;
                nextBtn.style.background = !paginationState.hasNextPage ? '#9ca3af' : '#3b82f6';
                nextBtn.style.cursor = !paginationState.hasNextPage ? 'not-allowed' : 'pointer';
            }
        }
        
        // Fix next page function
        window.nextPage = async function() {
            if (!paginationState.hasNextPage) return;
            
            paginationState.currentPage++;
            await loadContacts(false);
        };
        
        // Fix previous page function
        window.previousPage = async function() {
            if (paginationState.currentPage === 1) return;
            
            paginationState.currentPage--;
            await loadContacts(false);
        };
        
        console.log('Pagination fix applied successfully');
    });
    </script>
    """
    
    # Write the fix to a file
    with open('pagination_fix.js', 'w') as f:
        f.write(js_fix)
    
    print("✅ Created pagination fix script")
    print("📁 File created: pagination_fix.js")
    
    # Also create a simple HTML test page
    html_test = """<!DOCTYPE html>
<html>
<head>
    <title>Pagination Fix Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .controls { margin: 20px 0; }
        select, button { padding: 8px; margin: 5px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Contacts Pagination Test</h1>
    
    <div class="controls">
        <label>Page Size: </label>
        <select id="pageSize" onchange="changePageSize()">
            <option value="10">10</option>
            <option value="25" selected>25</option>
            <option value="50">50</option>
            <option value="100">100</option>
        </select>
        
        <button onclick="previousPage()" id="prevPageBtn">Previous</button>
        <span id="pageInfo">Page 1</span>
        <button onclick="nextPage()" id="nextPageBtn">Next</button>
        
        <button onclick="loadContacts()">Load Contacts</button>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Email</th>
                <th>First Name</th>
                <th>Last Name</th>
                <th>Company</th>
                <th>State</th>
                <th>Phone</th>
                <th>Created</th>
            </tr>
        </thead>
        <tbody id="contactsBody">
            <tr><td colspan="7" style="text-align: center; padding: 20px;">Click "Load Contacts" to start</td></tr>
        </tbody>
    </table>
    
    <!-- Include the pagination fix -->
    <script>
        // Mock API_URL for testing
        const API_URL = 'https://your-api-gateway-url.amazonaws.com/prod';
        
        // Mock pagination state
        let paginationState = {
            currentPage: 1,
            pageSize: 25,
            paginationKeys: [null],
            hasNextPage: false,
            displayedContacts: []
        };
        
        // Mock displayContacts function
        function displayContacts(contacts) {
            const tbody = document.getElementById('contactsBody');
            if (!contacts || contacts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px;">No contacts found</td></tr>';
                return;
            }
            
            tbody.innerHTML = contacts.map(contact => `
                <tr>
                    <td>${contact.email || ''}</td>
                    <td>${contact.first_name || ''}</td>
                    <td>${contact.last_name || ''}</td>
                    <td>${contact.agency_name || contact.company || ''}</td>
                    <td>${contact.state || ''}</td>
                    <td>${contact.phone || ''}</td>
                    <td>${contact.created_at || ''}</td>
                </tr>
            `).join('');
        }
    </script>
    
    <!-- Include the pagination fix -->
    <script src="pagination_fix.js"></script>
    
</body>
</html>"""
    
    with open('pagination_test.html', 'w') as f:
        f.write(html_test)
    
    print("📁 Created test page: pagination_test.html")
    
    return True

def main():
    """Main function"""
    print("🔧 Contacts Page Pagination Fix")
    print("=" * 40)
    
    try:
        create_pagination_fix()
        
        print("\n✅ Fix created successfully!")
        print("\n📋 What to do next:")
        print("  1. Open pagination_test.html in your browser to test the fix")
        print("  2. If the fix works, integrate pagination_fix.js into your web UI")
        print("  3. Or manually apply the JavaScript changes to bulk_email_api_lambda.py")
        
        print("\n🔍 The issue was:")
        print("  - Page size dropdown wasn't properly resetting pagination state")
        print("  - API calls weren't including correct pagination parameters")
        print("  - Pagination state wasn't being managed correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating fix: {str(e)}")
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("\n🎉 Pagination fix ready!")
    else:
        print("\n❌ Fix creation failed!")
