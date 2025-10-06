#!/usr/bin/env python3
"""
Test script for Adaptive Rate Control functionality
Tests attachment detection, throttle detection, and rate adjustment logic
"""

import sys
import os
import time
import json
from unittest.mock import Mock, patch, MagicMock

# Add the current directory to the path so we can import the email worker
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_attachment_delay_calculation():
    """Test attachment size-based delay calculation"""
    print("🧪 Testing Attachment Delay Calculation...")
    
    # Import the rate control class
    from email_worker_lambda import AdaptiveRateControl
    
    rate_control = AdaptiveRateControl()
    
    # Test cases
    test_cases = [
        {
            "name": "No attachments",
            "attachments": [],
            "expected_factor": 1.0
        },
        {
            "name": "Small attachment (500KB)",
            "attachments": [{"s3_key": "test1.pdf", "filename": "test1.pdf"}],
            "mock_size": 500 * 1024,  # 500KB
            "expected_factor": 1.5
        },
        {
            "name": "Medium attachment (3MB)",
            "attachments": [{"s3_key": "test2.pdf", "filename": "test2.pdf"}],
            "mock_size": 3 * 1024 * 1024,  # 3MB
            "expected_factor": 2.0
        },
        {
            "name": "Large attachment (8MB)",
            "attachments": [{"s3_key": "test3.pdf", "filename": "test3.pdf"}],
            "mock_size": 8 * 1024 * 1024,  # 8MB
            "expected_factor": 3.0
        },
        {
            "name": "Multiple attachments (total 6MB)",
            "attachments": [
                {"s3_key": "test4.pdf", "filename": "test4.pdf"},
                {"s3_key": "test5.pdf", "filename": "test5.pdf"}
            ],
            "mock_size": 3 * 1024 * 1024,  # 3MB each = 6MB total
            "expected_factor": 3.0
        }
    ]
    
    for test_case in test_cases:
        print(f"  Testing: {test_case['name']}")
        
        # Mock S3 head_object response
        mock_response = {
            'ContentLength': test_case.get('mock_size', 0)
        }
        
        with patch('email_worker_lambda.s3_client.head_object', return_value=mock_response):
            delay = rate_control.calculate_attachment_delay(test_case['attachments'])
            expected_delay = rate_control.base_delay * test_case['expected_factor']
            
            print(f"    Expected delay: {expected_delay:.3f}s")
            print(f"    Actual delay: {delay:.3f}s")
            
            if abs(delay - expected_delay) < 0.001:
                print(f"    ✅ PASS")
            else:
                print(f"    ❌ FAIL - Expected {expected_delay:.3f}, got {delay:.3f}")
    
    print()

def test_throttle_detection():
    """Test throttle exception detection"""
    print("🧪 Testing Throttle Detection...")
    
    from email_worker_lambda import AdaptiveRateControl
    from botocore.exceptions import ClientError
    
    rate_control = AdaptiveRateControl()
    
    # Test cases for throttle detection
    test_cases = [
        {
            "name": "AWS SES Throttling error",
            "exception": ClientError(
                error_response={'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
                operation_name='SendEmail'
            ),
            "should_detect": True
        },
        {
            "name": "AWS SES ServiceUnavailable error",
            "exception": ClientError(
                error_response={'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
                operation_name='SendEmail'
            ),
            "should_detect": True
        },
        {
            "name": "String with throttle message",
            "exception": Exception("Rate limit exceeded for this account"),
            "should_detect": True
        },
        {
            "name": "String with rate limit message",
            "exception": Exception("Too many requests, please slow down"),
            "should_detect": True
        },
        {
            "name": "Regular exception",
            "exception": Exception("Invalid email address"),
            "should_detect": False
        },
        {
            "name": "Network timeout",
            "exception": Exception("Connection timeout"),
            "should_detect": False
        }
    ]
    
    for test_case in test_cases:
        print(f"  Testing: {test_case['name']}")
        
        detected = rate_control.detect_throttle_exception(test_case['exception'])
        expected = test_case['should_detect']
        
        print(f"    Expected: {expected}, Got: {detected}")
        
        if detected == expected:
            print(f"    ✅ PASS")
        else:
            print(f"    ❌ FAIL - Expected {expected}, got {detected}")
    
    print()

def test_throttle_handling():
    """Test throttle handling and recovery"""
    print("🧪 Testing Throttle Handling and Recovery...")
    
    from email_worker_lambda import AdaptiveRateControl
    from botocore.exceptions import ClientError
    
    rate_control = AdaptiveRateControl()
    
    # Test initial state
    initial_delay = rate_control.current_delay
    print(f"  Initial delay: {initial_delay:.3f}s")
    
    # Simulate throttle detection
    throttle_exception = ClientError(
        error_response={'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
        operation_name='SendEmail'
    )
    
    # Handle throttle
    new_delay = rate_control.handle_throttle_detected()
    print(f"  After first throttle: {new_delay:.3f}s")
    
    # Should be 2x the initial delay
    expected_delay = initial_delay * 2.0
    if abs(new_delay - expected_delay) < 0.001:
        print(f"    ✅ PASS - Correct backoff")
    else:
        print(f"    ❌ FAIL - Expected {expected_delay:.3f}, got {new_delay:.3f}")
    
    # Simulate multiple throttles
    for i in range(3):
        rate_control.handle_throttle_detected()
    
    max_throttle_delay = rate_control.current_delay
    print(f"  After multiple throttles: {max_throttle_delay:.3f}s")
    
    # Test recovery (mock time passage)
    with patch('time.time', return_value=time.time() + 70):  # 70 seconds later
        recovered_delay = rate_control.recover_from_throttle()
        print(f"  After recovery: {recovered_delay:.3f}s")
        
        if recovered_delay < max_throttle_delay:
            print(f"    ✅ PASS - Recovery working")
        else:
            print(f"    ❌ FAIL - No recovery detected")
    
    print()

def test_integration_scenario():
    """Test a complete integration scenario"""
    print("🧪 Testing Integration Scenario...")
    
    from email_worker_lambda import AdaptiveRateControl
    
    rate_control = AdaptiveRateControl()
    
    # Scenario: Email with medium attachment, then throttle occurs
    print("  Scenario: Medium attachment + throttle")
    
    # Mock attachment with 3MB size
    attachments = [{"s3_key": "medium_file.pdf", "filename": "medium_file.pdf"}]
    mock_response = {'ContentLength': 3 * 1024 * 1024}
    
    with patch('email_worker_lambda.s3_client.head_object', return_value=mock_response):
        # Get delay for medium attachment
        delay1 = rate_control.get_delay_for_email(attachments)
        print(f"    Delay for medium attachment: {delay1:.3f}s")
        
        # Simulate throttle
        throttle_exception = Exception("Rate limit exceeded")
        delay2 = rate_control.get_delay_for_email(attachments, throttle_exception)
        print(f"    Delay after throttle: {delay2:.3f}s")
        
        # Should be higher due to throttle
        if delay2 > delay1:
            print(f"    ✅ PASS - Throttle increased delay")
        else:
            print(f"    ❌ FAIL - Throttle didn't increase delay")
    
    print()

def test_performance_impact():
    """Test performance impact of rate control"""
    print("🧪 Testing Performance Impact...")
    
    from email_worker_lambda import AdaptiveRateControl
    
    rate_control = AdaptiveRateControl()
    
    # Test different scenarios and measure time
    scenarios = [
        {"name": "No attachments", "attachments": []},
        {"name": "Small attachment", "attachments": [{"s3_key": "small.pdf", "filename": "small.pdf"}]},
        {"name": "Large attachment", "attachments": [{"s3_key": "large.pdf", "filename": "large.pdf"}]}
    ]
    
    for scenario in scenarios:
        print(f"  Testing: {scenario['name']}")
        
        # Mock S3 response
        if "small" in scenario['name']:
            mock_size = 500 * 1024  # 500KB
        elif "large" in scenario['name']:
            mock_size = 8 * 1024 * 1024  # 8MB
        else:
            mock_size = 0
        
        mock_response = {'ContentLength': mock_size}
        
        with patch('email_worker_lambda.s3_client.head_object', return_value=mock_response):
            start_time = time.time()
            delay = rate_control.get_delay_for_email(scenario['attachments'])
            end_time = time.time()
            
            calculation_time = (end_time - start_time) * 1000  # Convert to milliseconds
            print(f"    Calculation time: {calculation_time:.2f}ms")
            print(f"    Delay: {delay:.3f}s")
            
            if calculation_time < 100:  # Should be fast
                print(f"    ✅ PASS - Fast calculation")
            else:
                print(f"    ❌ FAIL - Slow calculation")
    
    print()

def main():
    """Run all tests"""
    print("🚀 Adaptive Rate Control Test Suite")
    print("=" * 50)
    
    try:
        test_attachment_delay_calculation()
        test_throttle_detection()
        test_throttle_handling()
        test_integration_scenario()
        test_performance_impact()
        
        print("🎉 All tests completed!")
        print("\nTo deploy the updated email worker:")
        print("  python deploy_email_worker.py")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure email_worker_lambda.py is in the same directory")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
