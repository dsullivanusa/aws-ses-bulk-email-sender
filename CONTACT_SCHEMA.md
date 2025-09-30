# 📋 Contact Schema - CISA Email Campaign System

## DynamoDB EmailContacts Table Structure

### **Complete Field List:**

| Field Name | Type | Description | Example | Required |
|------------|------|-------------|---------|----------|
| `email` | String | Primary email address (Primary Key) | john.doe@example.com | ✅ Yes |
| `first_name` | String | Contact's first name | John | ✅ Yes |
| `last_name` | String | Contact's last name | Doe | ✅ Yes |
| `title` | String | Job title or position | IT Director | No |
| `entity_type` | String | Type of entity | State Government, Local Government | No |
| `state` | String | US State | California, Texas, NY | No |
| `agency_name` | String | Government agency or organization | Department of Technology | No |
| `sector` | String | Industry sector | Government, Education, Utilities | No |
| `subsection` | String | Department or subsection | IT Services, Cybersecurity | No |
| `phone` | String | Phone number | 555-0100 | No |
| `ms_isac_member` | String | MS-ISAC membership status | Yes, No | No |
| `soc_call` | String | SOC call participation | Yes, No | No |
| `fusion_center` | String | Fusion center membership | Yes, No | No |
| `k12` | String | K-12 education designation | Yes, No | No |
| `water_wastewater` | String | Water/Wastewater sector | Yes, No | No |
| `weekly_rollup` | String | Weekly rollup subscription | Yes, No | No |
| `alternate_email` | String | Secondary email address | john.alt@example.com | No |
| `region` | String | Geographic region | West, South, Northeast | No |
| `group` | String | Contact group or category | State CISOs, Local Government | No |
| `created_at` | String | ISO timestamp | 2024-01-01T00:00:00 | Auto |

## 📧 Email Personalization

All fields can be used as placeholders in email templates:

### **Basic Contact Info:**
- `{{first_name}}` - First name
- `{{last_name}}` - Last name
- `{{email}}` - Email address
- `{{title}}` - Job title

### **Organization Info:**
- `{{entity_type}}` - Entity type
- `{{state}}` - State
- `{{agency_name}}` - Agency name
- `{{sector}}` - Sector
- `{{subsection}}` - Subsection
- `{{phone}}` - Phone number

### **CISA-Specific Fields:**
- `{{ms_isac_member}}` - MS-ISAC membership
- `{{soc_call}}` - SOC call status
- `{{fusion_center}}` - Fusion center
- `{{k12}}` - K-12 designation
- `{{water_wastewater}}` - Water/Wastewater sector
- `{{weekly_rollup}}` - Weekly rollup subscription
- `{{alternate_email}}` - Alternate email
- `{{region}}` - Region
- `{{group}}` - Group

### **Example Email Template:**

**Subject:**
```
CISA Alert for {{state}} - {{agency_name}}
```

**Body:**
```html
Dear {{first_name}} {{last_name}},

As the {{title}} for {{agency_name}}, we wanted to inform you about...

Your contact information:
- State: {{state}}
- Sector: {{sector}}
- Region: {{region}}
- MS-ISAC Member: {{ms_isac_member}}

Best regards,
CISA Team
```

## 📁 CSV Import Format

### **Full CSV Header:**
```csv
email,first_name,last_name,title,entity_type,state,agency_name,sector,subsection,phone,ms_isac_member,soc_call,fusion_center,k12,water_wastewater,weekly_rollup,alternate_email,region,group
```

### **Example CSV:**
```csv
email,first_name,last_name,title,entity_type,state,agency_name,sector,subsection,phone,ms_isac_member,soc_call,fusion_center,k12,water_wastewater,weekly_rollup,alternate_email,region,group
john.doe@example.com,John,Doe,IT Director,State Government,California,Department of Technology,Government,IT Services,555-0100,Yes,Yes,Yes,No,No,Yes,j.doe@alt.com,West,State CISOs
jane.smith@example.com,Jane,Smith,Security Analyst,Local Government,Texas,City of Austin,Government,Cybersecurity,555-0200,Yes,No,No,No,No,Yes,,South,Local Government
```

### **Supported CSV Header Variations:**

The system automatically maps these variations:

| Standard Field | Accepted CSV Headers |
|---------------|---------------------|
| `email` | email, email_address |
| `first_name` | first_name, firstname, first |
| `last_name` | last_name, lastname, last |
| `agency_name` | agency_name, agencyname, agency |
| `entity_type` | entity_type, entitytype |
| `phone` | phone, phone_number |
| `ms_isac_member` | ms_isac_member, ms-isac, msisac |
| `soc_call` | soc_call, soc |
| `fusion_center` | fusion_center, fusion |
| `k12` | k12, k-12 |
| `water_wastewater` | water_wastewater, water/wastewater, water |
| `weekly_rollup` | weekly_rollup, weekly, rollup |
| `alternate_email` | alternate_email, alt_email |

## 🎯 Field Guidelines

### **Entity Types:**
- State Government
- Local Government
- Tribal Government
- Territorial Government
- K-12 Education
- Higher Education
- Water/Wastewater
- Private Sector

### **Regions:**
- Northeast
- Southeast
- Midwest
- Southwest
- West
- Pacific
- Alaska
- Hawaii

### **Yes/No Fields:**
Accepted values:
- `Yes` / `No`
- `yes` / `no`
- `Y` / `N`
- `True` / `False`
- Leave empty if not applicable

## 📊 DynamoDB Structure

**Primary Key:**
- Partition Key: `email` (String)

**Attributes:**
- All fields are optional except `email`, `first_name`, `last_name`
- No secondary indexes needed (use Scan for filtering)
- Schema-less (can add new fields dynamically)

## 🔍 Querying Contacts

### **Get Single Contact:**
```python
contact = contacts_table.get_item(Key={'email': 'john@example.com'})
```

### **Get All Contacts:**
```python
contacts = contacts_table.scan()
```

### **Filter by Field (client-side):**
```python
contacts = contacts_table.scan()
california_contacts = [c for c in contacts['Items'] if c.get('state') == 'California']
```

## 🚀 Adding Contacts

### **Method 1: Web UI Form**
1. Go to Contacts tab
2. Click "Add Contact"
3. Fill in all available fields
4. Click "Add"

### **Method 2: CSV Upload**
1. Prepare CSV file with headers
2. Go to Contacts tab
3. Click "Upload CSV"
4. Select your CSV file

### **Method 3: API**
```bash
curl -X POST https://YOUR_API/contacts \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "title": "IT Director",
    "entity_type": "State Government",
    "state": "California",
    "agency_name": "Department of Technology",
    "sector": "Government",
    "subsection": "IT Services",
    "phone": "555-0100",
    "ms_isac_member": "Yes",
    "soc_call": "Yes",
    "fusion_center": "Yes",
    "k12": "No",
    "water_wastewater": "No",
    "weekly_rollup": "Yes",
    "alternate_email": "j.doe@alt.com",
    "region": "West",
    "group": "State CISOs"
  }'
```

## 📝 Sample Files

- `sample_contacts_full.csv` - Full example CSV with all fields
- `dynamodb_table_setup.py` - Creates table and adds sample contacts

## 🔄 Migration from Old Schema

If you have existing contacts with only `first_name`, `last_name`, `email`, `company`:
- ✅ No migration needed
- ✅ Old contacts will continue to work
- ✅ New fields can be added gradually
- ✅ `{{company}}` placeholder maps to `{{agency_name}}`

## ✅ Benefits of Extended Schema

1. **Better Targeting** - Filter campaigns by sector, region, group
2. **Personalization** - Use more fields in email templates
3. **Compliance** - Track MS-ISAC membership, SOC participation
4. **Organization** - Group contacts by entity type, sector
5. **Flexibility** - All fields optional, add as needed

---

See `sample_contacts_full.csv` for a complete example with all fields!
