# CC/BCC-Only Campaigns

## Feature
Allows sending campaigns to CC and BCC recipients only, without requiring contacts from the database.

## Problem Solved
Previously, the system required selecting contacts from the database before sending a campaign. This prevented sending emails to just CC/BCC recipients without also selecting database contacts.

## Solution
Updated validation logic to check for CC/BCC email addresses early and allow campaigns when:
- No contacts are selected from database, BUT
- CC or BCC fields contain email addresses

## Implementation

### Code Changes (Lines 3716-3749)

```javascript
// Check for CC/BCC early to allow CC/BCC-only campaigns
const ccValue = document.getElementById('campaignCc')?.value || '';
const bccValue = document.getElementById('campaignBcc')?.value || '';
const hasCcOrBcc = ccValue.trim().length > 0 || bccValue.trim().length > 0;

// THREE STATES: null = no filter, [] = filter with no results, [...] = filtered contacts
if (campaignFilteredContacts === null) {
    // No filters applied - check if CC/BCC exist
    if (!hasCcOrBcc) {
        // No contacts selected and no CC/BCC
        throw new Error('⚠️ Cannot send campaign: No targets selected...');
    }
    // CC/BCC exist, allow campaign with empty contact list
    targetContacts = [];
    filterDescription = 'CC/BCC Recipients Only';
}
```

## Use Cases

### Use Case 1: Quick Email to Specific People
**Scenario:** Need to send an email to 2-3 specific people without adding them to the database

**Steps:**
1. Go to Send Campaign tab
2. Fill in campaign details (subject, body)
3. Add email addresses to CC field: `john@example.com, jane@example.com`
4. Click "Send Campaign"

**Result:** ✅ Campaign sends to CC recipients only

### Use Case 2: Blind Copy to Management
**Scenario:** Send campaign to database contacts, plus blind copy to management

**Steps:**
1. Select contacts from database (e.g., "All" or filtered)
2. Add management emails to BCC field: `ceo@company.com, manager@company.com`
3. Click "Send Campaign"

**Result:** ✅ Campaign sends to all selected contacts + BCC recipients

### Use Case 3: CC/BCC Only (No Database Contacts)
**Scenario:** Send to external recipients not in the database

**Steps:**
1. Don't select any contacts from database
2. Add emails to CC and/or BCC fields
3. Click "Send Campaign"

**Result:** ✅ Campaign sends to CC/BCC only

### Use Case 4: Filter Returns 0 Contacts, but CC/BCC Exist
**Scenario:** Filter has no matches, but still want to send to CC/BCC

**Steps:**
1. Apply a filter that returns 0 contacts
2. Add emails to CC/BCC fields
3. Click "Send Campaign"

**Result:** ✅ Campaign sends to CC/BCC recipients

## Validation Logic

### Scenario 1: No Filter, No CC/BCC
```
Filter: null
CC: (empty)
BCC: (empty)

Result: ❌ Error - "No targets selected. Please select contacts, apply filter, or add CC/BCC"
```

### Scenario 2: No Filter, Has CC/BCC
```
Filter: null
CC: john@example.com
BCC: (empty)

Result: ✅ Allowed - Sends to CC only
Filter Description: "CC/BCC Recipients Only"
```

### Scenario 3: Filter Returns 0, No CC/BCC
```
Filter: Applied (0 results)
CC: (empty)
BCC: (empty)

Result: ❌ Error - "Filter returned 0 contacts. Please adjust filter or add CC/BCC"
```

### Scenario 4: Filter Returns 0, Has CC/BCC
```
Filter: Applied (0 results)
CC: jane@example.com
BCC: boss@example.com

Result: ✅ Allowed - Sends to CC and BCC
Filter Description: "CC/BCC Recipients Only (Filter returned 0 contacts)"
```

### Scenario 5: Filter Returns Contacts + CC/BCC
```
Filter: Applied (100 results)
CC: john@example.com
BCC: manager@example.com

Result: ✅ Allowed - Sends to 102 recipients (100 + 1 CC + 1 BCC, minus duplicates)
Filter Description: Shows applied filter criteria
```

## Backend Processing

### Your Backend Code
Based on your changes, the backend now:

1. **Processes Contacts:** Enqueues each contact from database to SQS
2. **Processes CC Recipients:** Enqueues each CC email separately
3. **Processes BCC Recipients:** Enqueues each BCC email separately
4. **Deduplication:** Skips CC/BCC if already in contact list

```python
# Your backend code
def enqueue_special(recipient_email, role):
    if recipient_email in all_target_emails:
        print(f"Skipping {role} {recipient_email} because it is already in target contacts")
        return
    
    # Enqueue CC/BCC recipient
    sqs_client.send_message(...)
```

## Confirmation Popup

The confirmation popup now shows correct counts for CC/BCC-only campaigns:

### Example: CC/BCC Only
```
📧 Campaign Confirmation

You are about to send this campaign to:

📊 Total Recipients: 5

Breakdown:
• Contacts from database: 0
• CC recipients: 3
• BCC recipients: 2

Filter: CC/BCC Recipients Only

⚠️ Are you sure you want to send this campaign?
```

### Example: Mixed (Contacts + CC/BCC)
```
📧 Campaign Confirmation

You are about to send this campaign to:

📊 Total Recipients: 523

Breakdown:
• Contacts from database: 500
• CC recipients: 20
• BCC recipients: 3

Filter: state: California, Texas

⚠️ Are you sure you want to send this campaign?
```

## Benefits

✅ **Flexibility** - Send to anyone without database entry  
✅ **Quick Sends** - Don't need to add contacts for one-off emails  
✅ **Privacy** - BCC for blind copies  
✅ **Management Oversight** - Easy to add supervisors to BCC  
✅ **No Database Clutter** - Don't add temporary recipients  
✅ **Deduplication** - Backend prevents duplicate sends  

## Error Messages

### Updated Error Messages

**No Targets and No CC/BCC:**
```
⚠️ Cannot send campaign: No targets selected.

No emails will be sent because you have not selected any targets.

Please select targets by:
• Clicking "All" to send to all contacts, OR
• Applying a filter to select specific contacts, OR
• Adding email addresses to CC/BCC fields

Then click "Apply Filter" (if using contacts) before sending.
```

**Filter Returns 0 and No CC/BCC:**
```
⚠️ Cannot send campaign: Your filter returned 0 contacts.

No emails will be sent because no targets are selected.

Please adjust your filter criteria, clear filters to send to all contacts, 
or add email addresses to CC/BCC fields.
```

## Testing Checklist

- [ ] Send campaign with CC only (no contacts)
- [ ] Send campaign with BCC only (no contacts)
- [ ] Send campaign with CC and BCC only (no contacts)
- [ ] Send campaign with contacts + CC
- [ ] Send campaign with contacts + BCC
- [ ] Send campaign with contacts + CC + BCC
- [ ] Verify confirmation popup shows correct counts
- [ ] Verify duplicate emails are not sent twice
- [ ] Test with invalid email format in CC/BCC
- [ ] Test with no targets and no CC/BCC (should error)
- [ ] Test with filter returning 0 but CC/BCC present
- [ ] Check backend logs for proper enqueuing
- [ ] Verify SQS messages include role (cc/bcc)

## Examples

### Example 1: Emergency Email to Executives
```
Scenario: Need to send urgent email to 3 executives not in database

Steps:
1. Subject: "Urgent: Security Alert"
2. Body: "Please review immediately..."
3. CC: (empty)
4. BCC: ceo@company.com, cto@company.com, ciso@company.com
5. Click "Send Campaign"

Result: 3 BCC recipients receive email
```

### Example 2: Campaign with Management Oversight
```
Scenario: Send campaign to all state contacts, with management in BCC

Steps:
1. Click "All" → "Apply Filter" (500 contacts)
2. Subject: "Monthly Update"
3. Body: "Hello {{first_name}}..."
4. CC: (empty)
5. BCC: supervisor@company.com, director@company.com
6. Click "Send Campaign"

Result: 502 recipients (500 contacts + 2 BCC)
```

### Example 3: Test Send to Self
```
Scenario: Test campaign before sending to large list

Steps:
1. Don't select any contacts
2. Subject: "TEST - Monthly Newsletter"
3. Body: "Hello {{first_name}}..."
4. CC: myemail@company.com
5. BCC: (empty)
6. Click "Send Campaign"

Result: 1 CC recipient (yourself) receives test email
```

## Console Logging

New log messages help track CC/BCC-only campaigns:

```javascript
// When sending to CC/BCC only
console.log('Sending to CC/BCC recipients only (no contacts from database)');

// When filter returns 0 but CC/BCC exist
console.log('Filter returned 0 contacts, but sending to CC/BCC recipients');

// Always logs breakdown
console.log(`Total targets including CC/BCC: 5 (Contacts: 0, CC: 3, BCC: 2)`);
```

## Backward Compatibility

✅ **No breaking changes** - Existing functionality preserved  
✅ **Database contact campaigns** - Work exactly as before  
✅ **Filter logic** - Unchanged for normal use cases  
✅ **CC/BCC with contacts** - Works as before  
✅ **Error messages** - Updated but still clear  

## Security Considerations

- CC/BCC emails are validated for proper format
- Duplicate emails are prevented by backend
- All recipients still logged in campaign records
- SQS messages include role (cc/bcc) for tracking
- No sensitive data exposed in error messages
