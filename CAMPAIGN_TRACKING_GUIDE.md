```markdown
# 📊 Campaign Tracking System - Complete Guide

## Overview
Comprehensive campaign tracking system that records and displays detailed information about every email campaign, including who launched it, when emails were sent, and which email addresses received the campaign.

## Features

### 🎯 Campaign Tracking Data
Each campaign automatically tracks:
- **Campaign ID**: Unique identifier
- **Campaign Name**: User-defined campaign name
- **Launched By**: User who initiated the campaign (with IP address)
- **Created At**: When campaign was created
- **Sent At**: When first email was actually sent
- **Status**: Current status (queued/sending/completed/failed)
- **Target Contacts**: Complete list of recipient email addresses
- **Statistics**: Total contacts, successfully sent, failed
- **Filter Details**: What filters were applied
- **Attachments**: List of attached files

### 🔧 Tools Available

#### 1. Campaign Tracking GUI (Recommended)
**File:** `campaign_tracking_gui.py`  
**Launcher:** `launch_campaign_tracking.bat`

Visual dashboard for campaign analytics with:
- ✅ Sortable campaign list with all key metrics
- ✅ Detailed campaign view (summary, recipients, raw JSON)
- ✅ Search and filter capabilities
- ✅ Export to CSV (individual campaign or all campaigns)
- ✅ Real-time status updates
- ✅ Multi-region support

#### 2. Command-Line Report Tool
**File:** `campaign_tracking_report.py`

Terminal-based tool with interactive menu:
- ✅ List all campaigns
- ✅ View campaign details
- ✅ Export recipient lists to CSV
- ✅ Search by name or status
- ✅ Batch export all campaigns

#### 3. DynamoDB Manager
**File:** `dynamodb_manager_gui.py`

Full database access to EmailCampaigns table:
- ✅ Query campaigns by any field
- ✅ Edit campaign records
- ✅ Bulk operations
- ✅ Advanced filtering

---

## Quick Start

### Launch Campaign Tracking GUI
```bash
# Method 1: Direct launch
python campaign_tracking_gui.py

# Method 2: Windows launcher
launch_campaign_tracking.bat
```

### Use Command-Line Tool
```bash
# Interactive menu
python campaign_tracking_report.py

# Quick commands
python campaign_tracking_report.py list
python campaign_tracking_report.py detail campaign_1234567890
python campaign_tracking_report.py export campaign_1234567890
python campaign_tracking_report.py export-all
```

---

## Campaign Tracking GUI

### Main Dashboard

**Campaign List View:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Campaign ID    │ Name       │ Launched By │ Status │ Sent/Total │
├─────────────────────────────────────────────────────────────────┤
│ campaign_12345 │ Weekly...  │ Web User... │ sent   │ 150/150    │
│ campaign_12344 │ Security...│ Admin...    │ queued │ 0/200      │
└─────────────────────────────────────────────────────────────────┘
```

**Detail Tabs:**
1. **📊 Summary**: Campaign metadata, statistics, attachments
2. **📧 Recipients**: Complete list of all recipient email addresses
3. **🔧 Raw JSON**: Full campaign data in JSON format

### Toolbar Functions

| Button | Function |
|--------|----------|
| 🔄 Refresh | Reload campaigns from DynamoDB |
| 📥 Export Campaign to CSV | Export selected campaign (full report with metadata) |
| 📧 Export Email List Only | Export just the email addresses (one per row) |
| 📊 Export All to CSV | Export all campaigns summary |
| 🔍 Filter by Status | Show only campaigns with specific status |
| 🗑️ Clear Filter | Show all campaigns |
| Search Box | Search campaigns by name |

### Workflow Example

**View Recent Campaign:**
1. Launch GUI
2. Campaigns load automatically (sorted by date, newest first)
3. Click on campaign in list
4. View details in tabs below

**Export Recipient List:**

*Option 1: Full Report*
1. Select campaign from list
2. Click "📥 Export Campaign to CSV"
3. Choose filename and location
4. CSV includes campaign metadata + all recipient emails (with row numbers)

*Option 2: Email List Only*
1. Select campaign from list
2. Click "📧 Export Email List Only"
3. Choose filename and location
4. CSV includes ONLY email addresses (one per row, no metadata)

**Filter Campaigns:**
1. Click "🔍 Filter by Status"
2. Enter status (e.g., "completed")
3. View filtered list
4. Click "🗑️ Clear Filter" to see all

---

## Command-Line Tool

### Interactive Menu

```bash
python campaign_tracking_report.py
```

Menu Options:
```
1. View All Campaigns (Summary)           - Table view of all campaigns
2. View Campaign Details (by ID)          - Detailed single campaign view
3. View Recent Campaigns (last 10)        - Most recent 10 campaigns
4. Export Campaign Recipients to CSV      - Export single campaign (full report)
5. Export Email List Only                 - Export just email addresses
6. Export All Campaigns Summary to CSV    - Export all campaigns
7. Search Campaigns by Name               - Search by campaign name
8. View Campaigns by Status               - Filter by status
9. Change Region                          - Switch AWS region
10. Exit                                  - Quit application
```

### Command-Line Usage

**List All Campaigns:**
```bash
python campaign_tracking_report.py list
```
Output:
```
================================================================================
ID                   Campaign Name           Launched By        Status    Sent
================================================================================
campaign_1234567890  Weekly Security Update  Web User (IP:...  completed 150
campaign_1234567889  Monthly Newsletter      Admin User        completed 200
================================================================================
```

**View Campaign Details:**
```bash
python campaign_tracking_report.py detail campaign_1234567890
```
Output:
```
================================================================================
📊 CAMPAIGN DETAILS
================================================================================
Campaign ID:       campaign_1234567890
Campaign Name:     Weekly Security Update
Launched By:       Web User (IP: 192.168.1.100)
Created At:        2025-10-04T10:30:00
Sent At:           2025-10-04T10:35:00
Status:            completed
--------------------------------------------------------------------------------
Target Filter:     Group: IT Staff, Security Team
Total Contacts:    150
Successfully Sent: 150
Failed:            0
--------------------------------------------------------------------------------

📧 RECIPIENT EMAIL ADDRESSES (150 total):
--------------------------------------------------------------------------------
    1. user1@example.com
    2. user2@example.com
    ...
================================================================================
```

**Export Campaign (Full Report):**
```bash
python campaign_tracking_report.py export campaign_1234567890 my_report.csv
```

**Export Email List Only:**
```bash
python campaign_tracking_report.py export-emails campaign_1234567890 email_list.csv
```

**Export All Campaigns:**
```bash
python campaign_tracking_report.py export-all all_campaigns.csv
```

---

## CSV Export Formats

### Individual Campaign Export

**Format:**
```csv
Campaign Report
Campaign ID,campaign_1234567890
Campaign Name,Weekly Security Update
Launched By,Web User (IP: 192.168.1.100)
Created At,2025-10-04T10:30:00
Sent At,2025-10-04T10:35:00
Status,completed
Total Recipients,150
Successfully Sent,150
Failed,0

Recipient Email Addresses
#,Email Address
1,user1@example.com
2,user2@example.com
...
```

### Email List Only Export

**Format:**
```csv
Email Addresses for Campaign: Weekly Security Update
Campaign ID: campaign_1234567890
Total Recipients: 150
Exported: 2025-10-04 11:00:00

Email Address
user1@example.com
user2@example.com
user3@example.com
...
```

**Use Case:**
- Import into another system
- Create mailing list
- Verify recipients
- Generate distribution list
- Bulk operations on email addresses

### All Campaigns Summary Export

**Format:**
```csv
Campaign ID,Campaign Name,Launched By,Created At,Sent At,Status,Filter Description,Total Contacts,Successfully Sent,Failed,Recipient Count
campaign_1234567890,Weekly Security Update,Web User (IP: 192...),2025-10-04T10:30:00,2025-10-04T10:35:00,completed,Group: IT Staff,150,150,0,150
campaign_1234567889,Monthly Newsletter,Admin User,2025-10-03T09:00:00,2025-10-03T09:05:00,completed,All Contacts,200,198,2,200
```

---

## How Campaign Tracking Works

### Automatic Data Collection

**When You Send a Campaign:**
1. User fills out campaign form in Web UI
2. Clicks "🚀 Send Campaign"
3. System automatically records:
   - Campaign name (from form)
   - User identifier (from request context + IP address)
   - Current timestamp as "created_at"
   - All filter criteria
   - Complete list of target email addresses
   - Campaign configuration

**When Emails Are Sent:**
1. Email worker Lambda processes SQS queue
2. For each successfully sent email:
   - Increments "sent_count"
   - Sets "sent_at" timestamp (first email only)
   - Updates status to "sending"
3. Tracks failed emails in "failed_count"

### Data Storage

**DynamoDB Table:** `EmailCampaigns`

**Schema:**
```json
{
  "campaign_id": "campaign_1234567890",          // Primary key
  "campaign_name": "Weekly Security Update",     // User-defined
  "launched_by": "Web User (IP: 192.168.1.100)", // Auto-captured
  "created_at": "2025-10-04T10:30:00",          // When created
  "sent_at": "2025-10-04T10:35:00",             // When first sent
  "status": "completed",                         // Current status
  "subject": "Important Security Update",
  "body": "<html>...</html>",
  "from_email": "security@agency.gov",
  "filter_description": "Group: IT Staff, Security Team",
  "filter_type": "group",
  "filter_values": ["IT Staff", "Security Team"],
  "target_contacts": [                           // All recipient emails
    "user1@example.com",
    "user2@example.com",
    ...
  ],
  "total_contacts": 150,
  "sent_count": 150,
  "failed_count": 0,
  "attachments": []
}
```

---

## Common Use Cases

### 1. Verify Campaign Recipients

**Question:** "Who received the security update I sent yesterday?"

**Solution:**
```bash
# GUI Method:
1. Launch campaign_tracking_gui.py
2. Search for campaign by name
3. Click on campaign
4. View Recipients tab
5. Export to CSV if needed

# CLI Method:
python campaign_tracking_report.py
> Select option 6 (Search by name)
> Enter "security update"
> Select option 2 (View details)
> View recipient list
```

### 2. Audit Campaign Activity

**Question:** "Show me all campaigns sent by a specific user"

**Solution:**
```bash
# GUI Method:
1. Launch campaign_tracking_gui.py
2. Load all campaigns
3. Manually search/filter (user field visible)
4. Export filtered results

# DynamoDB Manager:
1. Launch dynamodb_manager_gui.py
2. Select EmailCampaigns table
3. Use Advanced Query tab
4. Filter by "launched_by" field
```

### 3. Compliance Reporting

**Question:** "Generate monthly report of all campaigns sent"

**Solution:**
```bash
# Export all campaigns for the month
python campaign_tracking_report.py export-all monthly_report_2025_10.csv

# Or use GUI:
1. Launch campaign_tracking_gui.py
2. Filter by date range (manually)
3. Click "📊 Export All to CSV"
4. Submit report with CSV attachment
```

### 4. Troubleshoot Failed Campaign

**Question:** "Why did some emails fail in my campaign?"

**Solution:**
```bash
# View campaign details
python campaign_tracking_report.py detail campaign_1234567890

# Check:
- Status field (queued/sending/failed)
- Failed count
- Compare target_contacts with sent_count
- Review CloudWatch logs for worker Lambda
```

### 5. Resend to Failed Recipients

**Question:** "How do I resend to people who didn't get the email?"

**Solution:**
```bash
# Current system doesn't auto-resend, but you can:
1. Export campaign recipients to CSV
2. Check EmailCampaigns table for failed_count
3. Review CloudWatch logs for specific failures
4. Create new campaign with failed recipients
```

---

## Integration with Other Tools

### Web UI → Campaign Tracking
When you send a campaign from the Web UI:
- Campaign is automatically logged
- All tracking data captured
- View results in Campaign Tracking GUI

### Email Worker → Campaign Updates
As emails are sent:
- sent_count incremented in real-time
- sent_at timestamp set on first email
- Status updated (queued → sending → completed)

### DynamoDB Manager → Advanced Queries
For complex queries:
- Use DynamoDB Manager GUI
- Query EmailCampaigns table
- Apply custom filters
- Export results

---

## Troubleshooting

### Issue: Campaigns Not Showing

**Checks:**
```bash
# 1. Verify table exists
aws dynamodb describe-table --table-name EmailCampaigns --region us-gov-west-1

# 2. Check if campaigns exist
aws dynamodb scan --table-name EmailCampaigns --region us-gov-west-1 --limit 5

# 3. Verify correct region in GUI
```

### Issue: sent_at is Null

**Explanation:**
- `sent_at` is only set when first email is actually sent
- If status is "queued", emails haven't been processed yet
- Check SQS queue and email worker Lambda

**Solution:**
```bash
# Check SQS queue
aws sqs get-queue-attributes --queue-url https://... --attribute-names All

# Check Lambda logs
aws logs tail /aws/lambda/email-worker --follow
```

### Issue: Missing Recipient Emails

**Explanation:**
- `target_contacts` array stores emails at campaign creation
- If empty, check campaign creation logic

**Solution:**
- Review bulk_email_api_lambda.py send_campaign function
- Verify contact filter logic
- Check contacts were loaded before sending

### Issue: launched_by Shows "Unknown"

**Explanation:**
- launched_by comes from request context
- May not be available in all environments

**Solution:**
- Update bulk_email_api_lambda.py to pass user info
- Consider adding user authentication
- For now, shows IP address in parentheses

---

## Advanced Features

### Custom User Tracking

To capture specific user info, modify `bulk_email_api_lambda.py`:

```python
# Add to send_campaign function:
launched_by = body.get('launched_by', 'Web User')

# Then in Web UI, add to sendCampaign():
const payload = {
    campaign_name: campaignName,
    launched_by: 'Your User Name Here',  // Add this
    ...
};
```

### Campaign Status Tracking

Status progression:
1. **queued**: Campaign created, messages in SQS
2. **sending**: First email sent, worker processing
3. **completed**: All emails processed (check sent_count vs total_contacts)
4. **failed**: Critical failure (check logs)

### Automated Reports

Create scheduled reports:

```bash
# Create cron job or scheduled task
# Daily export:
0 0 * * * python campaign_tracking_report.py export-all /reports/daily_$(date +\%Y\%m\%d).csv

# Weekly summary:
0 0 * * 0 python campaign_tracking_report.py list > /reports/weekly_$(date +\%Y\%m\%d).txt
```

---

## Best Practices

### 1. Regular Audits
- Review campaigns weekly
- Export monthly summaries for records
- Check for unusual patterns

### 2. Naming Conventions
Use consistent campaign names:
```
[Type] [Date] - [Brief Description]
Examples:
- "Security 2025-10 - Phishing Alert"
- "Newsletter 2025-10 - October Updates"
- "Test 2025-10 - Load Testing"
```

### 3. Data Retention
- Export campaigns periodically for archival
- Consider implementing data retention policy
- Keep CSV exports for compliance

### 4. User Identification
- Add user authentication to Web UI
- Pass username in launched_by field
- Log actions for accountability

---

## Quick Reference

### Launch Tools
```bash
# GUI (Recommended)
python campaign_tracking_gui.py

# CLI Interactive
python campaign_tracking_report.py

# CLI Commands
python campaign_tracking_report.py list
python campaign_tracking_report.py detail <campaign_id>
python campaign_tracking_report.py export <campaign_id>
python campaign_tracking_report.py export-all
```

### Query DynamoDB Directly
```bash
# List all campaigns
aws dynamodb scan --table-name EmailCampaigns --region us-gov-west-1

# Get specific campaign
aws dynamodb get-item --table-name EmailCampaigns --key '{"campaign_id":{"S":"campaign_1234567890"}}' --region us-gov-west-1

# Count campaigns
aws dynamodb scan --table-name EmailCampaigns --select COUNT --region us-gov-west-1
```

### Export Formats
- **Individual Campaign**: Metadata + recipient list
- **All Campaigns**: Summary table with key metrics
- **DynamoDB Manager**: Custom queries with flexible export

---

## Support & Help

### Quick Help
- **GUI**: Hover over buttons for descriptions
- **CLI**: Run with no arguments for interactive menu
- **Status Bar**: Shows current operation status

### Resources
- This guide: `CAMPAIGN_TRACKING_GUIDE.md`
- DynamoDB Manager: `DYNAMODB_MANAGER_GUIDE.md`
- General docs: `GUI_TOOLS_INDEX.md`
- AWS DynamoDB docs

---

**Track Every Campaign!** 📊
```

