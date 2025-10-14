#!/usr/bin/env python3
"""
Test script to check for syntax errors in bulk_email_api_lambda.py
"""

def test_lambda_syntax():
    """Test if the lambda function has syntax errors"""
    try:
        # Try to compile the file
        with open('bulk_email_api_lambda.py', 'r') as f:
            code = f.read()
        
        # Compile the code to check for syntax errors
        compile(code, 'bulk_email_api_lambda.py', 'exec')
        print("✅ No syntax errors found in bulk_email_api_lambda.py")
        
        # Check for common issues
        if 'text' in code and 'text =' not in code and 'def text' not in code:
            print("⚠️  Found references to 'text' variable - checking...")
            
            # Look for undefined text references
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if 'text' in line and not any(x in line for x in ['text =', 'def text', 'import text', '.text', 'text(', '"text"', "'text'"]):
                    print(f"   Line {i}: {line.strip()}")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error found: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")
        return False

if __name__ == "__main__":
    test_lambda_syntax()