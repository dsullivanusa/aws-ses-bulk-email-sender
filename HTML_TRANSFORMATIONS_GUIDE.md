# HTML Transformations Guide

## ❓ Question: If I paste HTML code in the Quill editor, does the same HTML code appear in the recipient's email?

**Short Answer:** **Almost, but with important modifications.** The HTML is cleaned and transformed to work reliably across email clients.

## 🔄 What Happens to Pasted HTML

### Step 1: You Paste HTML into Quill Editor

**You paste:**
```html
<div class="my-custom-class" style="background: blue;">
  <p class="ql-align-center" data-custom="value">Hello World</p>
  <img src="data:image/png;base64,iVBORw0KGgoAAAANS..." alt="Logo">
</div>
```

**Quill processes it:**
- Quill converts to its internal format
- Adds Quill-specific classes (`ql-*`)
- May add data attributes for editor functionality
- Stores images as data: URIs

### Step 2: You Click "Send Campaign" or "Preview Email"

**HTML Cleanup Pipeline:**

#### 2A. Lock Image Sizes
```javascript
// Captures exact size from rendered editor
window.getComputedStyle(img) → width: 400px, height: 300px
// Applied to images so recipients see same size
```

#### 2B. Unwrap Images from Resize Containers
```javascript
// Before: <span style="width: 400px"><img src="..."></span>
// After:  <img src="..." style="width: 400px;">
```

#### 2C. Remove Quill-Specific Attributes
```javascript
// REMOVED:
- class="ql-align-center"     // Quill classes
- class="ql-indent-1"
- data-* (EXCEPT data-s3-key)  // Quill internal data
- contenteditable
- spellcheck, autocorrect, autocapitalize

// PRESERVED:
- Your custom classes (removed)  ← YES, removed
- style attributes  ← YES, preserved
- id attributes  ← YES, preserved
- HTML structure  ← YES, preserved
```

#### 2D. Remove Clipboard Containers
```javascript
// Removes .ql-clipboard elements (Quill artifacts)
```

#### 2E. Convert Embedded Images
```javascript
// Before: <img src="data:image/png;base64,iVBORw0...">
// Upload to S3
// After:  <img src="campaign-attachments/12345-image.png">
```

#### 2F. Clean Up Empty Elements
```javascript
// Blank lines: <p><br></p> → <p>&nbsp;</p>  ← PRESERVED
// Empty paragraphs: <p></p> → (removed)
// Double line breaks: <br><br> → <br>
// Empty class attributes: class="" → (removed)
```

#### 2G. Backend Processing (email_worker_lambda.py)
```python
# Personalize placeholders
"Hello {{first_name}}" → "Hello John"

# Convert S3 keys to CID references
<img src="campaign-attachments/12345.png"> → <img src="cid:inline-s3-1@inline">

# Clean Quill HTML (clean_quill_html_for_email function)
# - Removes remaining ql-* classes
# - Removes data-* attributes
# - Normalizes spacing
```

### Step 3: Recipient Receives

**They see:**
```html
<div style="background: blue;">
  <p>Hello John</p>
  <img src="cid:inline-s3-1@inline" style="width: 400px; height: 300px;" alt="Logo">
</div>
```

## ✅ What Is PRESERVED

| Element | Preserved? | Notes |
|---------|------------|-------|
| **HTML structure** | ✅ YES | `<div>`, `<p>`, `<span>`, etc. all preserved |
| **Inline styles** | ✅ YES | `style="..."` attributes preserved |
| **ID attributes** | ✅ YES | `id="..."` preserved |
| **Images** | ✅ YES | Converted to inline attachments |
| **Links** | ✅ YES | `<a href="...">` preserved |
| **Tables** | ✅ YES | `<table>` structure preserved |
| **Formatting tags** | ✅ YES | `<strong>`, `<em>`, `<u>` preserved |
| **Lists** | ✅ YES | `<ul>`, `<ol>`, `<li>` preserved |
| **Blank lines** | ✅ YES | Converted to `<p>&nbsp;</p>` |
| **Colors** | ✅ YES | Inline color styles preserved |
| **Font sizes** | ✅ YES | Inline font-size styles preserved |

## ❌ What Is REMOVED/CHANGED

| Element | Changed? | Transformation |
|---------|----------|----------------|
| **CSS classes** | ❌ REMOVED | All `class="..."` attributes removed |
| **Quill classes** | ❌ REMOVED | `ql-align-center`, `ql-indent-1`, etc. |
| **data-* attributes** | ❌ REMOVED | All data attributes removed (after processing) |
| **External CSS** | ❌ REMOVED | `<link>` and `<style>` tags may be removed |
| **JavaScript** | ❌ REMOVED | `<script>` tags removed (email security) |
| **Embedded images** | ✅ CONVERTED | `data:image` → S3 → `cid:` references |
| **Empty paragraphs** | ❌ REMOVED | `<p></p>` removed (but `<p>&nbsp;</p>` kept) |
| **Double <br>** | ✅ REDUCED | `<br><br>` → `<br>` |
| **Placeholders** | ✅ REPLACED | `{{first_name}}` → actual values |

## 🎯 Best Practices for Pasted HTML

### ✅ DO Use (Will Work)

```html
<!-- Inline styles (recommended for email) -->
<p style="color: red; font-size: 16px;">Red text</p>

<!-- Inline images (will be converted) -->
<img src="data:image/png;base64,..." alt="Logo">

<!-- Tables with inline styles -->
<table style="border: 1px solid black;">
  <tr><td style="padding: 10px;">Cell</td></tr>
</table>

<!-- Links -->
<a href="https://example.com" style="color: blue;">Click here</a>

<!-- Formatting -->
<strong>Bold</strong> <em>Italic</em> <u>Underline</u>

<!-- Colors and fonts -->
<span style="color: #FF0000; font-family: Arial;">Styled text</span>
```

### ❌ AVOID (Will Be Removed)

```html
<!-- CSS classes (will be removed) -->
<p class="my-custom-class">Text</p>  ← class removed

<!-- External stylesheets (won't load in emails anyway) -->
<link rel="stylesheet" href="style.css">  ← removed

<!-- JavaScript (security risk) -->
<script>alert('hi')</script>  ← removed

<!-- data-* attributes (removed) -->
<div data-custom="value">Text</div>  ← data-custom removed

<!-- Empty paragraphs (removed) -->
<p></p>  ← removed
```

## 📝 Example Transformation

### Input (Pasted HTML):
```html
<div class="header" style="background: #f0f0f0; padding: 20px;" data-section="top">
  <h1 class="ql-align-center" style="color: blue;">Newsletter</h1>
  <img class="logo" src="data:image/png;base64,iVBORw..." alt="Logo" style="width: 200px;">
  <p class="ql-indent-1">Dear {{first_name}} {{last_name}},</p>
  <p><br></p>
  <p>This is our monthly update.</p>
  <p></p>
  <p>Best regards,<br>The Team</p>
</div>
```

### Output (Sent to Recipients):
```html
<div style="background: #f0f0f0; padding: 20px;">
  <h1 style="color: blue;">Newsletter</h1>
  <img src="cid:inline-s3-1@inline" alt="Logo" style="width: 200px; height: 150px;">
  <p>Dear John Doe,</p>
  <p>&nbsp;</p>
  <p>This is our monthly update.</p>
  <p>Best regards,<br>The Team</p>
</div>
```

### What Changed:
- ✅ **Preserved:** Structure, inline styles, content
- ❌ **Removed:** All classes (`header`, `logo`, `ql-align-center`, `ql-indent-1`)
- ❌ **Removed:** data-section attribute
- ✅ **Converted:** Image data URI → S3 → CID reference
- ✅ **Added:** Exact image dimensions from editor
- ✅ **Replaced:** Placeholders with contact data
- ✅ **Preserved:** Blank line as `<p>&nbsp;</p>`
- ❌ **Removed:** Empty `<p></p>`

## 💡 Recommendations

### For Maximum Compatibility:

1. **Use Inline Styles Only**
   ```html
   <!-- Good -->
   <p style="color: red; font-size: 16px;">Text</p>
   
   <!-- Avoid (class will be removed) -->
   <p class="red-text">Text</p>
   ```

2. **Keep HTML Simple**
   - Avoid complex CSS
   - Avoid nested div structures
   - Use tables for layout (email-friendly)

3. **Test with Preview**
   - Click "Preview Email" to see exactly what recipients get
   - Preview shows the final HTML after all transformations

4. **Use Placeholders**
   ```html
   <p>Hello {{first_name}},</p>
   <p>Your email is {{email}}</p>
   ```

5. **Embed Images**
   - Paste images directly (Ctrl+V)
   - They'll be automatically uploaded to S3
   - Appear as inline images in recipient emails

## 🔍 How to See Transformations

### Browser Console (F12):
```javascript
📝 Original Quill HTML length: 5000 characters
✅ Cleaned Quill attributes
✅ tempDiv.innerHTML contains 1 <img> tag(s)
✅ After regex cleanup: 1 <img> tag(s) still present
🔍 BEFORE JSON: campaign.body has 1 <img> tag(s)
🖼️ Email body contains 1 <img> tag(s):
  1. <img src="campaign-attachments/12345.png" style="width: 400px;">
```

### CloudWatch Logs (Backend):
```python
📧 Campaign body sample: <div style="background: #f0f0f0;">...
🖼️ Found 1 <img> tag(s) in campaign body
📎 1 attachment(s) received: Image1.png - inline: true
```

## ✨ Summary

**Bottom Line:** 
- ✅ **HTML structure is preserved**
- ✅ **Inline styles are preserved**
- ✅ **Content is preserved**
- ❌ **CSS classes are removed**
- ❌ **data-* attributes are removed**
- ✅ **Images are converted to inline attachments**
- ✅ **Blank lines are preserved as `<p>&nbsp;</p>`**
- ✅ **Placeholders are replaced with contact data**

**Best Practice:** Use the **Preview button** to see exactly what recipients will receive before sending!

---

**Last Updated:** October 12, 2025

**Related Docs:**
- `EMAIL_PREVIEW_FEATURE.md` - Preview functionality
- `HTML_AND_IMAGE_SUPPORT_GUIDE.md` - HTML and image support
- `IMAGE_SIZE_POSITION_LOCKING.md` - Image size/position preservation

