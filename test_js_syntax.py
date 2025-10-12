#!/usr/bin/env python3
"""Extract and validate JavaScript from Lambda function"""

# Read the file
with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the serve_web_ui function
start_marker = 'def serve_web_ui(event):'
end_marker = 'def save_email_config(body, headers):'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print("Could not find function boundaries")
    exit(1)

# Extract the function
func_content = content[start_idx:end_idx]

# Find the HTML content (f-string)
html_start = func_content.find('html_content = f"""')
if html_start == -1:
    html_start = func_content.find("html_content = f'''")

if html_start == -1:
    print("Could not find HTML content")
    exit(1)

# Extract just a portion to check
portion = func_content[html_start:html_start+50000]

# Check for obvious issues
print("Checking for syntax issues...")
print(f"Total length: {len(func_content)} characters")

# Look for line 4324 area in source
lines = func_content.split('\n')
if len(lines) > 500:
    print(f"\nAround line 500 (might correspond to browser line 4324):")
    for i in range(495, min(505, len(lines))):
        print(f"{i}: {lines[i][:100]}")

print("\nChecking completed. Deploy and check browser console for exact error.")

