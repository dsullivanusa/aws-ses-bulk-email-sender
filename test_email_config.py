#!/usr/bin/env python3
"""
Test script for email configuration functionality
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal

def test_dynamodb_connection():
    """Test DynamoDB connection and table access"""
    print("Testing DynamoDB connection...")
    
    try:
        # Test with boto3.resource (high-level API)
        dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
        email_config_table = dynamodb.Table('EmailConfig')
        
        # Test table access
        print(f"✓ Connected to DynamoDB")
        print(f"✓ Table 'EmailConfig' accessible")
        
        # Test saving configuration
        test_config = {
            'config_id': 'test',
            'email_service': 'ses',
            'from_email': 'test@example.com',
            'emails_per_minute': 60,
            'aws_region': 'us-gov-west-1',
            'aws_access_key': 'test_key',
            'aws_secret_key': 'test_secret',
            'updated_at': datetime.now().isoformat()
        }
        
        # Try to save config
        email_config_table.put_item(Item=test_config)
        print("✓ Successfully saved test configuration")
        
        # Try to read config back
        response = email_config_table.get_item(Key={'config_id': 'test'})
        if 'Item' in response:
            print("✓ Successfully retrieved test configuration")
            print(f"  Retrieved data: {response['Item']}")
        else:
            print("✗ Could not retrieve test configuration")
        
        # Clean up test data
        email_config_table.delete_item(Key={'config_id': 'test'})
        print("✓ Cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"✗ DynamoDB test failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False

def test_secrets_manager():
    """Test AWS Secrets Manager integration"""
    print("\nTesting AWS Secrets Manager integration...")
    
    try:
        # Test with a dummy secret (this will fail but we can see if the function works)
        from bulk_email_api_lambda import get_aws_credentials_from_secrets_manager
        
        try:
            # This should fail since we don't have a real secret
            credentials = get_aws_credentials_from_secrets_manager('test-secret')
            print("✓ Secrets Manager integration working (unexpected success)")
        except Exception as e:
            if "ResourceNotFoundException" in str(e) or "InvalidRequestException" in str(e):
                print("✓ Secrets Manager integration working (expected error for test secret)")
            else:
                print(f"✗ Unexpected error: {e}")
                return False
                
        return True
        
    except Exception as e:
        print(f"✗ Secrets Manager test failed: {e}")
        return False

def test_config_functions():
    """Test the configuration functions"""
    print("\nTesting configuration functions...")
    
    try:
        # Import the functions from the lambda
        import sys
        sys.path.append('.')
        
        # Test data for SMTP (no secrets needed)
        test_body = {
            'email_service': 'smtp',
            'from_email': 'sender@test.com',
            'emails_per_minute': 30,
            'smtp_server': '192.168.1.100',
            'smtp_port': 25
        }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        }
        
        # Test save function
        from bulk_email_api_lambda import save_email_config
        result = save_email_config(test_body, headers)
        print(f"✓ Save config result: {result}")
        
        # Test get function
        from bulk_email_api_lambda import get_email_config
        result = get_email_config(headers)
        print(f"✓ Get config result: {result}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration function test failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=== Email Configuration Test Suite ===\n")
    
    # Test DynamoDB connection
    db_success = test_dynamodb_connection()
    
    # Test Secrets Manager integration
    secrets_success = test_secrets_manager()
    
    # Test configuration functions
    func_success = test_config_functions()
    
    print(f"\n=== Test Results ===")
    print(f"DynamoDB Connection: {'PASS' if db_success else 'FAIL'}")
    print(f"Secrets Manager Integration: {'PASS' if secrets_success else 'FAIL'}")
    print(f"Configuration Functions: {'PASS' if func_success else 'FAIL'}")
    
    if db_success and secrets_success and func_success:
        print("\n🎉 All tests passed! Email configuration should work correctly.")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
