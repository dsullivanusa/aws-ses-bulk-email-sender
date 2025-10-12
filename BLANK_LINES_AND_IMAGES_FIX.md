# Blank Lines and Embedded Images Fix

## 🐛 Issues Fixed

### Issue 1: Blank Lines Removed
**Problem:** When users add blank lines in the Quill editor, they were being removed from sent emails.

**Root Cause:** HTML cleanup was removing `<p><br></p>` tags that represent blank lines.

**Solution:** Preserve blank lines by converting `<p><br></p>` to `<p>&nbsp;</p>` instead of removing them.

### Issue 2: Embedded Images Not in Recipients' Emails
**Problem:** Embedded images uploaded to S3 weren't appearing in recipients' emails. Email worker logs showed "no <img> tags found in HTML body".

**Root Causes:**
1. **CRITICAL BUG:** Frontend was removing `data-s3-key` attributes BEFORE doing S3 key replacement
   - Line 4166-4171 removed ALL data-* attributes from images
   - This happened BEFORE line 4376 tried to use data-s3-key for replacement
   - Result: S3 keys were uploaded but never inserted into HTML body
2. Email worker wasn't detecting S3 keys in format `campaign-attachments/...`
3. S3 operations required AWS Signature Version 4 for KMS-encrypted buckets

**Solutions:**
1. **CRITICAL FIX:** Preserve `data-s3-key` and `data-inline` attributes during Quill cleanup
2. Do S3 key replacement using preserved attributes
3. Remove data attributes AFTER replacement is complete
4. Updated email worker to detect simple S3 key paths
5. Configured S3 client with signature_version='s3v4'

### Issue 3: Preview Window Line Spacing
**Problem:** Preview window showed 1.5 line spacing instead of 1.0.

**Solution:** Changed line-height from 1.5 to 1.0 in preview CSS.

## 🔧 Fixes Applied

### Fix 0: CRITICAL - Preserve data-s3-key Attributes

**THE BUG:**
```javascript
// Step 1: Upload image, set data-s3-key attribute
img.setAttribute('data-s3-key', uploadResult.s3_key);

// Step 2: Remove ALL data-* attributes (INCLUDING data-s3-key!) ← BUG!
Array.from(element.attributes).forEach(attr => {
    if (attr.name.startsWith('data-')) {
        element.removeAttribute(attr.name);  // Removes data-s3-key!
    }
});

// Step 3: Try to use data-s3-key for replacement ← FAILS!
const imagesWithS3Keys = tempDiv.querySelectorAll('img[data-s3-key]');  // Returns nothing!
```

**THE FIX:**
```javascript
// Preserve data-s3-key and data-inline during cleanup
Array.from(element.attributes).forEach(attr => {
    if (attr.name.startsWith('data-') && 
        attr.name !== 'data-s3-key' &&      // PRESERVE for S3 replacement
        attr.name !== 'data-inline') {      // PRESERVE for inline flag
        element.removeAttribute(attr.name);
    }
});

// Now data-s3-key is available for replacement
const imagesWithS3Keys = tempDiv.querySelectorAll('img[data-s3-key]');  // Works!
```

### Fix 1: Blank Lines Preservation

**In both `sendCampaign()` and `previewCampaign()` functions:**

```javascript
// Before (removed blank lines):
emailBody = emailBody
    .replace(/<p><br><\/p>/g, '<p></p>')  // Removed blank lines
    .replace(/<p>\s*<\/p>/g, '')  // Removed all empty paragraphs
    .replace(/<\/p><p>/g, '<br>')  // Converted to line breaks

// After (preserves blank lines):
emailBody = emailBody
    .replace(/<p>\s*<br\s*\/?\s*>\s*<\/p>/g, '<p>&nbsp;</p>')  // Preserve blank lines
    .replace(/<p>\s*<\/p>/g, '')  // Remove only truly empty paragraphs
    // Keeps <p> structure intact
```

**Result:**
```html
<!-- User types in editor: -->
Line 1
[blank line]
Line 2

<!-- Becomes in email: -->
<p>Line 1</p>
<p>&nbsp;</p>     <!-- Blank line preserved -->
<p>Line 2</p>
```

### Fix 2: S3 Signature Version 4

**In both `bulk_email_api_lambda.py` and `email_worker_lambda.py`:**

```python
# Added import
from botocore.config import Config

# Updated S3 client initialization
s3_config = Config(signature_version='s3v4', region_name='us-gov-west-1')
s3_client = boto3.client('s3', region_name='us-gov-west-1', config=s3_config)
```

### Fix 3: Email Worker S3 Key Detection

**In `email_worker_lambda.py`:**

```python
# Before (didn't match simple S3 keys):
elif src.startswith('s3://') or (ATTACHMENTS_BUCKET in src and ...)

# After (matches simple S3 key paths):
elif (src.startswith('s3://') or 
      (ATTACHMENTS_BUCKET in src and ...) or
      src.startswith('campaign-attachments/') or    # NEW
      src.startswith('email-previews/')):            # NEW
    
    # Handle direct S3 key paths
    elif src.startswith('campaign-attachments/') or src.startswith('email-previews/'):
        s3_key_candidate = src  # Use path directly
        logger.info(f"Detected inline S3 key: {s3_key_candidate}")
```

### Fix 4: Preview Window Line Spacing

**In preview HTML CSS:**

```css
/* Before */
line-height: 1.5;

/* After */
line-height: 1.0;  /* True single spacing */
```

### Fix 5: Enhanced Debugging

**Added to both preview and send functions:**

```javascript
// Show <img> tags in email body
const imgMatches = emailBody.match(/<img[^>]+>/g);
if (imgMatches) {
    console.log(`🖼️ Email body contains ${imgMatches.length} <img> tag(s):`);
    imgMatches.forEach((tag, i) => {
        console.log(`  ${i + 1}. ${tag.substring(0, 100)}...`);
    });
}

// Show attachment details
if (campaignAttachments.length > 0) {
    console.log(`📎 Attachment details:`);
    campaignAttachments.forEach((att, i) => {
        console.log(`  ${i + 1}. ${att.filename} (s3_key: ${att.s3_key}, inline: ${att.inline})`);
    });
}
```

## 📊 Expected Console Output

### When Sending Campaign with Image and Blank Lines:

```
🖼️ Email body contains 1 <img> tag(s):
  1. <img src="campaign-attachments/1728577800-abc123-Image1.png" style="width: 400px;">...

📎 Campaign attachments: 1
📎 Attachment details:
  1. Image1_1728577800_0.png (s3_key: campaign-attachments/1728577800-abc123-Image1.png, inline: true)

✅ Applied HTML cleanup and preserved blank lines as <p>&nbsp;</p>
Final email body preview: <p>Line 1</p><p>&nbsp;</p><p>Line 2</p><img src="campaign-attachments/...
```

### CloudWatch Logs (Email Worker):

```
[Message 1] Detected inline S3 key: campaign-attachments/1728577800-abc123-Image1.png
[Message 1] Inlined S3 image campaign-attachments/... as CID <inline-s3-1-1728577800@inline>
```

## 🚀 Deployment

Deploy all three Lambda functions:

```bash
# 1. API Lambda (blank lines fix, preview improvements)
python deploy_bulk_email_api.py

# 2. Email Worker Lambda (S3 key detection, signature v4)
python deploy_email_worker.py
```

## ✅ Verification Steps

### Test Blank Lines:
1. Type in Quill editor:
   ```
   Line 1
   [press Enter twice to create blank line]
   Line 2
   ```
2. Send campaign to yourself
3. **Verify:** Blank line appears between Line 1 and Line 2

### Test Embedded Images:
1. Paste image in Quill editor
2. Send campaign to yourself
3. Check browser console for:
   - `🖼️ Email body contains 1 <img> tag(s)`
   - `📎 Attachment details: ... inline: true`
4. Check CloudWatch logs for:
   - `Detected inline S3 key: campaign-attachments/...`
5. **Verify:** Image appears in received email

## 📋 Files Modified

- ✅ `bulk_email_api_lambda.py`
  - Preserves blank lines as `<p>&nbsp;</p>`
  - S3 client with signature v4
  - Enhanced debugging
  - Line-height 1.0 in preview

- ✅ `email_worker_lambda.py`
  - Detects simple S3 key paths
  - S3 client with signature v4
  - Logs inline S3 key detection

---

**Status:** ✅ Ready for deployment

**Impact:** Critical - Affects email formatting and image display

**Last Updated:** October 12, 2025

