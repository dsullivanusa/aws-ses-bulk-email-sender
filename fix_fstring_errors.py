#!/usr/bin/env python3
"""
Fix F-String Errors

This script fixes f-strings that don't have placeholders (which cause linting errors)
"""

import re

def fix_fstring_errors():
    """
    Fix f-strings without placeholders in bulk_email_api_lambda.py
    """
    
    print("🔧 Fixing F-String Errors")
    print("=" * 60)
    
    try:
        # Read the file
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("✅ Successfully read bulk_email_api_lambda.py")
        
        # Find and fix f-strings without placeholders
        # Pattern: f"text without {placeholders}"
        pattern = r'f"([^"]*(?:[^{][^"}]*)*)"'
        
        def replace_fstring(match):
            text = match.group(1)
            # Check if the text contains any { } placeholders
            if '{' not in text:
                return f'"{text}"'  # Remove the f prefix
            else:
                return match.group(0)  # Keep as is if it has placeholders
        
        # Apply the fix
        original_content = content
        content = re.sub(pattern, replace_fstring, content)
        
        # Also fix single-quoted f-strings
        pattern_single = r"f'([^']*(?:[^{][^'}]*)*)"
        
        def replace_fstring_single(match):
            text = match.group(1)
            if '{' not in text:
                return f"'{text}'"  # Remove the f prefix
            else:
                return match.group(0)  # Keep as is if it has placeholders
        
        content = re.sub(pattern_single, replace_fstring_single, content)
        
        # Count changes
        changes_made = len(re.findall(r'f"[^"]*"', original_content)) - len(re.findall(r'f"[^"]*"', content))
        changes_made += len(re.findall(r"f'[^']*'", original_content)) - len(re.findall(r"f'[^']*'", content))
        
        if changes_made > 0:
            # Write the fixed file
            with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Fixed {changes_made} f-string errors")
            print("✅ Successfully updated bulk_email_api_lambda.py")
        else:
            print("ℹ️  No f-string errors found to fix")
        
        # Verify the fix by checking for remaining problematic f-strings
        remaining_issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Look for f-strings without placeholders
            if re.search(r'f"[^"]*"', line) and '{' not in line:
                remaining_issues.append((i, line.strip()))
            elif re.search(r"f'[^']*'", line) and '{' not in line:
                remaining_issues.append((i, line.strip()))
        
        if remaining_issues:
            print(f"⚠️  Found {len(remaining_issues)} remaining f-string issues:")
            for line_num, line_content in remaining_issues[:5]:  # Show first 5
                print(f"   Line {line_num}: {line_content}")
        else:
            print("✅ No remaining f-string errors found")
        
        return True
        
    except FileNotFoundError:
        print("❌ bulk_email_api_lambda.py not found")
        return False
    except Exception as e:
        print(f"❌ Error fixing f-strings: {str(e)}")
        return False

if __name__ == "__main__":
    fix_fstring_errors()