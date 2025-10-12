#!/usr/bin/env python3
"""Test if serve_web_ui can generate HTML"""
import sys

# Try to render a small section of the problematic area
def test_fstring():
    # Simulate what's around line 4323-4325
    # In the actual code, this is inside an f-string
    try:
        # This simulates the ACTUAL Python code structure
        snippet = f"""
        try {{
            uploadResult = JSON.parse(responseText);
        }} catch (parseError) {{
            console.error('Failed to parse');
        }}
        
        if (uploadResult.error) {{
            throw new Error(uploadResult.error);
        }}
        """
        print("SUCCESS! The f-string renders correctly")
        print("Output preview:")
        print(snippet[:200])
        return True
    except (NameError, KeyError) as e:
        print(f"FAILED: {e}")
        print("Python is trying to evaluate JavaScript variables")
        return False

if __name__ == "__main__":
    success = test_fstring()
    sys.exit(0 if success else 1)

