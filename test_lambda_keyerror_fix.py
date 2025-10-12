#!/usr/bin/env python3
"""
Test Lambda Function with Proper Event Structure
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def test_contacts_endpoint():
    """Test the /contacts endpoint with proper event structure"""
    print("🧪 Testing /contacts endpoint...")
    
    # Proper API Gateway event structure
    test_event = {
        'httpMethod': 'GET',
        'resource': '/contacts',
        'path': '/contacts',
        'queryStringParameters': {'limit': '5'},
        'pathParameters': None,  # Important: set to None, not missing
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': None,
        'requestContext': {
            'apiId': 'test-api',
            'stage': 'prod',
            'identity': {
                'sourceIp': '127.0.0.1',
                'userAgent': 'test-client'
            }
        }
    }
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Status Code: {status_code}")
        
        if status_code == 200:
            print("✅ SUCCESS! KeyError fixed")
            body = json.loads(payload.get('body', '{}'))
            contacts = body.get('contacts', [])
            print(f"   Contacts returned: {len(contacts)}")
            
        elif status_code == 500:
            print("❌ 500 Error")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"   Error: {error_message}")
            
            if 'KeyError' in error_message:
                print("🔴 Still getting KeyError - check the error details")
            elif '403' in error_message or 'AccessDenied' in error_message:
                print("🔴 403 Permission error - run fix_403_permissions.py")
                
        else:
            print(f"⚠️  Unexpected status: {status_code}")
            print(f"   Response: {payload.get('body')}")
            
    except Exception as e:
        print(f"❌ Lambda invocation failed: {str(e)}")

def test_campaign_endpoint():
    """Test the /campaign/{campaign_id} endpoint that was causing KeyError"""
    print("\n🧪 Testing /campaign/{campaign_id} endpoint...")
    
    test_event = {
        'httpMethod': 'GET',
        'resource': '/campaign/{campaign_id}',
        'path': '/campaign/test-campaign-123',
        'queryStringParameters': None,
        'pathParameters': {
            'campaign_id': 'test-campaign-123'
        },
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': None,
        'requestContext': {
            'apiId': 'test-api',
            'stage': 'prod'
        }
    }
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Status Code: {status_code}")
        
        if status_code == 404:
            print("✅ SUCCESS! KeyError fixed (404 expected for non-existent campaign)")
            
        elif status_code == 200:
            print("✅ SUCCESS! Campaign found")
            
        elif status_code == 500:
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"❌ 500 Error: {error_message}")
            
            if 'KeyError' in error_message:
                print("🔴 Still getting KeyError on pathParameters")
            else:
                print("✅ KeyError fixed, but other error occurred")
                
        else:
            print(f"⚠️  Status: {status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

def test_missing_path_parameters():
    """Test with missing pathParameters to ensure it's handled gracefully"""
    print("\n🧪 Testing missing pathParameters handling...")
    
    test_event = {
        'httpMethod': 'GET',
        'resource': '/campaign/{campaign_id}',
        'path': '/campaign/test-123',
        'queryStringParameters': None,
        # pathParameters is missing entirely (this was causing the KeyError)
        'headers': {},
        'body': None,
        'requestContext': {
            'apiId': 'test-api'
        }
    }
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Status Code: {status_code}")
        
        if status_code == 400:
            print("✅ SUCCESS! Missing pathParameters handled gracefully")
            body = json.loads(payload.get('body', '{}'))
            print(f"   Error message: {body.get('error')}")
            
        elif status_code == 500:
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            if 'KeyError' in error_message:
                print("❌ Still getting KeyError - fix didn't work")
            else:
                print("✅ KeyError fixed, different error occurred")
            print(f"   Error: {error_message}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

def main():
    """Run all tests"""
    print("🔧 Testing Lambda KeyError Fixes")
    print("="*60)
    
    # Test basic endpoint
    test_contacts_endpoint()
    
    # Test the endpoint that was causing KeyError
    test_campaign_endpoint()
    
    # Test missing pathParameters handling
    test_missing_path_parameters()
    
    print("\n" + "="*60)
    print("✅ Testing complete")
    print("\nIf you're still getting KeyErrors:")
    print("1. Check CloudWatch logs for the exact line number")
    print("2. Look for other event['...'] accesses without .get()")
    print("3. Run: python diagnose_403_errors.py for permission issues")

if __name__ == '__main__':
    main()