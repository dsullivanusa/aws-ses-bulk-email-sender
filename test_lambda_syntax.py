#!/usr/bin/env python3
"""
Test Lambda Function Syntax
Checks if the Lambda code has syntax errors that would prevent execution
"""

import sys
import py_compile
import tempfile
import os

def test_lambda_syntax(lambda_file):
    """Test if Lambda Python file has syntax errors"""
    
    print("=" * 80)
    print("🔍 Testing Lambda Function Syntax")
    print("=" * 80)
    
    print(f"\n📝 Checking: {lambda_file}")
    
    try:
        # Try to compile the Python file
        with tempfile.NamedTemporaryFile(suffix='.pyc', delete=False) as tmp:
            tmp_name = tmp.name
        
        py_compile.compile(lambda_file, cfile=tmp_name, doraise=True)
        
        print(f"✅ Syntax check PASSED")
        print(f"   No Python syntax errors found")
        
        # Clean up
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        
        return True
        
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax check FAILED")
        print(f"\n{e}")
        
        # Clean up
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        
        return False
    
    except Exception as e:
        print(f"❌ Error during syntax check: {str(e)}")
        return False

def main():
    """Main function"""
    
    # Test email worker Lambda
    worker_file = 'email_worker_lambda.py'
    
    print(f"\nTesting Lambda functions for syntax errors...")
    print(f"This helps diagnose if re-delivery is caused by Lambda failures\n")
    
    if not os.path.exists(worker_file):
        print(f"❌ File not found: {worker_file}")
        return
    
    result = test_lambda_syntax(worker_file)
    
    if result:
        print(f"\n" + "=" * 80)
        print(f"✅ Lambda syntax is valid!")
        print(f"=" * 80)
        print(f"\nIf emails are still being re-sent, the issue is likely:")
        print(f"  1. Lambda throwing runtime errors (check logs)")
        print(f"  2. Lambda timing out (check timeout setting)")
        print(f"  3. SQS visibility timeout (run fix_sqs_redelivery.py)")
        print(f"\n🔍 Check logs:")
        print(f"   python view_lambda_errors.py email-worker-function 1")
    else:
        print(f"\n" + "=" * 80)
        print(f"❌ Lambda has syntax errors!")
        print(f"=" * 80)
        print(f"\nThis WILL cause re-delivery because Lambda fails on startup.")
        print(f"Fix the syntax errors above, then redeploy:")
        print(f"   python update_email_worker.py")

if __name__ == '__main__':
    main()

