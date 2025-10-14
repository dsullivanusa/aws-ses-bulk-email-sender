#!/usr/bin/env python3
"""
Check for encoding issues in bulk_email_api_lambda.py
"""

def check_encoding():
    """Check for non-ASCII characters that might cause issues"""
    try:
        with open('bulk_email_api_lambda.py', 'rb') as f:
            content = f.read()
        
        print(f"File size: {len(content)} bytes")
        
        # Look for non-ASCII bytes
        non_ascii_positions = []
        for i, byte in enumerate(content):
            if byte > 127:
                non_ascii_positions.append((i, byte))
        
        if non_ascii_positions:
            print(f"Found {len(non_ascii_positions)} non-ASCII bytes:")
            for pos, byte in non_ascii_positions[:10]:  # Show first 10
                print(f"  Position {pos}: byte {hex(byte)}")
                
                # Show context
                start = max(0, pos-30)
                end = min(len(content), pos+30)
                context = content[start:end]
                try:
                    context_str = context.decode('utf-8', errors='replace')
                    print(f"    Context: ...{context_str}...")
                except:
                    print(f"    Context (hex): {context.hex()}")
                print()
        else:
            print("No non-ASCII bytes found")
            
        # Try to decode as UTF-8
        try:
            text_content = content.decode('utf-8')
            print("✅ File can be decoded as UTF-8")
        except UnicodeDecodeError as e:
            print(f"❌ UTF-8 decode error: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_encoding()