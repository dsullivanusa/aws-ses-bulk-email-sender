# Email Preview Feature - Complete Guide

## 🎯 Overview

The **Email Preview** feature allows users to see exactly what recipients will receive before sending a campaign. When you click the "👁️ Preview Email" button, the system:

1. **Processes the email** with the same logic as sending (locks image sizes, cleans HTML, uploads images to S3)
2. **Saves to S3 and DynamoDB** for future reference
3. **Opens a new window** showing the rendered email exactly as recipients will see it

## ✨ Key Features

- 🔒 **Exact WYSIWYG Preview** - Shows precise size/position of images
- 📸 **Image Processing** - Uploads and displays inline images
- 💾 **Saved to S3** - Preview HTML stored for 24 hours
- 📝 **Metadata Tracking** - Saves to DynamoDB with preview details
- 🆕 **New Window** - Opens in separate browser window
- 📎 **Attachment List** - Shows all attachments including inline images

## 🚀 How To Use

### Step-by-Step

1. **Compose Your Email**
   - Fill in campaign name and subject
   - Add email body content
   - Paste and resize images
   - Add attachments if needed

2. **Click Preview Button**
   - Click "👁️ Preview Email" button
   - System processes email (same as sending)
   - Images are uploaded to S3
   - Preview is generated

3. **View Preview Window**
   - New browser window opens automatically
   - Shows formatted preview with:
     - Email subject and campaign name
     - Preview ID and timestamp
     - Rendered email body
     - List of attachments
   - Review the preview carefully

4. **Make Changes (if needed)**
   - Close preview window
   - Edit your email in the editor
   - Click Preview again to see updates

5. **Send Campaign**
   - When satisfied with preview
   - Click "🚀 Send Campaign" button
   - Recipients will receive exactly what you saw in preview

## 📊 Console Output

When you click Preview, watch the console (F12 → Console):

```
👁️ PREVIEW: Locking image sizes and positions...
🔒 PREVIEW: Locked image 1 size/position
🔒 PREVIEW: Locked image 2 size/position
👁️ PREVIEW: Unwrapped 2 image(s)
👁️ PREVIEW: Locked 2 image(s) to exact editor size/position
👁️ PREVIEW: Found 2 embedded image(s)
Uploading image 1/2...
✅ Uploaded embedded image: attachments/PreviewImage1_....png
Uploading image 2/2...
✅ Uploaded embedded image: attachments/PreviewImage2_....png
👁️ PREVIEW: Sending to backend...
   Body length: 2450 characters
   Attachments: 2
👁️ PREVIEW: Generated successfully!
👁️ PREVIEW: Opening in new window: https://....execute-api.../preview/abc-123-...
```

## 🏗️ Technical Architecture

### Frontend Flow

```
User clicks "Preview Email"
  ↓
JavaScript previewCampaign() function
  ↓
1. Lock image sizes (window.getComputedStyle)
2. Apply locked styles to HTML
3. Unwrap images from resize containers
4. Clean HTML (remove Quill artifacts)
5. Upload embedded images to S3
6. Replace data: URIs with S3 keys
  ↓
POST to /preview endpoint
  ↓
Backend saves to S3 and DynamoDB
  ↓
Returns preview_id
  ↓
Open new window: /preview/{preview_id}
```

### Backend Flow

```
POST /preview
  ↓
save_preview() function
  ↓
1. Generate unique preview ID (UUID)
2. Extract email data (subject, body, attachments)
3. Replace S3 keys with presigned URLs (1 hour)
4. Create complete HTML document
5. Save HTML to S3: email-previews/{id}.html
6. Save metadata to DynamoDB campaigns table
7. Return preview_id
  ↓
GET /preview/{preview_id}
  ↓
get_preview() function
  ↓
1. Query DynamoDB for preview metadata
2. Get S3 key from metadata
3. Retrieve HTML from S3
4. Return HTML with Content-Type: text/html
  ↓
Browser renders preview in new window
```

## 💾 Data Storage

### S3 Storage

**Location:** `s3://jcdc-ses-contact-list/email-previews/`

**File:** `{preview_id}.html`

**Contents:**
- Complete HTML document
- Inline CSS for styling
- Preview header with metadata
- Email body with images (presigned URLs)
- Attachments list
- Preview footer

**Retention:** Manually managed (no automatic expiration)

### DynamoDB Storage

**Table:** `EmailCampaigns`

**Item Structure:**
```json
{
  "campaign_id": "abc-123-def-456",  // Same as preview_id
  "preview_id": "abc-123-def-456",
  "type": "preview",
  "status": "preview",
  "campaign_name": "Q1 Newsletter Preview",
  "subject": "Welcome to Q1!",
  "body_length": 2450,
  "attachment_count": 2,
  "s3_key": "email-previews/abc-123-def-456.html",
  "created_at": "2025-10-10T15:30:00.000Z",
  "expires_at": "2025-10-11T15:30:00.000Z"  // 24 hours later
}
```

## 📸 Preview HTML Structure

The generated preview includes:

### 1. Header Section
```html
<div class="preview-header">
  <h1>📧 Email Preview</h1>
  <div class="preview-meta">
    <strong>Subject:</strong> Q1 Newsletter
    <strong>Campaign:</strong> Q1 Newsletter Preview
    <strong>Preview ID:</strong> abc-123-def-456
    <strong>Generated:</strong> 2025-10-10T15:30:00Z
  </div>
</div>
```

### 2. Body Section
```html
<div class="preview-body">
  <!-- Your email HTML with locked image sizes -->
  <img src="https://...presigned-url..." style="width: 400px; height: 300px;">
  <p>Your email content here...</p>
</div>
```

### 3. Attachments Section
```html
<div class="attachments-list">
  <h3>📎 Attachments (2)</h3>
  <div>• InlineImage1.png (image/png) - Inline Image</div>
  <div>• InlineImage2.png (image/png) - Inline Image</div>
</div>
```

### 4. Footer Section
```html
<div class="preview-footer">
  This is a preview of what recipients will see. 
  Generated at 2025-10-10T15:30:00Z
</div>
```

## 🎨 Preview Styling

The preview uses:
- **Max width:** 800px (centered)
- **Clean design:** White background, gray accents
- **Responsive images:** `max-width: 100%`
- **Professional header:** Purple/indigo theme
- **Clear metadata:** Shows all relevant info
- **Attachment badges:** Blue-themed list

## ⚙️ Configuration

### API Gateway Routes

Two new routes are required:

1. **POST /preview**
   - Handler: `save_preview(body, headers)`
   - Purpose: Save preview data
   - Returns: `{preview_id, s3_key, timestamp}`

2. **GET /preview/{preview_id}**
   - Handler: `get_preview(preview_id, headers)`
   - Purpose: Serve preview HTML
   - Returns: HTML content

### Lambda Permissions

Ensure Lambda has permissions for:
- ✅ S3 PutObject (to `email-previews/*`)
- ✅ S3 GetObject (from `email-previews/*`)
- ✅ S3 GeneratePresignedUrl (for inline images)
- ✅ DynamoDB PutItem (to `EmailCampaigns`)
- ✅ DynamoDB GetItem (from `EmailCampaigns`)

## 🧪 Testing

### Test Scenario 1: Simple Text Email

1. Enter subject: "Test Preview"
2. Enter body: "Hello, this is a test."
3. Click "Preview Email"
4. **Verify:** New window opens with formatted preview

### Test Scenario 2: Email with Images

1. Paste an image into editor
2. Resize to 400px
3. Center align
4. Click "Preview Email"
5. **Verify:** 
   - Image appears in preview
   - Size is 400px
   - Image is centered
   - Attachments list shows inline image

### Test Scenario 3: Multiple Images

1. Paste 3 different images
2. Resize each differently
3. Add text between images
4. Click "Preview Email"
5. **Verify:**
   - All 3 images appear
   - Each has correct size
   - Text flows correctly
   - Attachments list shows all 3

### Test Scenario 4: Preview → Edit → Preview Again

1. Create email with image
2. Click "Preview Email"
3. Review preview
4. Close preview window
5. Resize image in editor
6. Click "Preview Email" again
7. **Verify:** New preview reflects changes

## 🔍 Troubleshooting

### Issue: Preview window doesn't open

**Possible Causes:**
- Pop-up blocker enabled
- JavaScript error

**Solutions:**
- Allow pop-ups for this site
- Check browser console (F12)
- Try again

### Issue: Images don't appear in preview

**Possible Causes:**
- S3 upload failed
- Presigned URL generation failed
- Image data corrupted

**Solutions:**
- Check console for upload errors
- Verify S3 bucket permissions
- Try smaller images
- Check Lambda CloudWatch logs

### Issue: Preview HTML looks broken

**Possible Causes:**
- HTML processing error
- CSS not loading
- Invalid HTML structure

**Solutions:**
- Check console for errors
- Simplify email content
- Try text-only preview first
- Check Lambda logs

### Issue: "Preview not found" error

**Possible Causes:**
- Preview ID invalid
- DynamoDB item not found
- S3 file missing

**Solutions:**
- Generate new preview
- Check DynamoDB for preview record
- Check S3 for HTML file
- Review Lambda logs

## 📝 Best Practices

### 1. Always Preview Before Sending
- 👍 Use preview to catch formatting issues
- 👍 Verify image sizes and alignment
- 👍 Check for typos or errors
- 👍 Ensure all images load correctly

### 2. Test Different Scenarios
- 👍 Preview with no images
- 👍 Preview with multiple images
- 👍 Preview with attachments
- 👍 Preview long emails
- 👍 Preview short emails

### 3. Clean Up Previews
- 👍 Previews stored for 24 hours
- 👍 S3 cleanup may be needed periodically
- 👍 DynamoDB items can be manually deleted
- 👍 Consider implementing automatic cleanup

### 4. Monitor Performance
- 👍 Watch for slow image uploads
- 👍 Monitor S3 storage usage
- 👍 Check Lambda execution time
- 👍 Review CloudWatch logs

## 🎉 Benefits

### For Users
- ✅ **Confidence** - See exactly what recipients get
- ✅ **Catch Errors** - Find issues before sending
- ✅ **WYSIWYG Accuracy** - Preview matches editor
- ✅ **Save Time** - No test emails needed
- ✅ **Professional** - Send polished campaigns

### For Administrators
- ✅ **Debugging** - Preview stored for review
- ✅ **Audit Trail** - All previews logged
- ✅ **Testing** - Easy to verify functionality
- ✅ **Support** - Help users troubleshoot
- ✅ **Documentation** - Preview IDs for reference

## 🔗 Related Features

- **Image Size Locking** - See `IMAGE_SIZE_POSITION_LOCKING.md`
- **Image Resize Fix** - See `QUILL_IMAGE_RESIZE_FIX.md`
- **HTML Image Support** - See `HTML_AND_IMAGE_SUPPORT_GUIDE.md`
- **S3 Attachments** - See `S3_ATTACHMENTS_GUIDE.md`

## 🚀 Deployment

The preview feature requires **TWO steps**:

### Step 1: Deploy Updated Lambda Function

```bash
python deploy_bulk_email_api.py
```

This updates the Lambda function with the new preview code.

### Step 2: Add API Gateway Endpoints

**⚠️ REQUIRED:** The preview feature needs two new API Gateway endpoints.

Run the automated script:

```bash
python add_preview_endpoint.py
```

This will:
1. ✅ Create `/preview` resource
2. ✅ Add POST method to `/preview` (save preview)
3. ✅ Create `/preview/{preview_id}` resource  
4. ✅ Add GET method to `/preview/{preview_id}` (retrieve preview)
5. ✅ Configure Lambda integration for both endpoints
6. ✅ Add Lambda invoke permissions
7. ✅ Deploy to 'prod' stage

**Expected Output:**
```
============================================================
  Add Preview Endpoints to API Gateway
============================================================

✅ Found API: bulk-email-api (ID: abc123xyz)
✅ Found Lambda function: bulk-email-api-function
✅ Root resource ID: abc123

📋 Step 1: Creating /preview resource...
   ✅ Created /preview (ID: xyz789)

📋 Step 2: Adding POST method to /preview...
   ✅ Created POST method
   ✅ Lambda integration configured
   ✅ Lambda permission added

📋 Step 3: Creating /preview/{preview_id} resource...
   ✅ Created /preview/{preview_id} (ID: def456)

📋 Step 4: Adding GET method to /preview/{preview_id}...
   ✅ Created GET method
   ✅ Lambda integration configured
   ✅ Lambda permission added

📋 Step 5: Deploying API to 'prod' stage...
   ✅ Deployment created (ID: ghi789)

============================================================
✅ Preview endpoints successfully added to API Gateway!
============================================================

📍 API Gateway ID: abc123xyz
📍 Preview resource ID: xyz789
📍 Preview ID resource ID: def456

🔗 Endpoints:
   POST   https://abc123xyz.execute-api.us-gov-west-1.amazonaws.com/prod/preview
   GET    https://abc123xyz.execute-api.us-gov-west-1.amazonaws.com/prod/preview/{preview_id}

✅ API deployed to 'prod' stage

💡 Test the endpoints:
   1. Create an email in the web UI
   2. Click '👁️ Preview Email' button
   3. New window should open with preview
```

### Manual API Gateway Setup (if needed)

If automatic deployment doesn't add the routes:

1. Go to API Gateway Console
2. Find your API
3. Add resource: `/preview`
   - Method: `POST`
   - Integration: Lambda function
   - Lambda proxy integration: Yes
4. Add resource: `/preview/{preview_id}`
   - Method: `GET`
   - Integration: Lambda function  
   - Lambda proxy integration: Yes
5. Deploy to stage
6. Test endpoints

## 📊 Monitoring

### CloudWatch Metrics

Monitor:
- **Preview generation time**
- **S3 upload duration**
- **DynamoDB write latency**
- **Lambda execution time**
- **Error rates**

### CloudWatch Logs

Look for:
```
📧 Saving email preview...
   Preview ID: abc-123-def-456
   Subject: Q1 Newsletter
   Body length: 2450 characters
   Attachments: 2
   ✅ Replaced S3 key with presigned URL: ...
   ✅ Saved preview HTML to S3: ...
   ✅ Saved preview metadata to DynamoDB
```

## 🎯 Future Enhancements

Potential improvements:
- [ ] Email client rendering (Gmail, Outlook, etc.)
- [ ] Mobile preview mode
- [ ] Desktop preview mode
- [ ] Preview sharing (send link to colleague)
- [ ] Preview history (list all previews)
- [ ] Preview comparison (before/after edits)
- [ ] Automatic cleanup of old previews
- [ ] Preview analytics (views, time spent)

---

**Status:** ✅ Feature complete and ready for use

**Version:** 1.0

**Last Updated:** October 10, 2025

**Author:** Email Campaign System

**Support:** Check CloudWatch logs and console output for debugging

