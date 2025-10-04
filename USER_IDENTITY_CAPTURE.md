# 👤 User Identity Capture - Implementation Guide

## Overview
The Web UI now captures user identity directly from the browser and records who launched each email campaign. This information is stored with the campaign and visible in all tracking reports.

---

## How It Works

### 1. Browser-Side Capture
The Web UI includes a **"Your Name"** field in the Send Campaign form that:
- ✅ Captures user's name/identity
- ✅ Saves to browser's localStorage
- ✅ Auto-fills on next visit (user only enters once)
- ✅ Sends to backend with campaign data

### 2. Backend Storage
When a campaign is sent:
- User name from browser → `launched_by` field
- IP address from API Gateway → appended to `launched_by`
- Final format: `"John Smith (IP: 192.168.1.100)"`
- Stored in DynamoDB EmailCampaigns table

### 3. Tracking & Reports
User identity appears in:
- Campaign Tracking GUI
- Command-line reports
- DynamoDB Manager
- CSV exports

---

## User Experience

### First Time User Opens Web UI:

```
┌────────────────────────────────────────┐
│ 📧 Send Campaign                       │
├────────────────────────────────────────┤
│ 👤 Your Name:                          │
│ [________________________]             │
│ Enter your name (saved in browser)     │
│ This will be recorded as who launched  │
│ the campaign. Your name is saved.      │
├────────────────────────────────────────┤
│ 📝 Campaign Name:                      │
│ [________________________]             │
└────────────────────────────────────────┘
```

**User enters:** "John Smith"
**Browser saves:** Name to localStorage
**Next time:** Field auto-fills with "John Smith"

### Campaign Creation:

When user clicks **"🚀 Send Campaign"**:
1. Web UI reads name from field
2. Sends to backend: `launched_by: "John Smith"`
3. Backend appends IP: `"John Smith (IP: 192.168.1.100)"`
4. Stored in EmailCampaigns table

### Campaign Tracking:

**In Campaign Tracking GUI:**
```
Campaign ID: campaign_1728057600
Campaign Name: Security Update
Launched By: John Smith (IP: 192.168.1.100)  ← Shows user + IP
Created At: 2025-10-04 10:00:00
Sent At: 2025-10-04 10:05:23
```

**In CSV Export:**
```csv
Campaign ID,campaign_1728057600
Campaign Name,Security Update
Launched By,John Smith (IP: 192.168.1.100)
Created At,2025-10-04T10:00:00
```

---

## Technical Implementation

### Frontend (JavaScript)

**1. User Name Field (HTML):**
```html
<div class="form-group">
    <label>👤 Your Name:</label>
    <input type="text" id="userName" 
           placeholder="Enter your name (saved in browser)" 
           onchange="saveUserName()">
    <small>This will be recorded as who launched the campaign.</small>
</div>
```

**2. Save to localStorage:**
```javascript
function saveUserName() {
    const userName = document.getElementById('userName').value.trim();
    if (userName) {
        localStorage.setItem('emailCampaignUserName', userName);
    }
}
```

**3. Load from localStorage:**
```javascript
function loadUserName() {
    const savedName = localStorage.getItem('emailCampaignUserName');
    if (savedName) {
        document.getElementById('userName').value = savedName;
    }
}

window.onload = () => {
    loadUserName();  // Auto-fill on page load
};
```

**4. Send to Backend:**
```javascript
async function sendCampaign() {
    const userName = document.getElementById('userName').value.trim() || 'Web User';
    
    const campaign = {
        campaign_name: '...',
        subject: '...',
        body: '...',
        launched_by: userName,  // ← User identity
        // ... other fields
    };
    
    await fetch('/campaign', {
        method: 'POST',
        body: JSON.stringify(campaign)
    });
}
```

### Backend (Python Lambda)

**Capture User Info:**
```python
def send_campaign(body, headers, event=None):
    # Get user name from request body
    launched_by = body.get('launched_by', 'Web User')
    
    # Append IP address from API Gateway context
    if event and 'requestContext' in event:
        identity = event['requestContext'].get('identity', {})
        source_ip = identity.get('sourceIp', 'Unknown')
        launched_by = f"{launched_by} (IP: {source_ip})"
    
    # Store in campaign record
    campaign_item = {
        'campaign_id': campaign_id,
        'campaign_name': body.get('campaign_name'),
        'launched_by': launched_by,  # ← Combined user + IP
        # ... other fields
    }
    
    campaigns_table.put_item(Item=campaign_item)
```

**DynamoDB Record:**
```json
{
  "campaign_id": "campaign_1728057600",
  "campaign_name": "Security Update",
  "launched_by": "John Smith (IP: 192.168.1.100)",
  "created_at": "2025-10-04T10:00:00",
  "sent_at": "2025-10-04T10:05:23",
  ...
}
```

---

## User Instructions

### For End Users:

**First Time Setup (One-Time):**
1. Open Web UI
2. Go to "Send Campaign" tab
3. Enter your name in "Your Name" field
4. Your name is now saved in your browser

**Every Time You Send a Campaign:**
1. Your name auto-fills (no need to re-enter)
2. Fill out campaign as usual
3. Click "Send Campaign"
4. Your name is recorded with the campaign

**To Change Your Name:**
1. Edit the "Your Name" field
2. New name is automatically saved
3. Future campaigns use the new name

**Privacy Note:**
- Name is stored only in **your browser** (localStorage)
- Cleared if you clear browser data
- Each browser/computer is independent

### For Administrators:

**View Who Sent Campaigns:**
```bash
# Launch tracking GUI
python campaign_tracking_gui.py

# Or use CLI
python campaign_tracking_report.py list
```

**Export for Auditing:**
```bash
# Export all campaigns with user info
python campaign_tracking_report.py export-all audit_report.csv
```

**Query by User:**
```bash
# Use DynamoDB Manager
python dynamodb_manager_gui.py
# Select EmailCampaigns
# Advanced Query → Filter by "launched_by"
```

---

## Data Captured

### Three Sources of Identity:

| Source | Example | Captured By | Always Available? |
|--------|---------|-------------|-------------------|
| **Browser Name** | "John Smith" | Web UI form | ✅ Yes (if user enters) |
| **IP Address** | "192.168.1.100" | API Gateway | ✅ Yes (automatic) |
| **User Agent** | "Mozilla/5.0..." | API Gateway | ✅ Yes (not displayed) |

### Final Format:

**With User Name:**
```
"John Smith (IP: 192.168.1.100)"
```

**Without User Name (default):**
```
"Web User (IP: 192.168.1.100)"
```

---

## Advantages of This Approach

### ✅ Benefits:

1. **No Authentication Required**
   - No login system needed
   - No password management
   - Works immediately

2. **User-Friendly**
   - Enter name once, auto-fills forever
   - Stored in browser (like form auto-fill)
   - No additional steps

3. **Accountability**
   - Clear record of who sent what
   - IP address for verification
   - Timestamp for when

4. **Privacy-Conscious**
   - Name stays in user's browser
   - Only sent when sending campaigns
   - User controls their identity

5. **Audit Trail**
   - All campaigns tracked
   - Exportable to CSV
   - Searchable/filterable

### ⚠️ Limitations:

1. **Honor System**
   - Users can enter any name
   - No verification
   - Trust-based

2. **Browser-Specific**
   - Each browser stores separately
   - Cleared with browser data
   - Not shared across devices

3. **No Role-Based Access**
   - No permissions system
   - Everyone can send campaigns
   - No approval workflow

---

## Future Enhancements (Optional)

### Potential Upgrades:

**1. AWS Cognito Integration**
```javascript
// Replace browser localStorage with Cognito
const user = await Auth.currentAuthenticatedUser();
const userName = user.attributes.name;
```

**2. Active Directory Integration**
```python
# Backend LDAP lookup
user_info = ldap.lookup(source_ip)
launched_by = f"{user_info['name']} ({user_info['email']})"
```

**3. API Key Authentication**
```javascript
// Users get personal API keys
headers: {
    'X-API-Key': 'user_api_key_here'
}
```

**4. SSO (Single Sign-On)**
```javascript
// SAML or OAuth integration
const user = await getSSOUser();
```

---

## Troubleshooting

### Issue: Name Field is Empty

**Cause:** First time user, or browser data cleared

**Solution:**
1. Enter your name in the field
2. It will auto-save
3. Refresh page to verify

### Issue: Wrong Name Appears

**Cause:** Previous user on same browser

**Solution:**
1. Clear the field
2. Enter correct name
3. Will save new name

### Issue: Name Not Showing in Reports

**Cause:** Campaign sent before this feature

**Solution:**
- Old campaigns show "Web User (IP: ...)"
- New campaigns show full name
- Re-send campaign if needed

### Issue: Multiple Users Same Browser

**Cause:** Shared computer/browser

**Solution:**
- Each user should change name before sending
- Or use different browser profiles
- Or implement proper authentication

---

## Testing

### Test the Feature:

**1. Enter Name:**
```
1. Open Web UI
2. Go to Send Campaign tab
3. Enter "Test User" in Your Name field
4. Send a test campaign
```

**2. Verify Storage:**
```
1. Open browser console (F12)
2. Type: localStorage.getItem('emailCampaignUserName')
3. Should show: "Test User"
```

**3. Verify Auto-Fill:**
```
1. Refresh the page (F5)
2. Go to Send Campaign tab
3. Your Name field should say "Test User"
```

**4. Verify in Campaign:**
```
1. Launch campaign_tracking_gui.py
2. Find your test campaign
3. Launched By should show: "Test User (IP: ...)"
```

**5. Verify in Export:**
```
1. Export campaign to CSV
2. Check "Launched By" row
3. Should show: "Test User (IP: ...)"
```

---

## Security Considerations

### Current Security:

✅ **HTTPS**: Data encrypted in transit  
✅ **IP Logging**: Source IP tracked  
⚠️ **Trust-Based**: No verification of identity  
⚠️ **No Auth**: Anyone with URL can access  

### Recommendations for Production:

1. **Add Authentication**
   - AWS Cognito user pools
   - Active Directory integration
   - API key authentication

2. **Network Restrictions**
   - VPC endpoints
   - IP whitelisting
   - VPN requirement

3. **Audit Logging**
   - CloudWatch logging
   - CloudTrail events
   - DynamoDB streams

4. **Access Control**
   - IAM roles
   - API Gateway authorizers
   - Lambda function policies

---

## Summary

### What Changed:

| Component | Change | Impact |
|-----------|--------|--------|
| **Web UI** | Added "Your Name" field | Users identify themselves |
| **JavaScript** | localStorage save/load | Name persists across sessions |
| **API Payload** | Added `launched_by` field | Name sent to backend |
| **Lambda** | Enhanced user capture | Combined name + IP |
| **DynamoDB** | Stores `launched_by` | Permanent record |
| **Tracking Tools** | Display user info | Visible in reports |

### User Flow:

```
1. User opens Web UI
   └─> Name auto-fills from localStorage
   
2. User fills campaign form
   └─> Enters or keeps existing name
   
3. User clicks "Send Campaign"
   └─> Name sent to backend
   
4. Backend processes campaign
   └─> Appends IP address
   └─> Stores in DynamoDB
   
5. Campaign tracked forever
   └─> Visible in GUI
   └─> Exportable to CSV
   └─> Searchable/filterable
```

---

## Quick Reference

### Files Modified:
- `bulk_email_api_lambda.py` (Web UI + backend)

### New Functions:
- `saveUserName()` - Save to localStorage
- `loadUserName()` - Load from localStorage

### HTML Added:
- "Your Name" input field

### API Changed:
- Campaign POST now includes `launched_by`

### DynamoDB Field:
- `launched_by` (String) in EmailCampaigns

### Tracking Tools:
- All tools now display `launched_by`

---

**User identity is now fully captured!** 👤✅

Every campaign records who launched it with their name and IP address.

