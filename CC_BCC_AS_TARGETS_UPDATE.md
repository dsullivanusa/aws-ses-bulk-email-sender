# CC and BCC Email Addresses as Campaign Targets

## Summary
Updated the campaign sending functionality to include CC and BCC email addresses as additional targets when sending campaigns.

## Changes Made

### 1. **Combined Target Email List**
**Before:**
- Only contacts from the database were included as targets
- CC and BCC were sent separately but not counted as targets

**After:**
- CC and BCC emails are now included in the target list
- All emails are combined and deduplicated using JavaScript Set
- Total target count includes contacts + CC + BCC

### 2. **Code Changes (Lines 3788-3816)**

**Email Collection:**
```javascript
// Parse CC and BCC from input fields
const ccList = parseEmails(document.getElementById('campaignCc')?.value || '');
const bccList = parseEmails(document.getElementById('campaignBcc')?.value || '');

// Extract contacts from database
const targetEmails = targetContacts.map(c => c?.email).filter(email => email && email.includes('@'));

// Combine all targets and remove duplicates
const allTargetEmails = [...new Set([...targetEmails, ...ccList, ...bccList])];
```

**Campaign Payload:**
```javascript
const campaign = {
    campaign_name: document.getElementById('campaignName').value,
    subject: document.getElementById('subject').value,
    body: emailBody,
    launched_by: userName,
    filter_type: Object.keys(selectedCampaignFilterValues).length > 0 ? 'custom' : null,
    filter_values: Object.keys(selectedCampaignFilterValues).length > 0 ? JSON.stringify(selectedCampaignFilterValues): null,
    filter_description: filterDescription,
    target_contacts: allTargetEmails,  // ✅ NOW INCLUDES CC + BCC
    cc: ccList,   // array of CC emails (for display/tracking)
    bcc: bccList, // array of BCC emails (for display/tracking)
    attachments: campaignAttachments
};
```

### 3. **Enhanced Logging**
Added detailed console logging to show the breakdown:
```javascript
console.log(`Total targets including CC/BCC: ${allTargetEmails.length} (Contacts: ${targetEmails.length}, CC: ${ccList.length}, BCC: ${bccList.length})`);
```

### 4. **Updated Error Message**
Improved error message when no targets are found:
```javascript
if (allTargetEmails.length === 0) {
    throw new Error('No valid email addresses found. Please check that your contacts have valid email addresses or add CC/BCC recipients.');
}
```

## How It Works

### User Workflow

1. **User selects contacts** (e.g., clicks "All" or applies filters)
2. **User adds CC/BCC emails** (optional, comma-separated)
   - Example CC: `alice@example.com, bob@example.com`
   - Example BCC: `hidden@example.com, manager@example.com`
3. **User clicks "Send Campaign"**
4. **System combines all targets:**
   - Contacts: 100 emails
   - CC: 2 emails
   - BCC: 2 emails
   - **Total: 104 unique targets** (duplicates removed)

### Email Processing

- **Backend receives:** `target_contacts` array with all 104 emails
- **Campaign sends to:** All 104 recipients
- **CC/BCC fields:** Also tracked separately for display/tracking purposes
- **Duplicates:** Automatically removed using JavaScript Set

## Benefits

✅ **CC/BCC as Targets:** CC and BCC recipients now receive the campaign email  
✅ **Flexible Targeting:** Can send to contacts only, CC/BCC only, or combination  
✅ **No Duplicates:** Automatic deduplication ensures no one receives multiple copies  
✅ **Accurate Counts:** Total target count reflects all recipients  
✅ **Enhanced Logging:** Clear console output shows breakdown of all targets  

## Examples

### Example 1: Contacts + CC
- **Contacts:** 50 selected from filter
- **CC:** `manager@example.com, supervisor@example.com`
- **BCC:** (empty)
- **Total Targets:** 52 emails

### Example 2: CC/BCC Only (No Contacts)
- **Contacts:** None selected (filter returned 0)
- **CC:** `team@example.com`
- **BCC:** `admin@example.com`
- **Total Targets:** 2 emails (will work if CC/BCC provided)

### Example 3: Duplicate Removal
- **Contacts:** `user@example.com, john@example.com`
- **CC:** `user@example.com` (duplicate)
- **BCC:** `jane@example.com`
- **Total Targets:** 3 unique emails (duplicate removed)

## Input Format

CC and BCC fields accept comma-separated email addresses:

**Valid formats:**
```
alice@example.com, bob@example.com
alice@example.com,bob@example.com
alice@example.com , bob@example.com
```

The `parseEmails()` function handles:
- Trimming whitespace
- Splitting by commas
- Validating email format
- Filtering out empty entries

## Backward Compatibility

✅ **No breaking changes**  
✅ **Empty CC/BCC:** Works exactly as before (only sends to contacts)  
✅ **Existing campaigns:** Not affected (stored data unchanged)  
✅ **API:** Backend receives same structure with larger target list  

## Testing Checklist

- [ ] Send campaign with contacts only (no CC/BCC)
- [ ] Send campaign with contacts + CC
- [ ] Send campaign with contacts + BCC
- [ ] Send campaign with contacts + CC + BCC
- [ ] Send campaign with CC only (no contacts)
- [ ] Send campaign with duplicate emails in contacts and CC
- [ ] Verify console log shows correct breakdown
- [ ] Verify campaign success message shows correct count
- [ ] Check backend campaign record has all targets
