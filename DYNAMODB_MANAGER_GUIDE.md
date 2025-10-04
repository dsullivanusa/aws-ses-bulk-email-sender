# 🗄️ DynamoDB Manager GUI - Complete User Guide

## Overview
A comprehensive GUI application for managing all DynamoDB tables in your AWS SES Email Campaign project. This tool provides full CRUD (Create, Read, Update, Delete) operations with an intuitive interface.

## Features

### 🎯 Core Capabilities
- **Browse Data**: View all records with pagination and filtering
- **Advanced Query**: Build complex queries with filters
- **Edit Records**: Update records with JSON editor and validation
- **Bulk Operations**: Export and bulk delete capabilities
- **Multi-Table Support**: Works with all project tables
- **Real-time Updates**: Immediate feedback on all operations

### 📊 Supported Tables
- **EmailContacts** / **EmailContactsNew**: Contact management
- **EmailCampaigns**: Campaign tracking
- **EmailConfig**: Email configuration
- **SMTPConfig**: SMTP settings

## Getting Started

### Installation Requirements
```bash
pip install boto3
# tkinter is usually included with Python
```

### Launch the Application

**Method 1: Direct Launch**
```bash
python dynamodb_manager_gui.py
```

**Method 2: Windows Launcher**
```
Double-click: launch_db_manager.bat
```

## User Interface

### 🔝 Header Section
- **Region Selector**: Choose AWS region (us-gov-west-1, us-east-1, us-west-2)
- **Table Selector**: Select which table to work with
- **Refresh Tables**: Update available tables list
- **Connection Status**: Shows DynamoDB connection state (🟢 Connected / 🔴 Failed)

### 📑 Tabs Overview

#### 1. 📊 Browse Data Tab
View and manage records in a spreadsheet-like interface.

**Features:**
- **Load All Records**: Fetch all records from selected table
- **Edit Selected**: Open record in edit tab (or double-click row)
- **Delete Selected**: Remove a single record
- **Delete All Rows**: Remove ALL records from table (with double confirmation)
- **Export to CSV**: Save current view to CSV file
- **Right-Click Menu**: Context menu with Edit, Delete, Copy options

**Quick Search:**
- Select field to search
- Enter search value
- Click Search to filter results
- Click Clear to show all records

**Record Details:**
- Click any row to view full JSON in detail panel
- View complete record data with formatting

#### 2. 🔎 Advanced Query Tab
Build and execute complex DynamoDB queries.

**Query Builder:**
- **Primary Key Query**:
  - Enter primary key name (e.g., `contact_id`, `email`)
  - Enter value to search
  - Click Execute Query

- **Filter Attributes**:
  - Choose attribute to filter on
  - Select operator (=, !=, <, <=, >, >=, contains, begins_with)
  - Enter filter value
  - Click Execute Query

**Operations:**
- 🔍 **Execute Query**: Run the built query
- 📊 **Scan Table**: Load all records (no filters)
- ❌ **Clear Query**: Reset all fields

**Results:**
- JSON-formatted results in scrollable panel
- Record count in status bar

#### 3. ✏️ Edit Record Tab
Update existing records with JSON editing.

**Workflow:**
1. **Load Record**:
   - Enter primary key name and value
   - Click "Load Record"
   - OR select from Browse tab

2. **Edit JSON**:
   - Modify JSON directly in editor
   - Use proper JSON syntax
   - Click "Validate JSON" to check syntax

3. **Save Changes**:
   - Click "Save Changes"
   - Confirm the update
   - Record is updated in DynamoDB

**Buttons:**
- 💾 **Save Changes**: Write updates to database
- ❌ **Cancel**: Discard changes
- ✅ **Validate JSON**: Check JSON syntax before saving

#### 4. ⚡ Bulk Operations Tab
Perform operations on multiple records.

**⚠️ Warning**: Bulk operations affect multiple records and cannot be undone!

**Bulk Delete:**
- Enter attribute name
- Enter value to match
- Click "Execute Bulk Delete"
- Confirm twice (safety measure)
- All matching records are deleted

**Export Table:**
- 📥 **Export to JSON**: Save entire table as JSON
- 📥 **Export to CSV**: Save entire table as CSV
- Choose filename and location
- All records exported with pagination handling

**Table Information:**
- View complete table schema
- See key definitions
- Check table status and metadata
- Click "Refresh Table Info" to update

## Common Operations

### 🔍 Searching for Records

**Quick Search (Browse Tab):**
```
1. Select table (e.g., EmailContacts)
2. Click "Load All Records"
3. Select search field (e.g., "email")
4. Enter search value (e.g., "test@example.com")
5. Click Search
```

**Advanced Query (Query Tab):**
```
1. Select table
2. Enter primary key (e.g., contact_id)
3. Enter value
4. Click "Execute Query"
```

### ✏️ Updating a Record

**Method 1: From Browse Tab**
```
1. Load records
2. Click on record to select
3. Click "Edit Selected"
4. Modify JSON in Edit tab
5. Click "Save Changes"
```

**Method 2: Direct Edit**
```
1. Go to Edit tab
2. Enter primary key and value
3. Click "Load Record"
4. Modify JSON
5. Click "Save Changes"
```

### 🗑️ Deleting Records

**Single Record:**
```
1. Browse tab → Load records
2. Select record to delete
3. Click "Delete Selected"
4. Confirm deletion
```

**All Records in Table:**
```
1. Browse tab → Select table
2. Click "💥 Delete All Rows"
3. Review count
4. Confirm deletion (first warning)
5. Type table name to confirm (second warning)
6. All records deleted with progress tracking
```

**Multiple Records (Filtered):**
```
1. Bulk Operations tab
2. Enter filter attribute and value
3. Click "Execute Bulk Delete"
4. Review count and confirm twice
```

### 📤 Exporting Data

**Export Current View:**
```
1. Browse tab → Load and filter records
2. Click "Export to CSV"
3. Choose filename and save
```

**Export Entire Table:**
```
1. Bulk Operations tab
2. Click "Export to JSON" or "Export to CSV"
3. Choose filename and save
4. Wait for all records to load (shows progress)
```

## Data Formats

### EmailContacts / EmailContactsNew
```json
{
  "contact_id": "uuid-string",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "title": "IT Director",
  "entity_type": "State Government",
  "state": "CA",
  "agency_name": "Department of Technology",
  "sector": "Government",
  "subsection": "IT Services",
  "phone": "555-0100",
  "ms_isac_member": "Yes",
  "soc_call": "Yes",
  "fusion_center": "No",
  "k12": "No",
  "water_wastewater": "No",
  "weekly_rollup": "Yes",
  "alternate_email": "john.alt@example.com",
  "region": "West",
  "created_at": "2025-01-15T10:30:00"
}
```

### EmailCampaigns
```json
{
  "campaign_id": "uuid-string",
  "campaign_name": "Weekly Security Update",
  "subject": "Security Alert - Action Required",
  "body": "HTML email body...",
  "sender_email": "security@agency.gov",
  "status": "completed",
  "target_contacts": ["email1@example.com", "email2@example.com"],
  "filter_type": "group",
  "filter_values": ["IT Staff", "Security Team"],
  "total_sent": 150,
  "created_at": "2025-01-15T09:00:00",
  "attachments": []
}
```

### EmailConfig / SMTPConfig
```json
{
  "config_id": "default",
  "sender_email": "noreply@agency.gov",
  "sender_name": "Security Team",
  "reply_to": "support@agency.gov",
  "created_at": "2025-01-01T00:00:00"
}
```

## Tips & Best Practices

### 🎯 Performance Tips
1. **Use Filters**: Don't load all 20,000 contacts; filter first
2. **Query by Key**: Primary key queries are fastest
3. **Export in Batches**: For large exports, consider filtering first
4. **Close When Done**: Reduces AWS API calls

### 🛡️ Safety Tips
1. **Test Queries First**: Use Execute Query before bulk operations
2. **Export Before Delete**: Always export data before bulk deletes
3. **Validate JSON**: Always validate before saving edits
4. **Double-Check Keys**: Ensure correct primary key for edits/deletes

### 💡 Productivity Tips
1. **Use Quick Search**: Faster than advanced queries for simple searches
2. **Keep Detail Panel Open**: Easy reference while browsing
3. **Export for Analysis**: Export to CSV for Excel analysis
4. **Save Common Queries**: Keep a note of frequently used queries

## Troubleshooting

### Issue: "Not Connected" Status
**Solutions:**
- Check AWS credentials: `aws configure`
- Verify region selection
- Test connection: `aws dynamodb list-tables --region us-gov-west-1`
- Check IAM permissions

### Issue: Table Not Found
**Solutions:**
- Click "Refresh Tables"
- Verify table exists in AWS Console
- Check correct region is selected
- Ensure table name matches exactly

### Issue: Permission Denied
**Required IAM Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:Scan",
    "dynamodb:Query",
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:DescribeTable",
    "dynamodb:ListTables"
  ],
  "Resource": "*"
}
```

### Issue: JSON Validation Fails
**Common Mistakes:**
- Missing commas between fields
- Extra comma after last field
- Unquoted strings
- Single quotes instead of double quotes
- Missing closing braces/brackets

**Valid JSON:**
```json
{
  "field1": "value1",
  "field2": "value2",
  "field3": 123
}
```

### Issue: Bulk Delete Not Working
**Checks:**
- Verify attribute name matches exactly (case-sensitive)
- Check value format (string vs number)
- Ensure records exist with that attribute
- Confirm table has proper keys defined

### Issue: Export Takes Too Long
**Solutions:**
- Filter data first, then export
- Use Browse tab export for smaller sets
- Check network connection
- Verify no rate limiting on AWS account

## Keyboard Shortcuts & Mouse Actions

### Keyboard Shortcuts:
- **Ctrl+R**: Refresh current view
- **Ctrl+F**: Focus search field
- **Ctrl+S**: Save (when in Edit tab)
- **Delete**: Delete selected record
- **Escape**: Cancel/Clear current operation

### Mouse Actions:
- **Double-Click Row**: Open record in Edit tab
- **Right-Click Row**: Show context menu (Edit, Delete, Copy)
- **Single Click Row**: View details in detail panel

## Advanced Features

### Custom Queries
Build complex filter expressions using the Query Builder:

**Contains Search:**
```
Attribute: email
Operator: contains
Value: @example.com
```

**Begins With:**
```
Attribute: last_name
Operator: begins_with
Value: Smith
```

**Range Query:**
```
Attribute: created_at
Operator: >=
Value: 2025-01-01
```

### JSON Editing Tips

**Adding New Fields:**
```json
{
  "existing_field": "value",
  "new_field": "new value"
}
```

**Updating Arrays:**
```json
{
  "attachments": [
    {"name": "file1.pdf", "size": 1024},
    {"name": "file2.pdf", "size": 2048}
  ]
}
```

**Nested Objects:**
```json
{
  "metadata": {
    "created_by": "admin",
    "modified_at": "2025-01-15T10:30:00"
  }
}
```

## Integration with Project

### Verify Campaign Recipients
```
1. Select EmailCampaigns table
2. Query by campaign_id
3. View target_contacts array
4. Export to CSV for reporting
```

### Clean Test Data
```
1. Select EmailContactsNew table
2. Bulk Operations → Bulk Delete
3. Attribute: email
4. Value: test@example.com
5. Confirm deletion
```

### Audit Configuration
```
1. Select EmailConfig table
2. Load All Records
3. Review sender settings
4. Export for documentation
```

### Monitor Campaign Status
```
1. Select EmailCampaigns table
2. Filter by status = "completed"
3. View total_sent counts
4. Export for metrics
```

## Safety Checklist

Before performing destructive operations:

- [ ] Selected correct table
- [ ] Selected correct region
- [ ] Reviewed records to delete/update
- [ ] Exported backup (if needed)
- [ ] Confirmed with team (if production)
- [ ] Double-checked key values
- [ ] Validated JSON syntax (for updates)
- [ ] Tested query first (for bulk operations)

## Support & Help

### Quick Help
- Hover over buttons for tooltips
- Check status bar for operation feedback
- Review Detail Panel for record structure

### Resources
- AWS DynamoDB Documentation
- Project README files
- Error messages in pop-up dialogs

### Common Questions

**Q: Can I undo a delete?**
A: No, deletes are permanent. Always export backups first.

**Q: How many records can I load at once?**
A: No hard limit, but 1000+ may be slow. Use filters for better performance.

**Q: Can I add new records?**
A: Yes, use Edit tab with a new primary key value and JSON.

**Q: Will this affect my production data?**
A: Yes! Always verify region and table before operations.

---

## Quick Reference Card

### Essential Operations

| Action | Location | Steps |
|--------|----------|-------|
| View Records | Browse → Load All Records | 1. Select table<br>2. Click Load All |
| Search | Browse → Quick Search | 1. Choose field<br>2. Enter value<br>3. Click Search |
| Edit | Browse → Select → Edit | 1. Select record<br>2. Edit Selected<br>3. Modify JSON<br>4. Save |
| Delete | Browse → Select → Delete | 1. Select record<br>2. Delete Selected<br>3. Confirm |
| Export | Browse → Export to CSV | 1. Load/filter data<br>2. Click Export |
| Query | Query → Query Builder | 1. Set filters<br>2. Execute Query |
| Bulk Delete | Bulk → Bulk Delete | 1. Set criteria<br>2. Confirm twice |

---

**Ready to manage your DynamoDB tables!** 🗄️

