# Attachment Upload Troubleshooting - 500 Error

## Quick Diagnosis

The 500 error when uploading attachments is most likely one of these issues:

### 1. ❌ `/upload-attachment` Endpoint Not Added
**Symptom:** 404 error (but might show as 500)

**Solution:**
```bash
python add_attachment_endpoint.py
```

### 2. ❌ Lambda Missing S3 Permissions
**Symptom:** 500 error with "AccessDenied" in logs

**Solution:** Add S3 permissions to Lambda role

### 3. ❌ S3 Bucket Doesn't Exist
**Symptom:** 500 error with "NoSuchBucket"

**Solution:** Verify bucket `jcdc-ses-contact-list` exists

## Detailed Troubleshooting Steps

### Step 1: Check Browser Console

1. Press **F12** to open Developer Tools
2. Go to **Console** tab
3. Try uploading a file again
4. Look for error messages:

```javascript
Uploading attachment: test.pdf (245.3 KB)
POST https://...amazonaws.com/prod/upload-attachment 404 (Not Found)
```

**404 = Endpoint not added** → Run `python add_attachment_endpoint.py`

```javascript
POST https://...amazonaws.com/prod/upload-attachment 500 (Internal Server Error)
```

**500 = Lambda or S3 error** → Check CloudWatch logs (Step 2)

### Step 2: Check Lambda CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/bulk-email-api-function --follow --region us-gov-west-1
```

**Look for these messages:**

**Message 1: Endpoint Working**
```
Upload attachment request received
Filename: test.pdf, ContentType: application/pdf, S3Key: campaign-attachments/...
Data length: 12458 characters
Decoding base64 data...
Decoded file size: 9344 bytes
Uploading to S3 bucket: jcdc-ses-contact-list, key: campaign-attachments/...
```

**Message 2: S3 Permission Error**
```
ERROR: S3 upload error: An error occurred (AccessDenied) when calling the PutObject operation: Access Denied
ERROR: S3 Access Denied: Lambda role does not have permission to write to bucket 'jcdc-ses-contact-list'
```

**Solution:** Add S3 permissions (see Step 3)

**Message 3: Bucket Not Found**
```
ERROR: S3 upload error: An error occurred (NoSuchBucket) when calling the PutObject operation
ERROR: S3 bucket 'jcdc-ses-contact-list' does not exist or is not accessible.
```

**Solution:** Verify bucket exists or update bucket name in code

### Step 3: Add S3 Permissions to Lambda Role

#### Option A: Via AWS Console

1. Go to **Lambda Console**
2. Select function: `bulk-email-api-function`
3. Go to **Configuration** → **Permissions**
4. Click on the **Role name** (opens IAM)
5. Click **Add permissions** → **Attach policies**
6. Search for and attach: `AmazonS3FullAccess`
7. Or create custom policy (recommended):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list"
        }
    ]
}
```

#### Option B: Via AWS CLI

```bash
# Get Lambda role name
ROLE_NAME=$(aws lambda get-function --function-name bulk-email-api-function --region us-gov-west-1 --query 'Configuration.Role' --output text | cut -d'/' -f2)

# Create policy file
cat > s3-attachment-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list/*"
        }
    ]
}
EOF

# Create and attach policy
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name S3AttachmentAccess \
  --policy-document file://s3-attachment-policy.json \
  --region us-gov-west-1
```

### Step 4: Verify S3 Bucket Exists

```bash
# Check if bucket exists
aws s3 ls s3://jcdc-ses-contact-list --region us-gov-west-1

# If bucket doesn't exist, create it
aws s3 mb s3://jcdc-ses-contact-list --region us-gov-west-1
```

### Step 5: Test Upload Manually

Test the endpoint directly:

```bash
# Create test base64 data
echo "Hello World" | base64

# Test endpoint (replace YOUR-API-ID)
curl -X POST https://YOUR-API-ID.execute-api.us-gov-west-1.amazonaws.com/prod/upload-attachment \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.txt",
    "content_type": "text/plain",
    "s3_key": "campaign-attachments/test-123.txt",
    "data": "SGVsbG8gV29ybGQK"
  }'
```

**Expected response:**
```json
{
  "success": true,
  "s3_key": "campaign-attachments/test-123.txt",
  "bucket": "jcdc-ses-contact-list",
  "size": 12
}
```

### Step 6: Verify File in S3

```bash
# List files in campaign-attachments folder
aws s3 ls s3://jcdc-ses-contact-list/campaign-attachments/ --region us-gov-west-1

# Download test file
aws s3 cp s3://jcdc-ses-contact-list/campaign-attachments/test-123.txt test-downloaded.txt --region us-gov-west-1
```

## Common Issues & Solutions

### Issue 1: 404 Not Found
**Cause:** `/upload-attachment` endpoint not in API Gateway

**Solution:**
```bash
python add_attachment_endpoint.py
```

### Issue 2: 403 Forbidden or AccessDenied
**Cause:** Lambda role lacks S3 permissions

**Solution:** Add S3 policy to Lambda role (see Step 3)

**Verify permissions:**
```bash
aws iam list-role-policies --role-name YOUR-LAMBDA-ROLE --region us-gov-west-1
aws iam list-attached-role-policies --role-name YOUR-LAMBDA-ROLE --region us-gov-west-1
```

### Issue 3: 500 Internal Server Error
**Cause:** Various Lambda errors

**Solutions:**
1. Check CloudWatch logs for specific error
2. Verify Lambda code is updated
3. Check S3 bucket exists
4. Verify IAM permissions

### Issue 4: Request Too Large
**Cause:** File too large for API Gateway (10 MB limit for API Gateway payload)

**Note:** Even though email limit is 40 MB, API Gateway has a 10 MB payload limit for requests.

**Solution for large files:**
- Compress files before uploading
- For files > 10 MB, you'd need to use S3 pre-signed URLs (different implementation)

### Issue 5: CORS Error
**Cause:** CORS not configured on `/upload-attachment`

**Solution:** The `add_attachment_endpoint.py` script configures CORS automatically

## Debugging Checklist

- [ ] Run: `python add_attachment_endpoint.py`
- [ ] Verify endpoint exists in API Gateway console
- [ ] Check Lambda has S3 permissions
- [ ] Verify S3 bucket `jcdc-ses-contact-list` exists
- [ ] Check CloudWatch logs during upload attempt
- [ ] Try uploading small file (< 1 MB) first
- [ ] Check browser console for detailed error
- [ ] Test endpoint with curl command
- [ ] Redeploy Lambda with updated code

## Quick Fix Command

Run all necessary deployment steps:

```bash
# 1. Update Lambda function
python update_lambda.py

# 2. Add upload endpoint
python add_attachment_endpoint.py

# 3. Add S3 permissions (if using IAM policy file)
ROLE_NAME=$(aws lambda get-function --function-name bulk-email-api-function --region us-gov-west-1 --query 'Configuration.Role' --output text | cut -d'/' -f2)

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name S3AttachmentAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws-us-gov:s3:::jcdc-ses-contact-list/*"
    }]
  }' \
  --region us-gov-west-1
```

## What the Error Messages Mean

**From Browser:**
- `404` = Endpoint doesn't exist
- `403` = Permission denied
- `500` = Lambda error (check logs)
- `413` = Request too large (file > 10 MB for API Gateway)

**From Lambda Logs:**
- `AccessDenied` = Need S3 permissions
- `NoSuchBucket` = Bucket doesn't exist
- `InvalidRequest` = Bad request format
- Base64 decode error = File encoding issue

## Still Not Working?

1. **Check the exact error in browser console** - Copy the full error message
2. **Check CloudWatch logs** - Look for detailed error stack trace
3. **Verify bucket name** - Should be exactly `jcdc-ses-contact-list`
4. **Test with tiny file** - Create 1KB text file to isolate size issues
5. **Hard refresh browser** - Clear cache (Ctrl+F5)

## Contact for Help

Share these details for faster troubleshooting:
1. Browser console error message
2. CloudWatch log snippet showing error
3. IAM role policies attached to Lambda
4. S3 bucket name and region
5. File type and size you're trying to upload

