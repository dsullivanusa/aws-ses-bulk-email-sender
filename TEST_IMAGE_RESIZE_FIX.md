# Test Scenario: Image Resize Fix

## Purpose
Verify that images in sent emails match EXACTLY the size and position shown in the Quill editor. This includes testing resize functionality, alignment, and position locking.

## Prerequisites
- Lambda function deployed with the fix (`bulk_email_api_lambda.py`)
- Access to the email campaign editor
- A test contact or your own email address

## Test Steps

### Test 1: Basic Image Paste and Resize

1. **Open the Campaign Editor**
   - Navigate to the Campaigns tab
   - Create a new campaign or open an existing one

2. **Add an Image**
   - Copy any image (from a website, screenshot, or file)
   - Click in the email body editor
   - Press Ctrl+V to paste the image
   - The image should appear in the editor

3. **Resize the Image**
   - Click on the pasted image
   - You should see resize handles appear at the corners
   - Drag a corner handle to resize the image
   - Resize to approximately 400px wide (or any size)

4. **Verify Console Output**
   - Open browser Developer Tools (F12)
   - Go to Console tab
   - You should see:
     ```
     ✂️ Unwrapped 1 image(s) from resize containers
       📐 Preserved sizing from wrapper: width: 400px
     🖼️ Found 1 embedded image(s) in email body
     Uploading embedded image 1/1...
     ✅ Uploaded embedded image: attachments/InlineImage1_....png
     ```

5. **Send Test Campaign**
   - Fill in campaign details (subject, from email)
   - Select a test contact or enter your email in the "To" field
   - Click "Send Campaign"
   - Confirm the send

6. **Check Received Email**
   - Open your email inbox
   - Find the test campaign email
   - **VERIFY:** The resized image appears in the email body
   - **VERIFY:** The image size matches what you set in the editor

### Test 2: Multiple Resized Images

1. **Paste Multiple Images**
   - Paste 3 different images into the email body
   - Add some text between them:
     ```
     Image 1:
     [paste image 1]
     
     Image 2:
     [paste image 2]
     
     Image 3:
     [paste image 3]
     ```

2. **Resize Each Image Differently**
   - Click image 1, resize to ~300px wide
   - Click image 2, resize to ~500px wide  
   - Click image 3, resize to ~200px wide

3. **Verify Console Shows All Images**
   - Console should show:
     ```
     ✂️ Unwrapped 3 image(s) from resize containers
       📐 Preserved sizing from wrapper: width: 300px
       📐 Preserved sizing from wrapper: width: 500px
       📐 Preserved sizing from wrapper: width: 200px
     🖼️ Found 3 embedded image(s) in email body
     ```

4. **Send and Verify**
   - Send the campaign
   - Check that all 3 images appear with correct sizes

### Test 3: Mix of Resized and Non-Resized Images

1. **Paste Two Images**
   - Paste image 1 and DON'T resize it (don't click it)
   - Paste image 2 and resize it by clicking and dragging

2. **Verify Both Are Processed**
   - Console should show both images uploaded
   - One might show unwrapping, one might not

3. **Send and Verify**
   - Both images should appear in the email

### Test 4: Centered and Aligned Images

1. **Test Center Alignment**
   - Paste an image
   - Click in the paragraph containing the image
   - Use Quill's alignment button to center the paragraph
   - Resize the image to ~400px
   - Verify console shows "Preserved container alignment: center"
   - Send campaign

2. **Verify Center Alignment in Email**
   - Image should be centered in the email
   - Size should match what you set in editor

3. **Test Right Alignment**
   - Paste another image
   - Right-align the paragraph
   - Resize to ~300px
   - Send campaign
   - Verify right alignment is preserved

4. **Check Console**
   - Should show: `📍 Preserved container alignment: center`
   - Should show: `📍 Preserved container alignment: right`

### Test 5: Size Locking at Send Time

1. **Verify Size Is Locked When Sending**
   - Paste an image
   - Resize to 500px wide
   - Click "Send Campaign" button
   - Check console immediately

2. **Console Should Show:**
   ```
   🔒 Locked image 1 size/position: {width: "500px", height: "XXXpx", ...}
     ✅ Applied locked styles to image 1
   🔒 Locked 1 image(s) to exact editor size/position
   ```

3. **Verify Exact Match**
   - Measure image in editor (should be 500px)
   - Measure image in received email (should be 500px)
   - They should match EXACTLY

### Test 6: Resize After Initial Paste

1. **Paste an Image**
   - Paste an image and immediately send WITHOUT resizing
   - Verify it appears in email (baseline)

2. **Paste and Resize After Delay**
   - Paste a new image
   - Wait 5 seconds
   - Click the image to activate resize handles
   - Resize the image
   - Send campaign

3. **Verify**
   - Resized image should appear correctly

## Expected Results

### ✅ Success Criteria

- [x] Images appear in received emails
- [x] Image sizes in email EXACTLY match editor preview
- [x] Image positions/alignment match editor (center, left, right)
- [x] Console shows "🔒 Locked X image(s) to exact editor size/position"
- [x] Console shows "✅ Applied locked styles to image X"
- [x] Console shows "Unwrapped X image(s) from resize containers"
- [x] Console shows "📍 Preserved container alignment" (if centered/right-aligned)
- [x] No errors during campaign send
- [x] All images upload successfully to S3
- [x] Email looks identical to editor preview (WYSIWYG)

### ❌ Failure Indicators

- [ ] Images missing from received emails
- [ ] Console errors about image upload
- [ ] Wrong image sizes in received emails
- [ ] Console shows "WARNING: Email body still contains data:image URIs"

## Troubleshooting

### Issue: Images Still Don't Appear

**Check:**
1. Console for upload errors
2. S3 bucket permissions
3. Lambda function was deployed with the fix

**Solution:**
```bash
python deploy_bulk_email_api.py
```

### Issue: Wrong Image Sizes

**Check:**
- Console output for "Preserved sizing" messages
- Ensure you're clicking the image to activate resize handles before resizing

**Solution:**
- The fix should handle this automatically
- Check that you're actually dragging the resize handles (not just changing the style manually)

### Issue: Console Shows No Unwrapping

**Possible Causes:**
1. Image wasn't wrapped by resize module (no resize handles activated)
2. Image was in a `<p>` tag (intentionally not unwrapped)

**This is OK if:**
- Images still appear in sent emails
- You didn't activate resize handles

## Debug Console Commands

Open browser console and run these to inspect:

```javascript
// Show all images in editor
document.querySelectorAll('#body img')

// Show image wrapper elements
document.querySelectorAll('#body span, #body div')

// Check if resize module is loaded
typeof ImageResize !== 'undefined'

// Check Quill editor content
quillEditor.root.innerHTML
```

## Rollback

If the fix causes issues:

1. Revert `bulk_email_api_lambda.py` to previous version
2. Deploy: `python deploy_bulk_email_api.py`

Or temporarily disable unwrapping by setting:
```javascript
const ENABLE_IMAGE_UNWRAP = false;  // Add at line 3939
if (!ENABLE_IMAGE_UNWRAP) return;    // Add at line 3943
```

## Related Documentation

- `QUILL_IMAGE_RESIZE_FIX.md` - Technical details about the fix
- `HTML_AND_IMAGE_SUPPORT_GUIDE.md` - General image handling
- `S3_ATTACHMENTS_GUIDE.md` - Attachment upload system

---

**Last Updated:** October 10, 2025

