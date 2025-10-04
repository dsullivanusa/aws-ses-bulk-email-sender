# 🎨 GUI Tools Index - Project Management Suite

## Overview
Complete collection of GUI applications for managing your AWS SES Email Campaign System. All tools are built with Python tkinter for cross-platform compatibility.

---

## 🗄️ 1. DynamoDB Manager GUI

**File:** `dynamodb_manager_gui.py`  
**Launcher:** `launch_db_manager.bat`  
**Guide:** `DYNAMODB_MANAGER_GUIDE.md`

### Purpose
Comprehensive database administration tool for all DynamoDB tables in the project.

### Key Features
- ✅ Browse and search records with filtering
- ✅ Advanced query builder with multiple operators
- ✅ Edit records with JSON validation
- ✅ Delete single or bulk records
- ✅ Export to CSV/JSON
- ✅ View table schemas and metadata
- ✅ Multi-table support (all project tables)

### Use Cases
- View and manage contacts
- Query campaign results
- Update email configurations
- Delete test data
- Export reports
- Audit database records

### Quick Start
```bash
python dynamodb_manager_gui.py
# or
launch_db_manager.bat
```

### Supported Tables
- EmailContacts / EmailContactsNew
- EmailCampaigns
- EmailConfig
- SMTPConfig

---

## 🧪 2. Test Contact Generator GUI

**File:** `generate_test_contacts_gui.py`  
**Launcher:** `launch_test_generator.bat`  
**Guide:** `TEST_GENERATOR_GUI_GUIDE.md`

### Purpose
Generate thousands of test contacts with duplicate emails for load testing.

### Key Features
- ✅ Generate 1-100,000+ test contacts
- ✅ Configurable contact templates
- ✅ Real-time progress tracking
- ✅ Cancellable operations
- ✅ Performance statistics
- ✅ Detailed logging
- ✅ Batch processing (25 items/batch)

### Use Cases
- Load testing email campaigns
- Performance benchmarking
- Database stress testing
- Development data generation

### Quick Start
```bash
python generate_test_contacts_gui.py
# or
launch_test_generator.bat
# or
python generate_test_contacts.py
# Then select option 2 (GUI)
```

### Performance
- **Rate**: 200-400 contacts/second
- **10K contacts**: ~30-50 seconds
- **100K contacts**: ~5-8 minutes

---

## 📧 3. Web UI (Bulk Email Campaign Manager)

**File:** `bulk_email_api_lambda.py` (serves HTML)  
**Access:** Via API Gateway URL or Custom Domain  
**Guides:** `DEPLOYMENT_GUIDE.md`, `QUICKSTART.md`

### Purpose
Web-based interface for managing contacts and sending email campaigns.

### Key Features
- ✅ Contact management (add, edit, delete)
- ✅ CSV bulk import with progress tracking
- ✅ Advanced filtering (checkboxes, multi-select)
- ✅ Name search with DynamoDB integration
- ✅ Rich text email editor (Quill)
- ✅ S3 attachment support (40MB limit)
- ✅ Campaign creation and tracking
- ✅ Test group filtering

### Use Cases
- Daily email campaign management
- Contact database maintenance
- Bulk email operations
- Campaign tracking and reporting

### Access
```bash
# Deploy first
python deploy_complete.py

# Then access via browser
https://your-api-gateway-url/prod/

# Or configure custom domain
See: CUSTOM_DOMAIN_SETUP.md
```

### Main Features

**Contact Management Tab:**
- Add/edit/delete contacts
- CSV import with batch processing
- Multi-filter system (checkboxes)
- Name search (DynamoDB-backed)
- Export contacts

**Send Campaign Tab:**
- Rich text editor
- Attachment upload (S3)
- Filter by multiple criteria
- Test group selection
- Template variables

**View Campaigns Tab:**
- Campaign history
- Sent count tracking
- Filter details
- Recipient lists

---

## 🛠️ Comparison Matrix

| Feature | DynamoDB Manager | Test Generator | Web UI |
|---------|-----------------|----------------|--------|
| **Interface** | Desktop GUI | Desktop GUI | Web Browser |
| **Contact CRUD** | ✅ Full | ❌ Generate Only | ✅ Full |
| **Query Data** | ✅ Advanced | ❌ | ⚠️ Basic |
| **Bulk Operations** | ✅ Yes | ✅ Generate | ✅ CSV Import |
| **Export Data** | ✅ CSV/JSON | ❌ | ✅ CSV |
| **Edit Campaigns** | ✅ JSON | ❌ | ✅ Form |
| **Load Testing** | ❌ | ✅ Yes | ❌ |
| **Send Emails** | ❌ | ❌ | ✅ Yes |
| **Attachments** | ⚠️ View | ❌ | ✅ Upload |
| **Real-time Search** | ✅ Yes | ❌ | ✅ Yes |
| **Offline Use** | ✅ Yes | ✅ Yes | ❌ Needs API |

---

## 🎯 When to Use Each Tool

### Use DynamoDB Manager When...
- ✅ Need to query specific records
- ✅ Want to edit data manually (JSON)
- ✅ Need to bulk delete records
- ✅ Want to export entire tables
- ✅ Debugging data issues
- ✅ Auditing database contents
- ✅ Managing configurations (EmailConfig, SMTPConfig)

### Use Test Generator When...
- ✅ Load testing email system
- ✅ Performance benchmarking
- ✅ Generating large test datasets
- ✅ Stress testing DynamoDB
- ✅ Creating duplicate email scenarios

### Use Web UI When...
- ✅ Daily operational tasks
- ✅ Sending email campaigns
- ✅ Managing contacts regularly
- ✅ Importing contact lists (CSV)
- ✅ Creating campaigns with attachments
- ✅ Team collaboration (multiple users)
- ✅ Production email operations

---

## 🚀 Installation & Setup

### Prerequisites
```bash
# Python 3.7+
python --version

# Install dependencies
pip install boto3

# Configure AWS credentials
aws configure
```

### AWS Permissions Required
All tools need these IAM permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:DescribeTable",
        "dynamodb:ListTables"
      ],
      "Resource": "*"
    }
  ]
}
```

### Launch Each Tool

**DynamoDB Manager:**
```bash
python dynamodb_manager_gui.py
```

**Test Generator:**
```bash
python generate_test_contacts_gui.py
```

**Web UI:**
```bash
# Deploy first
python deploy_complete.py

# Access in browser
https://{api-gateway-url}/prod/
```

---

## 📚 Documentation Index

### General Guides
- `README.md` - Project overview
- `QUICKSTART.md` - Quick start guide
- `DEPLOYMENT_GUIDE.md` - Full deployment instructions
- `FILES_TO_RUN.md` - Script execution order

### GUI Tool Guides
- `DYNAMODB_MANAGER_GUIDE.md` - Database manager manual
- `TEST_GENERATOR_GUI_GUIDE.md` - Test generator manual
- `GUI_TOOLS_INDEX.md` - This file

### Feature-Specific Guides
- `S3_ATTACHMENTS_GUIDE.md` - Email attachment handling
- `BATCH_IMPORT_GUIDE.md` - CSV batch import
- `CSV_IMPORT_GUIDE.md` - CSV troubleshooting
- `CUSTOM_DOMAIN_SETUP.md` - Custom URL setup
- `CONTACT_SCHEMA.md` - Contact data schema

### Technical Guides
- `ARCHITECTURE_UPDATE.md` - System architecture
- `ATTACHMENT_TROUBLESHOOTING.md` - Attachment debugging
- Various `README_*.md` files for specific features

---

## 🔧 Troubleshooting

### Common Issues Across All Tools

**AWS Credentials:**
```bash
# Configure if needed
aws configure

# Test connection
aws dynamodb list-tables --region us-gov-west-1
```

**Python Dependencies:**
```bash
pip install --upgrade boto3
```

**tkinter (for GUI tools):**
```bash
# Usually included, but if missing on Linux:
sudo apt-get install python3-tk
```

### Tool-Specific Issues
See individual guide files for detailed troubleshooting:
- DynamoDB Manager: `DYNAMODB_MANAGER_GUIDE.md`
- Test Generator: `TEST_GENERATOR_GUI_GUIDE.md`
- Web UI: `DEPLOYMENT_GUIDE.md` and various README files

---

## 🎨 GUI Screenshots & Features

### DynamoDB Manager
```
┌─────────────────────────────────────────┐
│  🗄️ DynamoDB Manager                   │
├─────────────────────────────────────────┤
│ Region: [us-gov-west-1▼] Table: [▼]    │
├─────────────────────────────────────────┤
│ [Browse] [Query] [Edit] [Bulk Ops]     │
│                                          │
│ ┌─ Browse Data ────────────────────┐   │
│ │ 🔄 Load  🗑️ Delete  ✏️ Edit  📥 Export │
│ │                                   │   │
│ │ [Spreadsheet View of Records]    │   │
│ │                                   │   │
│ │ Record Details:                  │   │
│ │ { JSON preview... }              │   │
│ └───────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Test Generator
```
┌─────────────────────────────────────────┐
│  🧪 Test Contact Generator              │
├─────────────────────────────────────────┤
│ Region: us-gov-west-1                   │
│ Table: EmailContactsNew                 │
│ Email: test@example.com                 │
│ Count: 10000                            │
├─────────────────────────────────────────┤
│ [Contact Template Fields...]            │
│ ✅ MS-ISAC  ✅ SOC Call  ❌ K-12        │
├─────────────────────────────────────────┤
│ Progress: [████████░░] 80%              │
│ Imported: 8,000 | Rate: 320/s | ETA: 6s│
├─────────────────────────────────────────┤
│ [Log panel with timestamps...]          │
├─────────────────────────────────────────┤
│ [🚀 Start] [🛑 Cancel] [🗑️ Clear] [❌ Exit]│
└─────────────────────────────────────────┘
```

---

## 💡 Pro Tips

### Workflow Integration

**Daily Operations:**
1. Use **Web UI** for normal email campaigns
2. Use **DynamoDB Manager** to audit and troubleshoot
3. Use **Test Generator** for periodic load tests

**Data Management:**
1. Import contacts via **Web UI** (CSV bulk import)
2. Query and validate via **DynamoDB Manager**
3. Export reports via **DynamoDB Manager** (CSV/JSON)

**Development & Testing:**
1. Generate test data with **Test Generator**
2. Test campaigns via **Web UI**
3. Clean up test data with **DynamoDB Manager** (bulk delete)

### Productivity Hacks

**Quick Data Audit:**
```
DynamoDB Manager → Select Table → Scan Table → Export CSV
```

**Rapid Testing:**
```
Test Generator → Set 100 contacts → Start → Web UI → Send test campaign
```

**Contact Verification:**
```
Web UI → Search by name → DynamoDB Manager → View full record
```

**Campaign Analysis:**
```
DynamoDB Manager → EmailCampaigns → Export JSON → Analyze
```

---

## 📊 Project Statistics

### Tool Capabilities

| Metric | DynamoDB Manager | Test Generator | Web UI |
|--------|-----------------|----------------|--------|
| Max Records/View | Unlimited | 100,000+ | 20,000 |
| Query Speed | Fast (indexed) | N/A | Fast (filtered) |
| Bulk Operations | Yes | Generate only | CSV import |
| Export Formats | CSV, JSON | N/A | CSV |
| Platform | Desktop | Desktop | Web |
| Concurrent Users | Single | Single | Multiple |

---

## 🆘 Getting Help

### Documentation Priority
1. Tool-specific guide (e.g., `DYNAMODB_MANAGER_GUIDE.md`)
2. This index file (`GUI_TOOLS_INDEX.md`)
3. `QUICKSTART.md` or `README.md`
4. AWS DynamoDB documentation

### Support Checklist
- [ ] Checked tool-specific guide
- [ ] Verified AWS credentials
- [ ] Confirmed correct region
- [ ] Tested with simple operation first
- [ ] Reviewed error messages
- [ ] Checked IAM permissions

---

## 🔄 Version Information

**Current Version:** 1.0  
**Last Updated:** January 2025  
**Compatibility:**
- Python 3.7+
- boto3 latest
- tkinter (included with Python)
- AWS DynamoDB

---

**Happy Managing!** 🎉

Choose the right tool for your task and boost your productivity!

