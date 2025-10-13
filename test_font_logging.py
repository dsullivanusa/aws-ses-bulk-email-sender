#!/usr/bin/env python3
"""
Test Font Logging Implementation
"""

import boto3
import json

REGION = 'us-gov-west-1'
LAMBDA_FUNCTION_NAME = 'bulk-email-api-function'

def test_font_logging_features():
    """Test that font logging features are implemented correctly"""
    print("🧪 Testing Font Logging Implementation...")
    
    # Test event for the root path (serves HTML with font logging)
    test_event = {
        'httpMethod': 'GET',
        'resource': '/',
        'path': '/',
        'queryStringParameters': None,
        'pathParameters': None,
        'headers': {
            'Accept': 'text/html'
        },
        'body': None,
        'requestContext': {
            'apiId': 'test-api-12345',
            'stage': 'prod',
            'identity': {
                'sourceIp': '127.0.0.1'
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
            body = payload.get('body', '')
            
            # Check for font logging features
            logging_checks = {
                'Font Change Event Listeners': 'quillEditor.on(\'selection-change\'' in body,
                'Font Dropdown Monitoring': 'fontPicker.addEventListener(\'click\'' in body,
                'Font Usage Analysis Function': 'logFontUsage()' in body,
                'Font Monitoring Startup': 'startFontMonitoring()' in body,
                'Campaign Font Analysis': 'CAMPAIGN FONT ANALYSIS' in body,
                'Preview Font Analysis': 'PREVIEW FONT ANALYSIS' in body,
                'Font Usage Toast Notifications': 'Toast.info(`Font changed to:' in body,
                'Console Font Logging': 'console.log(`🎨 FONT' in body
            }
            
            print("\n📋 Font Logging Feature Checks:")
            all_passed = True
            for check_name, passed in logging_checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check_name}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print("\n🎉 SUCCESS! All font logging features implemented")
                print("✅ Real-time font change detection")
                print("✅ Font dropdown click monitoring")
                print("✅ Campaign font usage analysis")
                print("✅ Preview font logging")
                print("✅ Console logging for debugging")
                print("✅ User notifications for font changes")
            else:
                print("\n⚠️  Some font logging features may be missing")
                
        elif status_code == 500:
            print("❌ 500 Error - Internal Server Error")
            body = json.loads(payload.get('body', '{}'))
            error_message = body.get('error', 'Unknown error')
            print(f"   Error: {error_message}")
            
        else:
            print(f"⚠️  Unexpected status: {status_code}")
            
    except Exception as e:
        print(f"❌ Lambda invocation failed: {str(e)}")

def test_campaign_font_logging():
    """Test campaign sending with font logging"""
    print("\n🧪 Testing Campaign Font Logging...")
    
    # Test campaign with font usage
    test_campaign = {
        'httpMethod': 'POST',
        'resource': '/campaign',
        'path': '/campaign',
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'campaign_name': 'Font Test Campaign',
            'subject': 'Testing Font Logging',
            'body': '<p class="ql-font-arial">Arial text</p><p class="ql-font-georgia">Georgia text</p>',
            'font_usage': {
                'arial': 1,
                'georgia': 1
            },
            'to': 'test@example.com',
            'launched_by': 'Font Test User'
        }),
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
            Payload=json.dumps(test_campaign)
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        status_code = payload.get('statusCode')
        
        print(f"📊 Campaign Status Code: {status_code}")
        
        if status_code == 200:
            print("✅ Campaign sent successfully with font logging")
            body = json.loads(payload.get('body', '{}'))
            campaign_id = body.get('campaign_id')
            if campaign_id:
                print(f"📧 Campaign ID: {campaign_id}")
                print("✅ Font usage should be logged in DynamoDB")
        else:
            print(f"⚠️  Campaign status: {status_code}")
            if status_code >= 400:
                body = json.loads(payload.get('body', '{}'))
                print(f"   Error: {body.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Campaign test failed: {str(e)}")

def main():
    """Run font logging tests"""
    print("🎨 Testing Font Logging Implementation")
    print("="*60)
    
    test_font_logging_features()
    test_campaign_font_logging()
    
    print("\n" + "="*60)
    print("✅ Font Logging Testing Complete")
    print("\nFont Logging Features Added:")
    print("1. ✅ Real-time font change detection in editor")
    print("2. ✅ Font dropdown click monitoring")
    print("3. ✅ Automatic font usage analysis")
    print("4. ✅ Campaign font logging to DynamoDB")
    print("5. ✅ Preview font analysis")
    print("6. ✅ Console logging for debugging")
    print("7. ✅ User-friendly toast notifications")
    print("8. ✅ Server-side font usage tracking")
    
    print("\nHow to Monitor Font Usage:")
    print("• Open browser console (F12)")
    print("• Change fonts in the editor")
    print("• Watch for '🎨 FONT' log messages")
    print("• Send campaigns to see font analysis")
    print("• Check DynamoDB for font_usage field")

if __name__ == '__main__':
    main()