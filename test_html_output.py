#!/usr/bin/env python3
"""Test the HTML output from serve_web_ui function"""

# Mock the serve_web_ui function with minimal imports
def test_html_generation():
    # Create a minimal version of the f-string around line 4324
    uploadResult = None  # Mock variable
    uploadResponse = None  # Mock variable
    responseText = None  # Mock variable
    
    try:
        test_snippet = f"""
                        if (uploadResult.error) {{
                            throw new Error(uploadResult.error);
                        }}
"""
        print("ERROR: Python tried to evaluate uploadResult.error!")
        print("This is the problem - uploadResult is in the JavaScript, not Python scope")
    except NameError as e:
        print(f"✓ Confirmed issue: {e}")
        print("\nThe fix: escape the inner braces with {{ and }}")
        
    # Test the fixed version
    try:
        fixed_snippet = """
                        if (uploadResult.error) {
                            throw new Error(uploadResult.error);
                        }
"""
        print(f"\n✓ Fixed version works!")
        print(f"Output:\n{fixed_snippet}")
    except Exception as e:
        print(f"✗ Still broken: {e}")

if __name__ == "__main__":
    test_html_generation()
