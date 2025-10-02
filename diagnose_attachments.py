#!/usr/bin/env python3
"""
Diagnose Attachment Issues
Checks if email worker is configured correctly for attachments
"""

import boto3
import json

REGION = 'us-gov-west-1'
WORKER_FUNCTION_NAME = 'email-worker-function'
BUCKET_NAME = 'jcdc-ses-contact-list'
CAMPAIGN_TABLE = 'EmailCampaigns'

def diagnose_attachments():
    """Run diagnostics on attachment configuration"""
    
    lambda_client = boto3.client('lambda', region_name=REGION)
    iam_client = boto3.client('iam')
    s3_client = boto3.client('s3', region_name=REGION)
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    
    print("="*70)
    print("ATTACHMENT DIAGNOSTICS")
    print("="*70)
    print()
    
    issues_found = []
    
    # Check 1: Email Worker Lambda exists
    print("1️⃣  Checking Email Worker Lambda...")
    try:
        function_config = lambda_client.get_function(FunctionName=WORKER_FUNCTION_NAME)
        print(f"   ✓ Lambda function '{WORKER_FUNCTION_NAME}' exists")
        
        # Check last modified
        last_modified = function_config['Configuration']['LastModified']
        print(f"   Last Updated: {last_modified}")
        
        # Check if it has S3 in environment or code
        runtime = function_config['Configuration']['Runtime']
        print(f"   Runtime: {runtime}")
        
        role_arn = function_config['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        print(f"   Role: {role_name}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"   ❌ Lambda function '{WORKER_FUNCTION_NAME}' NOT FOUND")
        issues_found.append("Email worker Lambda not found")
        return
    
    # Check 2: Lambda has S3 permissions
    print("\n2️⃣  Checking Lambda S3 Permissions...")
    try:
        # Check attached policies
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        print(f"   Attached policies:")
        for policy in attached_policies['AttachedPolicies']:
            print(f"     • {policy['PolicyName']}")
            if 'S3' in policy['PolicyName']:
                print(f"       ✓ S3 policy found!")
        
        # Check inline policies
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        print(f"   Inline policies:")
        has_s3_inline = False
        for policy_name in inline_policies['PolicyNames']:
            print(f"     • {policy_name}")
            if 'S3' in policy_name or 'Attachment' in policy_name:
                has_s3_inline = True
                # Get policy details
                policy_doc = iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                policy_json = policy_doc['PolicyDocument']
                print(f"       ✓ S3 attachment policy found!")
                
                # Check if it has the right bucket
                policy_str = json.dumps(policy_json)
                if BUCKET_NAME in policy_str:
                    print(f"       ✓ Policy includes bucket: {BUCKET_NAME}")
                else:
                    print(f"       ⚠️  Policy doesn't mention bucket: {BUCKET_NAME}")
        
        if not has_s3_inline and not any('S3' in p['PolicyName'] for p in attached_policies['AttachedPolicies']):
            print(f"   ⚠️  WARNING: No S3 permissions found!")
            issues_found.append("Lambda role missing S3 permissions")
        else:
            print(f"   ✓ Lambda has S3 permissions")
            
    except Exception as e:
        print(f"   ⚠️  Could not check permissions: {str(e)}")
    
    # Check 3: S3 Bucket accessible
    print(f"\n3️⃣  Checking S3 Bucket: {BUCKET_NAME}...")
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"   ✓ Bucket exists and is accessible")
        
        # Check if campaign-attachments folder has files
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix='campaign-attachments/',
            MaxKeys=10
        )
        
        file_count = response.get('KeyCount', 0)
        print(f"   Files in campaign-attachments/: {file_count}")
        
        if file_count > 0:
            print(f"   Recent attachments:")
            for obj in response.get('Contents', [])[:5]:
                size_kb = obj['Size'] / 1024
                print(f"     • {obj['Key']} ({size_kb:.1f} KB) - {obj['LastModified']}")
        else:
            print(f"   ⚠️  No attachments found in S3")
            
    except Exception as e:
        print(f"   ❌ Bucket error: {str(e)}")
        issues_found.append(f"S3 bucket issue: {str(e)}")
    
    # Check 4: Recent campaigns with attachments
    print(f"\n4️⃣  Checking Recent Campaigns...")
    try:
        campaigns_table = dynamodb.Table(CAMPAIGN_TABLE)
        response = campaigns_table.scan(Limit=10)
        
        campaigns_with_attachments = [c for c in response['Items'] if 'attachments' in c and c['attachments']]
        
        print(f"   Total recent campaigns scanned: {len(response['Items'])}")
        print(f"   Campaigns with attachments: {len(campaigns_with_attachments)}")
        
        if campaigns_with_attachments:
            latest = campaigns_with_attachments[0]
            print(f"\n   Latest campaign with attachments:")
            print(f"     Campaign ID: {latest.get('campaign_id')}")
            print(f"     Name: {latest.get('campaign_name')}")
            print(f"     Attachments: {len(latest.get('attachments', []))}")
            for idx, att in enumerate(latest.get('attachments', []), 1):
                print(f"       {idx}. {att.get('filename')} - S3 key: {att.get('s3_key')}")
        else:
            print(f"   ⚠️  No campaigns with attachments found in DynamoDB")
            print(f"   This could mean:")
            print(f"     • Attachment metadata not saved to campaign")
            print(f"     • Campaign was created before attachment feature added")
            
    except Exception as e:
        print(f"   ⚠️  Could not check campaigns: {str(e)}")
    
    # Summary
    print("\n" + "="*70)
    if issues_found:
        print("❌ ISSUES FOUND:")
        print("="*70)
        for idx, issue in enumerate(issues_found, 1):
            print(f"{idx}. {issue}")
        
        print("\n🔧 RECOMMENDED FIXES:")
        if "Email worker Lambda not found" in str(issues_found):
            print("  → Run: python deploy_email_worker.py")
        if "S3 permissions" in str(issues_found):
            print("  → Run: python update_email_worker.py")
        if "S3 bucket" in str(issues_found):
            print("  → Verify bucket exists: aws s3 ls s3://jcdc-ses-contact-list")
        
    else:
        print("✅ ALL CHECKS PASSED")
        print("="*70)
        print("\nConfiguration looks good!")
        print("\nIf attachments still not arriving, check:")
        print("  1. CloudWatch logs for email-worker-function")
        print("  2. Look for 'Downloading attachment' messages")
        print("  3. Verify email didn't go to spam folder")
        print("  4. Send test campaign with attachment and monitor logs")
    
    print()

if __name__ == '__main__':
    diagnose_attachments()

