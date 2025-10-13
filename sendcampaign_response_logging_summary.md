# SendCampaign POST Response Logging - Summary

## ✅ **ENHANCED LOGGING ADDED**

I've added comprehensive logging to capture the sendCampaign POST request and response details in the web UI.

## 📍 **LOGGING LOCATIONS**

### **1. Campaign Data Preparation Logging**
**Location**: After campaign object creation (~line 5025)
**What it shows**: Complete campaign data being sent to backend

```javascript
console.log('📡 CAMPAIGN DATA PREPARED:');
console.log('   Campaign Name:', campaign.campaign_name);
console.log('   Subject:', campaign.subject);
console.log('   Body Length:', campaign.body ? campaign.body.length : 0, 'characters');
console.log('   Filter Description:', campaign.filter_description);
console.log('   Target Contacts:', campaign.target_contacts.length, 'addresses');
console.log('   To Recipients:', campaign.to.length, 'addresses');
console.log('   CC Recipients:', campaign.cc.length, 'addresses');
console.log('   BCC Recipients:', campaign.bcc.length, 'addresses');
console.log('   Attachments:', campaign.attachments.length, 'files');
console.log('   Full Campaign Object:', campaign);
```

### **2. HTTP Request Logging**
**Location**: Before fetch request (~line 5095)
**What it shows**: Request details being sent

```javascript
console.log('📡 SENDING CAMPAIGN REQUEST:');
console.log('   URL:', `${API_URL}/campaign`);
console.log('   Method: POST');
console.log('   Headers:', {'Content-Type': 'application/json'});
console.log('   Body size:', campaignJSON.length, 'characters');
```

### **3. HTTP Response Logging**
**Location**: After fetch response (~line 5105)
**What it shows**: Complete response details

```javascript
console.log('📡 CAMPAIGN RESPONSE RECEIVED:');
console.log('   Status:', response.status, response.statusText);
console.log('   Headers:', Object.fromEntries(response.headers.entries()));
console.log('   OK:', response.ok);
console.log('   Type:', response.type);
console.log('   URL:', response.url);
console.log('   Response length:', responseText.length, 'characters');
console.log('   Response preview (first 200 chars):', responseText.substring(0, 200));
```

### **4. Error Response Analysis**
**Location**: When response is not OK
**What it shows**: Detailed error information

```javascript
if (!response.ok) {
    console.error('📡 ERROR RESPONSE DETAILS:');
    console.error('   Status Code:', response.status);
    console.error('   Status Text:', response.statusText);
    console.error('   Full Response Body:', responseText);
}
```

### **5. JSON Parsing Logging**
**Location**: During response parsing (~line 5145)
**What it shows**: JSON parsing results

```javascript
console.log('📡 PARSING RESPONSE AS JSON...');
result = JSON.parse(responseText);
console.log('📡 JSON PARSE SUCCESS:');
console.log('   Parsed result:', result);
console.log('   Result keys:', Object.keys(result));
if (result.error) {
    console.error('📡 API ERROR IN RESPONSE:', result.error);
}
if (result.success) {
    console.log('📡 API SUCCESS:', result.success);
}
```

## 🔍 **HOW TO VIEW THE LOGGING**

### **Browser Developer Tools**:
1. **Open Developer Tools** (F12 or right-click → Inspect)
2. **Go to Console tab**
3. **Send a campaign** with To/CC recipients
4. **Look for messages** starting with `📡`

### **Example Output**:
```
📡 CAMPAIGN DATA PREPARED:
   Campaign Name: Test Campaign
   Subject: Test Subject
   Body Length: 150 characters
   Filter Description: To/CC/BCC Recipients Only
   Target Contacts: 1 addresses
   To Recipients: 0 addresses
   CC Recipients: 1 addresses
   BCC Recipients: 0 addresses
   Attachments: 0 files
   Full Campaign Object: {campaign_name: "Test Campaign", ...}

📡 SENDING CAMPAIGN REQUEST:
   URL: https://your-api.amazonaws.com/prod/campaign
   Method: POST
   Headers: {Content-Type: "application/json"}
   Body size: 1250 characters

📡 CAMPAIGN RESPONSE RECEIVED:
   Status: 400 Bad Request
   Headers: {content-type: "application/json", ...}
   OK: false
   Type: cors
   URL: https://your-api.amazonaws.com/prod/campaign
   Response length: 125 characters
   Response preview (first 200 chars): {"error": "No valid email addresses found..."}

📡 ERROR RESPONSE DETAILS:
   Status Code: 400
   Status Text: Bad Request
   Full Response Body: {"error": "No valid email addresses found. Received 2 entries but none are valid emails. Please check email format."}

📡 PARSING RESPONSE AS JSON...
📡 JSON PARSE SUCCESS:
   Parsed result: {error: "No valid email addresses found..."}
   Result keys: ["error"]
📡 API ERROR IN RESPONSE: No valid email addresses found. Received 2 entries but none are valid emails. Please check email format.
```

## 🎯 **WHAT THIS HELPS DIAGNOSE**

### **Request Issues**:
- ✅ **Campaign data structure** - See exactly what's being sent
- ✅ **Recipient counts** - Verify To/CC/BCC numbers
- ✅ **Request size** - Check if payload is too large
- ✅ **Missing fields** - Identify empty required fields

### **Response Issues**:
- ✅ **HTTP status codes** - 400, 500, etc.
- ✅ **Error messages** - Exact backend error text
- ✅ **Response format** - JSON vs HTML error pages
- ✅ **Response headers** - Content-type, etc.

### **Specific to Your Issue**:
- ✅ **Target contacts count** - Should show correct number
- ✅ **CC recipients** - Should show your CC addresses
- ✅ **Error details** - Will show exact 400 error message
- ✅ **Request payload** - Verify what data is sent

## 🚀 **DEPLOYMENT**

1. **Deploy** the updated `bulk_email_api_lambda.py`
2. **Open browser developer tools** (F12)
3. **Go to Console tab**
4. **Send a campaign** with To/CC recipients
5. **Review the detailed logging** to diagnose the issue

This enhanced logging will show you exactly what's happening with your To/CC campaign request and why it's returning a 400 error!