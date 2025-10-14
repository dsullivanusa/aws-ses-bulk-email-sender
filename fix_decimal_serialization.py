#!/usr/bin/env python3
"""
Fix all json.dumps calls to handle Decimal serialization properly
"""

def fix_decimal_serialization():
    """Add default=_json_default to json.dumps calls that might contain Decimal data"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find json.dumps calls that don't have default parameter and might contain DynamoDB data
    import re
    
    # Pattern to find json.dumps calls without default parameter
    pattern = r'json\.dumps\([^)]*\)(?!\s*,\s*default=)'
    
    matches = re.findall(pattern, content)
    
    print(f"Found {len(matches)} json.dumps calls")
    
    # Functions that likely return DynamoDB data and need default parameter
    functions_with_dynamodb_data = [
        'get_campaigns', 'get_contacts', 'filter_contacts', 'search_contacts',
        'get_distinct_values', 'send_campaign', 'get_campaign_status'
    ]
    
    # Check each json.dumps call
    fixed_count = 0
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if 'json.dumps(' in line and 'default=' not in line:
            # Check if this line is in a function that handles DynamoDB data
            function_context = ""
            
            # Look backwards to find the function definition
            for j in range(i, max(0, i-100), -1):
                if lines[j].strip().startswith('def '):
                    function_context = lines[j]
                    break
            
            # Check if this is in a function that handles DynamoDB data
            needs_default = any(func in function_context for func in functions_with_dynamodb_data)
            
            # Also check if the json.dumps contains variables that might have Decimals
            decimal_indicators = ['campaign', 'contact', 'result', 'items', 'response']
            has_decimal_data = any(indicator in line for indicator in decimal_indicators)
            
            if needs_default or has_decimal_data:
                # Add default parameter if it's a simple json.dumps call
                if line.strip().endswith('})'):
                    old_line = line
                    new_line = line.replace('})', '}, default=_json_default)')
                    lines[i] = new_line
                    fixed_count += 1
                    print(f"Fixed line {i+1}: Added default=_json_default")
                    print(f"  Before: {old_line.strip()}")
                    print(f"  After:  {new_line.strip()}")
                    print()
    
    if fixed_count > 0:
        # Write back the fixed content
        with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"✅ Fixed {fixed_count} json.dumps calls")
    else:
        print("No additional json.dumps calls needed fixing")
    
    return fixed_count > 0

if __name__ == "__main__":
    fix_decimal_serialization()