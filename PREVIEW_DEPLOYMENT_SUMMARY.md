# Preview Feature Deployment - Quick Reference

## ⚠️ Important: YES, New API Gateway Endpoints Required

The preview feature requires **2 new API Gateway endpoints**:

1. **POST /preview** - To save preview data
2. **GET /preview/{preview_id}** - To retrieve and display preview HTML

## 🚀 Deployment Steps

### Step 1: Update Lambda Function

```bash
python deploy_bulk_email_api.py
```

**What this does:**
- Updates Lambda function code with preview functionality
- Adds `save_preview()` and `get_preview()` functions
- Adds `previewCampaign()` JavaScript function
- Updates UI with Preview button

### Step 2: Add API Gateway Endpoints ⚠️ REQUIRED

```bash
python add_preview_endpoint.py
```

**What this does:**
- Creates `/preview` resource in API Gateway
- Adds POST method to `/preview`
- Creates `/preview/{preview_id}` resource
- Adds GET method to `/preview/{preview_id}`
- Configures Lambda integration
- Adds invoke permissions
- Deploys to 'prod' stage

## ✅ Verification

After running both scripts:

1. **Check API Gateway Console:**
   - Go to AWS Console → API Gateway
   - Find your API (e.g., "bulk-email-api")
   - Verify resources exist:
     - `/preview` with POST method
     - `/preview/{preview_id}` with GET method

2. **Test in Web UI:**
   - Open the email campaign editor
   - Create a simple email with subject and body
   - Click "👁️ Preview Email" button
   - **Expected:** New window opens with formatted preview
   - **If fails:** Check browser console (F12) for errors

3. **Check Console Output:**
   ```
   👁️ PREVIEW: Locking image sizes and positions...
   👁️ PREVIEW: Sending to backend...
   👁️ PREVIEW: Generated successfully!
   👁️ PREVIEW: Opening in new window: https://...
   ```

## 🔍 Troubleshooting

### Preview Button Does Nothing

**Cause:** API Gateway endpoints not configured

**Solution:**
```bash
python add_preview_endpoint.py
```

### 404 Error When Clicking Preview

**Cause:** `/preview` endpoint doesn't exist

**Check:**
1. Run `python add_preview_endpoint.py`
2. Verify in API Gateway Console
3. Check deployment to 'prod' stage

### 500 Error in Preview

**Cause:** Lambda function not updated or permissions missing

**Solutions:**
1. Run `python deploy_bulk_email_api.py` to update Lambda
2. Check Lambda has S3 permissions:
   - `s3:PutObject` for `email-previews/*`
   - `s3:GetObject` for `email-previews/*`
3. Check Lambda has DynamoDB permissions:
   - `dynamodb:PutItem` for `EmailCampaigns` table
   - `dynamodb:GetItem` for `EmailCampaigns` table

### Preview Window Shows "Preview Not Found"

**Cause:** DynamoDB or S3 save failed

**Check CloudWatch Logs:**
```
/aws/lambda/bulk-email-api-function
```

Look for:
- `📧 Saving email preview...`
- `✅ Saved preview HTML to S3`
- `✅ Saved preview metadata to DynamoDB`

## 📋 Complete Deployment Checklist

- [ ] Run `python deploy_bulk_email_api.py`
- [ ] Run `python add_preview_endpoint.py`
- [ ] Verify `/preview` endpoint exists in API Gateway
- [ ] Verify `/preview/{preview_id}` endpoint exists
- [ ] Check both endpoints deployed to 'prod' stage
- [ ] Test preview button in web UI
- [ ] Verify new window opens with preview
- [ ] Check CloudWatch logs for errors
- [ ] Test with images (paste, resize, preview)
- [ ] Verify image sizes match in preview

## 🎯 Quick Test

After deployment:

```bash
# 1. Open the web UI in browser
# 2. Go to Campaigns tab
# 3. Enter:
#    - Campaign Name: "Test Preview"
#    - Subject: "Hello World"
#    - Body: "This is a test"
# 4. Click "👁️ Preview Email"
# 5. New window should open showing the preview
```

## 📊 Expected API Gateway Structure

After running `add_preview_endpoint.py`:

```
API Gateway: bulk-email-api
├── / (root)
├── /config
├── /contacts
├── /campaign
├── /upload-attachment
└── /preview ← NEW
    ├── POST /preview ← NEW (save preview)
    └── /{preview_id} ← NEW
        └── GET /preview/{preview_id} ← NEW (retrieve preview)
```

## 🔗 Related Documentation

- **Full Feature Guide:** `EMAIL_PREVIEW_FEATURE.md`
- **Image Locking:** `IMAGE_SIZE_POSITION_LOCKING.md`
- **Image Resize Fix:** `QUILL_IMAGE_RESIZE_FIX.md`

---

**Last Updated:** October 10, 2025

**Status:** ✅ Scripts ready - Run both deployment steps to enable preview

