#!/usr/bin/env python3
"""Convert f-string to .format() in bulk_email_api_lambda.py"""

# Read the file
with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the serve_web_ui function
start_marker = '    html_content = """<!DOCTYPE html>'
end_marker = '</html>"""'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print("Could not find HTML content boundaries")
    exit(1)

# Extract the HTML section
html_section = content[start_idx:end_idx + len(end_marker)]

print(f"Found HTML section: {len(html_section)} characters")
print(f"Start: {start_idx}, End: {end_idx}")

# Count double braces
double_open = html_section.count('{{')
double_close = html_section.count('}}')
print(f"Double braces: {{ count = {double_open}, }} count = {double_close}")

# Replace all {{ with { and }} with }
converted = html_section.replace('{{', '{').replace('}}', '}')

# Now we need to escape {api_url} back to {{api_url}} for .format()
converted = converted.replace('{api_url}', '{{api_url}}')

# Add .format() at the end
converted = converted.replace('</html>"""', '</html>""".format(api_url=api_url)')

print(f"\nConverted HTML section: {len(converted)} characters")

# Replace in original content
new_content = content[:start_idx] + converted + content[end_idx + len(end_marker):]

# Write back
with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("\n✓ Conversion complete!")
print(f"Changed {double_open} {{ and {double_close} }} to single braces")
print("Added .format(api_url=api_url) at end")


