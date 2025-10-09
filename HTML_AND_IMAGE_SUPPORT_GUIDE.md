# HTML and Inline Image Support Guide

## 🎨 Overview

The email campaign editor now fully supports:
- ✅ **Pasting HTML** directly (Ctrl+V or Paste HTML button)
- ✅ **Inline images** embedded in email text
- ✅ **Copy/paste images** from anywhere
- ✅ **Rich text formatting** (bold, colors, lists, etc.)
- ✅ **Tables, links, and complex HTML**

## 📋 How to Use HTML Content

### Method 1: Copy/Paste HTML (Ctrl+V)
1. Copy HTML content from anywhere (webpage, Word, Outlook, etc.)
2. Click in the email body editor
3. Press **Ctrl+V** to paste
4. Quill automatically converts and renders the HTML
5. Send your campaign!

**What happens:**
- HTML is parsed and converted to Quill format
- Formatting is preserved (bold, italic, colors, lists, etc.)
- Links are preserved
- Tables are converted to Quill format
- Images are auto-extracted and uploaded to S3

### Method 2: Paste HTML Button
1. Click the **📋 Paste HTML** button below the editor
2. Paste your raw HTML in the dialog box
3. Click OK
4. HTML is imported into the editor
5. Send your campaign!

**Best for:**
- Pasting HTML from files
- Importing complex HTML templates
- Bulk HTML content

### Method 3: Type and Format
1. Type your content directly in the editor
2. Use the toolbar to format (bold, colors, etc.)
3. Insert images using the image button or paste
4. Send your campaign!

---

## 🖼️ Inline Image Support

### How Inline Images Work

When you paste or embed an image in the email body:

```
Step 1: User pastes image
  ↓
Step 2: Image detected as base64 data URI
  ↓
Step 3: Automatically uploaded to S3
  ↓
Step 4: Data URI replaced with S3 reference
  ↓
Step 5: Marked as inline attachment
  ↓
Step 6: Email sent with image embedded in text
  ↓
Step 7: Recipients see image in email body!
```

### Ways to Add Inline Images

#### 1. Copy/Paste Images
```
1. Copy an image from anywhere (webpage, screenshot, image file)
2. Click in the email editor where you want the image
3. Press Ctrl+V
4. Image appears in editor ✅
5. When sending, it's auto-uploaded and sent inline
```

#### 2. Drag and Drop (if supported by Quill)
```
1. Drag an image file
2. Drop it into the editor
3. Image appears inline ✅
```

#### 3. Use Image Button
```
1. Click the 🖼️ image button in toolbar
2. Paste image URL or data URI
3. Image appears in editor ✅
```

#### 4. Paste HTML with Images
```html
<!-- Paste HTML like this: -->
<p>Here is our product:</p>
<img src="data:image/png;base64,iVBORw0KG..." alt="Product">
<p>Amazing, right?</p>

<!-- Images are auto-extracted and uploaded to S3 ✅ -->
```

### Example: Email with Inline Images

```
Dear {{first_name}},

Thank you for your interest! Here's what we're offering:

[IMAGE 1: Product photo appears here]

As you can see from the image above, our product is excellent.

Key features:
• Feature 1
• Feature 2

[IMAGE 2: Diagram appears here]

The diagram shows how it works.

Best regards,
Your Team
```

---

## ✅ Supported HTML Elements

### Fully Supported
- `<p>` - Paragraphs
- `<h1>`, `<h2>`, `<h3>` - Headers
- `<strong>`, `<b>` - Bold
- `<em>`, `<i>` - Italic
- `<u>` - Underline
- `<s>`, `<strike>` - Strikethrough
- `<a href="">` - Links
- `<ol>`, `<ul>`, `<li>` - Lists
- `<img src="">` - Images (auto-converted)
- `<br>` - Line breaks
- `<span style="">` - Inline styles

### Partially Supported
- `<table>` - Converted to basic format
- `<div>` - Converted to paragraphs
- Custom CSS classes - May be stripped
- Complex styles - Simplified

### Not Supported (Stripped by Quill)
- `<script>` - JavaScript (security)
- `<iframe>` - Frames
- `<form>` - Forms
- `<input>` - Form inputs

---

## 🎨 Supported Formatting

### Text Formatting
- ✅ **Bold** - `<strong>` or `<b>`
- ✅ **Italic** - `<em>` or `<i>`
- ✅ **Underline** - `<u>`
- ✅ **Strikethrough** - `<s>` or `<strike>`
- ✅ **Colors** - Text and background colors
- ✅ **Font sizes** - Headers (H1, H2, H3)

### Structure
- ✅ **Paragraphs** - `<p>`
- ✅ **Line breaks** - `<br>`
- ✅ **Lists** - Ordered and unordered
- ✅ **Alignment** - Left, center, right
- ✅ **Links** - Clickable URLs

### Advanced
- ✅ **Images** - Inline with text
- ✅ **Placeholders** - `{{first_name}}`, etc.
- ⚠️ **Tables** - Basic support (may need reformatting)

---

## 📝 Example HTML Templates

### Simple Newsletter Template
```html
<h2>Monthly Newsletter</h2>

<p>Dear {{first_name}},</p>

<p>Welcome to our monthly newsletter!</p>

<img src="data:image/png;base64,..." alt="Banner">

<h3>This Month's Highlights</h3>
<ul>
  <li>New feature releases</li>
  <li>Customer success stories</li>
  <li>Upcoming events</li>
</ul>

<p>Best regards,<br>
The Team</p>
```

### Marketing Email Template
```html
<div style="text-align: center;">
  <h1 style="color: #3b82f6;">Special Offer!</h1>
  
  <p>Hi {{first_name}},</p>
  
  <img src="data:image/jpeg;base64,..." alt="Product" style="max-width: 600px;">
  
  <p style="font-size: 18px; color: #059669;">
    <strong>Save 50% this week only!</strong>
  </p>
  
  <p>
    <a href="https://example.com/offer" style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
      Shop Now
    </a>
  </p>
</div>
```

---

## 🔧 Technical Details

### Automatic Processing

When you click **Send Campaign**, the system:

1. **Gets HTML from Quill:**
   ```javascript
   let emailBody = quillEditor.root.innerHTML;
   ```

2. **Cleans Quill artifacts:**
   - Removes `class="ql-*"` attributes
   - Removes `data-*` attributes
   - Removes clipboard containers

3. **Processes embedded images:**
   - Detects `img[src^="data:"]` tags
   - Extracts base64 data
   - Uploads to S3
   - Replaces with S3 references
   - Marks as inline attachments

4. **Sends to backend:**
   ```javascript
   {
     body: emailBody,  // Cleaned HTML
     attachments: [    // Includes inline images
       {filename: "image.png", s3_key: "...", inline: true}
     ]
   }
   ```

5. **Email worker processes:**
   - Downloads images from S3
   - Attaches as inline with CID references
   - Converts `img src="s3_key"` to `img src="cid:..."`
   - Sends email with embedded images

### Console Logging

You'll see these messages when images are processed:
```
🖼️ Found 2 embedded image(s) in email body - converting to inline attachments
Uploading embedded image 1/2: InlineImage1.png (125.5 KB)
✅ Uploaded embedded image: attachments/InlineImage1_123456.png
Uploading embedded image 2/2: InlineImage2.png (87.3 KB)
✅ Uploaded embedded image: attachments/InlineImage2_654321.png
✅ Converted 2 embedded image(s) to inline attachments
```

---

## 🚨 Limitations and Workarounds

### Limitation 1: Complex CSS Styles
**Problem:** Some advanced CSS may be simplified by Quill

**Workaround:**
- Use the Paste HTML button for complex styles
- Quill will preserve what it can
- Test with a sample email first

### Limitation 2: Very Large Images
**Problem:** Large embedded images can be slow to upload

**Workaround:**
- Resize images before pasting
- Use compressed formats (JPEG instead of PNG)
- Keep images under 5MB each

### Limitation 3: External Image Links
**Problem:** Images with `src="http://..."` URLs may not display if server blocks

**Workaround:**
- Download and embed the image instead
- Or use the attachment system

---

## 💡 Best Practices

### For Inline Images

1. **Optimize image sizes**
   - Compress images before embedding
   - Use JPEG for photos (smaller)
   - Use PNG for graphics with transparency

2. **Use descriptive alt text**
   - Helps if image doesn't load
   - Better for accessibility
   - Example: `<img src="..." alt="Product diagram">`

3. **Keep total email size reasonable**
   - Email with many large images = slow to send
   - Recommend: 3-5 images max per email
   - Total size: Under 10MB per email

### For HTML Content

1. **Test with a sample first**
   - Send to yourself before mass campaign
   - Check formatting in different email clients

2. **Use inline styles**
   - Better than CSS classes
   - More likely to work across email clients
   - Example: `<p style="color: blue;">Text</p>`

3. **Keep HTML simple**
   - Complex layouts may not render well
   - Email clients have limited CSS support
   - Simpler = more reliable

4. **Use placeholders**
   - Personalize with `{{first_name}}`, etc.
   - Makes emails feel more personal
   - Higher engagement rates

---

## 🧪 Testing

### Test Inline Images

1. Open Send Campaign tab
2. Type: "Here is our logo:"
3. **Paste an image** (Ctrl+V)
4. Type: "Pretty cool, right?"
5. Add email address to To field
6. Click Send Campaign
7. Check your email - image should appear inline!

### Test HTML Paste

1. Create HTML file:
   ```html
   <h2>Test Email</h2>
   <p>This is <strong>bold</strong> and <em>italic</em>.</p>
   <img src="data:image/png;base64,iVBORw0K..." alt="Test">
   <p>Image above should appear inline!</p>
   ```
2. Copy the HTML
3. Click **📋 Paste HTML** button
4. Paste and click OK
5. Send to yourself
6. Verify formatting and images appear correctly

---

## 🔍 Troubleshooting

### "Campaign Failed: Unexpected Token"
**Cause:** Very large embedded image causing JSON parsing error

**Solution:**
- The new code should prevent this automatically
- If it still occurs, images may be too large
- Try compressing images first

### Images Don't Upload
**Cause:** Upload endpoint error or network issue

**Solution:**
- Check console for error messages
- Verify S3 bucket permissions
- Try smaller images

### HTML Formatting Lost
**Cause:** Quill simplified some styles

**Solution:**
- Use simpler HTML
- Use inline styles instead of CSS classes
- Use Quill's toolbar for formatting

### Images Appear as Attachments Instead of Inline
**Cause:** Email client doesn't support inline images

**Solution:**
- This is normal for some email clients
- Most modern email clients support inline images
- Gmail, Outlook, Apple Mail all work

---

## 📊 What's Happening Behind the Scenes

### When You Paste HTML:

```
User pastes HTML
  ↓
Quill.clipboard.convert(html)
  ↓
Quill renders in editor
  ↓
quillEditor.root.innerHTML
  ↓
Clean Quill artifacts
  ↓
Extract embedded images
  ↓
Upload images to S3
  ↓
Replace data: URIs with S3 keys
  ↓
Send campaign with attachments
  ↓
Email worker downloads from S3
  ↓
Attach as inline with CID
  ↓
Replace S3 keys with cid: references
  ↓
Send via AWS SES
  ↓
Recipient sees formatted email with inline images! 🎉
```

---

## 🎯 Common Use Cases

### Use Case 1: Newsletter with Banner
```html
<img src="[paste your banner]" alt="Newsletter Banner" style="width: 100%; max-width: 600px;">

<h2>Monthly Update - January 2025</h2>

<p>Dear {{first_name}},</p>

<p>Here's what's new this month...</p>
```

### Use Case 2: Product Showcase
```html
<h3>Introducing Our New Product</h3>

<div style="text-align: center;">
  <img src="[paste product image]" alt="Product" style="max-width: 400px;">
</div>

<p>Features:</p>
<ul>
  <li>Feature 1</li>
  <li>Feature 2</li>
</ul>
```

### Use Case 3: Event Invitation
```html
<h1 style="color: #3b82f6; text-align: center;">You're Invited!</h1>

<img src="[paste event photo]" alt="Event" style="width: 100%; border-radius: 8px;">

<p><strong>When:</strong> January 15, 2025</p>
<p><strong>Where:</strong> Virtual Event</p>

<p style="text-align: center;">
  <a href="https://register.example.com" style="background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
    Register Now
  </a>
</p>
```

---

## 🎓 Advanced Tips

### Tip 1: Use Inline Styles
Email clients don't support `<style>` tags well, so use inline styles:

```html
<!-- Bad -->
<style>
  .header { color: blue; }
</style>
<p class="header">Text</p>

<!-- Good -->
<p style="color: blue;">Text</p>
```

### Tip 2: Responsive Images
Make images scale to different screen sizes:

```html
<img src="..." alt="..." style="max-width: 100%; height: auto;">
```

### Tip 3: Combine with Placeholders
Personalize your HTML emails:

```html
<p>Dear {{first_name}} {{last_name}},</p>

<p>Your email address on file is: {{email}}</p>

<img src="..." alt="Welcome">

<p>Welcome to {{agency_name}}!</p>
```

### Tip 4: Center Images
```html
<div style="text-align: center;">
  <img src="..." alt="Centered Image" style="max-width: 500px;">
</div>
```

### Tip 5: Add Captions
```html
<div style="text-align: center;">
  <img src="..." alt="Chart">
  <p style="font-size: 12px; color: #6b7280; margin-top: 5px;">
    Figure 1: Sales Growth Chart
  </p>
</div>
```

---

## 📈 Performance Considerations

### Image Size Recommendations

| Image Type | Recommended Size | Max Size |
|------------|------------------|----------|
| Logo | 50-100 KB | 500 KB |
| Banner | 200-500 KB | 2 MB |
| Product Photo | 100-300 KB | 1 MB |
| Diagram/Chart | 50-200 KB | 1 MB |
| Icon | 10-50 KB | 200 KB |

### Email Size Limits

- **Per email:** 40 MB total (all attachments + inline images)
- **Recommended:** Keep under 5 MB for better deliverability
- **Best practice:** 1-2 MB total (faster sending, better inbox placement)

### Number of Images

- **Recommended:** 3-5 images per email
- **Maximum:** 10 images (but will be slow)
- **Best practice:** 1-3 images for faster delivery

---

## 🔧 Configuration

### Quill Editor Settings

Location: `bulk_email_api_lambda.py` lines 1641-1655

Current configuration:
```javascript
quillEditor = new Quill('#body', {
    theme: 'snow',
    modules: {
        toolbar: [
            [{ 'header': [1, 2, 3, false] }],
            ['bold', 'italic', 'underline', 'strike'],
            [{ 'color': [] }, { 'background': [] }],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            [{ 'align': [] }],
            ['link', 'image'],
            ['clean']
        ]
    }
});
```

### Inline Image Processing

Location: `bulk_email_api_lambda.py` lines 3838-3919

- Automatically detects embedded images
- Uploads to S3 in background
- Converts to inline attachments
- Shows progress in console

---

## 🚀 Quick Reference

### ✅ YES - These Work Great

| Feature | How to Use | Result |
|---------|-----------|--------|
| **Paste HTML** | Ctrl+V or Paste HTML button | ✅ Formatting preserved |
| **Paste Images** | Ctrl+V with image copied | ✅ Images inline |
| **Bold/Italic** | Toolbar or `<strong>`/`<em>` | ✅ Works perfectly |
| **Colors** | Toolbar or inline styles | ✅ Works perfectly |
| **Links** | Toolbar or `<a href="">` | ✅ Works perfectly |
| **Lists** | Toolbar or `<ul>`/`<ol>` | ✅ Works perfectly |
| **Headers** | Toolbar or `<h1>`, `<h2>`, `<h3>` | ✅ Works perfectly |
| **Placeholders** | Type `{{first_name}}` | ✅ Personalized per recipient |

### ⚠️ MAYBE - May Be Simplified

| Feature | What Happens |
|---------|-------------|
| **Tables** | Converted to simpler format |
| **Complex layouts** | May be simplified |
| **Custom fonts** | May fall back to default |
| **Advanced CSS** | May be stripped |

### ❌ NO - Not Supported

| Feature | Why Not | Alternative |
|---------|---------|-------------|
| **JavaScript** | Security risk | Use links instead |
| **Forms** | No interactivity in email | Link to web form |
| **Video** | Too large | Link to video |
| **Audio** | Not supported in email | Link to audio file |

---

## 🎉 Summary

**YES!** Users can:
- ✅ **Copy/paste HTML** from anywhere (Ctrl+V)
- ✅ **Embed images** inline with text
- ✅ **Use rich formatting** (bold, colors, lists, etc.)
- ✅ **Paste from Word, Outlook, web pages**
- ✅ **Combine images and text**
- ✅ **Use placeholders** for personalization

**The system automatically:**
- Converts embedded images to S3 attachments
- Preserves HTML formatting
- Sends emails with inline images
- Handles errors gracefully

**Recipients see:**
- Beautifully formatted HTML emails
- Images embedded in the text (not as attachments)
- Personalized content with placeholders
- Professional-looking emails

---

## 📞 Need Help?

Common questions:

**Q: Can I paste from Microsoft Word?**  
A: Yes! Copy from Word and paste (Ctrl+V) into the editor.

**Q: Can I paste a full HTML email template?**  
A: Yes! Use the 📋 Paste HTML button or Ctrl+V.

**Q: Will images stay in the right position?**  
A: Yes! Images appear exactly where you place them.

**Q: Can I edit after pasting?**  
A: Yes! Use the toolbar to make changes.

**Q: How many images can I include?**  
A: Recommended: 3-5 images. Maximum: 40MB total.

---

**Ready to create beautiful HTML emails with inline images!** 🎨✨

