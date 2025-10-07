# 🧪 API Gateway Curl Test Commands

Replace `YOUR_API_URL` with your actual API Gateway URL.

## 🔗 Find Your API URL

Run:
```bash
python get_api_gateway_info.py
```

Or check your deployed API in AWS Console.

---

## 📋 Basic Curl Commands

### 1. Health Check (GET /)
```bash
curl -X GET "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "message": "Bulk Email API is running",
  "version": "2.0"
}
```

---

### 2. Get Contacts (GET /contacts)
```bash
curl -X GET "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts?limit=10" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "contacts": [
    {
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe"
    }
  ],
  "count": 10
}
```

---

### 3. Add Contact (POST /contacts)
```bash
curl -X POST "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts" \
  -H "Content-Type: application/json" \
  -d '{
    "contact": {
      "email": "newuser@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "company": "ACME Corp"
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "contact_id": "uuid-here"
}
```

---

### 4. Update Contact (PUT /contacts)
```bash
curl -X PUT "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "uuid-here",
    "email": "updated@example.com",
    "first_name": "Jane",
    "last_name": "Updated"
  }'
```

---

### 5. Delete Contact (DELETE /contacts)
```bash
curl -X DELETE "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts?contact_id=uuid-here" \
  -H "Content-Type: application/json"
```

---

### 6. Get Distinct Values (GET /contacts/distinct)
```bash
curl -X GET "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts/distinct?field=company" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "values": ["ACME Corp", "Tech Inc", "Gov Agency"],
  "count": 3
}
```

---

### 7. Filter Contacts (POST /contacts/filter)
```bash
curl -X POST "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": [
      {
        "field": "company",
        "values": ["ACME Corp", "Tech Inc"]
      }
    ]
  }'
```

---

### 8. Search Contacts (POST /contacts/search)
```bash
curl -X POST "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/contacts/search" \
  -H "Content-Type: application/json" \
  -d '{
    "search_term": "john"
  }'
```

---

### 9. Send Campaign (POST /campaign)
```bash
curl -X POST "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/campaign" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Test Campaign",
    "subject": "Hello {{first_name}}",
    "body": "<p>Hi {{first_name}},</p><p>This is a test email.</p>",
    "launched_by": "Test User",
    "target_contacts": ["test1@example.com", "test2@example.com"],
    "filter_description": "Manual Test"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "campaign_id": "campaign_1728219323",
  "message": "Campaign queued successfully",
  "total_contacts": 2,
  "queued_count": 2
}
```

---

### 10. Check Campaign Status (GET /campaign/{campaign_id})
```bash
curl -X GET "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod/campaign/campaign_1728219323" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "campaign_id": "campaign_1728219323",
  "campaign_name": "Test Campaign",
  "status": "completed",
  "total_contacts": 2,
  "sent_count": 2,
  "failed_count": 0
}
```

---

## 🔧 Debugging Options

### Verbose Output (-v)
See all request/response headers:
```bash
curl -v -X GET "https://your-api-url/contacts"
```

### Include Response Headers (-i)
```bash
curl -i -X GET "https://your-api-url/contacts"
```

### Show Only HTTP Status (-w)
```bash
curl -X GET "https://your-api-url/contacts" \
  -w "\nHTTP Status: %{http_code}\n" \
  -o /dev/null -s
```

### Save Response to File (-o)
```bash
curl -X GET "https://your-api-url/contacts" -o response.json
```

---

## 🧪 Quick Test Script

Create a file `test.sh`:
```bash
#!/bin/bash
API_URL="YOUR_URL_HERE"

# Test GET
echo "Testing GET /contacts..."
curl -X GET "$API_URL/contacts?limit=5" -H "Content-Type: application/json"

# Test POST
echo -e "\n\nTesting POST /contacts..."
curl -X POST "$API_URL/contacts" \
  -H "Content-Type: application/json" \
  -d '{"contact":{"email":"test@test.com","first_name":"Test"}}'
```

Make executable:
```bash
chmod +x test.sh
./test.sh
```

---

## 🔍 Common Issues & Solutions

### Issue 1: CORS Error
**Error:** `Access-Control-Allow-Origin`

**Solution:** Your API already has CORS enabled. Make sure you're using the correct URL.

### Issue 2: 403 Forbidden
**Error:** `{"message":"Forbidden"}`

**Causes:**
- Wrong API key (if using API keys)
- API not deployed to stage
- Wrong URL

**Check:**
```bash
curl -v https://your-api-url/contacts
# Look for "403 Forbidden" or "Missing Authentication Token"
```

### Issue 3: 404 Not Found
**Error:** `{"message":"Not Found"}`

**Cause:** Wrong endpoint path or URL

**Solution:** Verify API Gateway deployment stage (usually `/prod`)

### Issue 4: Connection Refused
**Error:** `curl: (7) Failed to connect`

**Cause:** Wrong URL or region

**Get correct URL:**
```bash
python get_api_gateway_info.py
```

---

## 🎯 Complete Test Sequence

```bash
# 1. Set your API URL
export API_URL="https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod"

# 2. Test health
curl -X GET "$API_URL/" -H "Content-Type: application/json"

# 3. Get contacts
curl -X GET "$API_URL/contacts?limit=5" -H "Content-Type: application/json"

# 4. Add contact
curl -X POST "$API_URL/contacts" \
  -H "Content-Type: application/json" \
  -d '{"contact":{"email":"test@test.com","first_name":"Test"}}'

# 5. Send test campaign
curl -X POST "$API_URL/campaign" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name":"Curl Test",
    "subject":"Test",
    "body":"<p>Test</p>",
    "target_contacts":["verified@email.com"],
    "filter_description":"Test"
  }'
```

---

## 📝 Windows PowerShell Version

If using PowerShell instead of bash:

```powershell
# Set API URL
$API_URL = "https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod"

# Test GET
Invoke-RestMethod -Uri "$API_URL/contacts?limit=5" `
  -Method GET `
  -ContentType "application/json"

# Test POST
$body = @{
  contact = @{
    email = "test@test.com"
    first_name = "Test"
    last_name = "User"
  }
} | ConvertTo-Json

Invoke-RestMethod -Uri "$API_URL/contacts" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

---

## 🚀 Quick Start

1. Get your API URL:
   ```bash
   python get_api_gateway_info.py
   ```

2. Test basic endpoint:
   ```bash
   curl -X GET "YOUR_URL/contacts?limit=1" -H "Content-Type: application/json"
   ```

3. If it works, you'll see JSON response with contacts ✅

4. If it fails, check:
   - URL is correct
   - API is deployed
   - No authentication required (or add auth headers)

---

**Happy Testing! 🎉**
