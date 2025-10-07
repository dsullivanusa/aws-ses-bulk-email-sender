#!/usr/bin/env python3
"""
Find Single Braces
Look for {anything} that is not {{anything}} and not ${anything}
"""

import re

with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    content = f.read()

html_start = content.find('html_content = """')
html_end = content.find('""".format(api_url=api_url)', html_start)
html_template = content[html_start + 18:html_end]

# Find {variable} patterns that are not {{variable}} and not ${variable}
# Pattern: {word} but not {{word}} or ${word}
matches = []
i = 0
while i < len(html_template):
    if html_template[i] == '{':
        # Check if it's {{ or ${
        if i > 0 and html_template[i-1] in ['{', '$']:
            i += 1
            continue
        # Found a single {, find the closing }
        end = html_template.find('}', i)
        if end != -1:
            # Check if it's followed by }
            if end < len(html_template) - 1 and html_template[end+1] == '}':
                i = end + 2
                continue
            # Found a single {variable}
            var_content = html_template[i+1:end]
            if var_content:  # Not empty
                line_num = html_template[:i].count('\n') + 1
                matches.append((line_num, i, var_content))
                print(f'Line ~{line_num}: {{{var_content}}}')
                # Show context
                line_start = html_template.rfind('\n', max(0, i - 50), i) + 1
                line_end = html_template.find('\n', i, min(len(html_template), i + 100))
                if line_end == -1:
                    line_end = min(len(html_template), i + 100)
                context = html_template[line_start:line_end]
                try:
                    print(f'  Context: ...{context[max(0, i-line_start-20):min(len(context), i-line_start+50)]}...')
                except:
                    pass
                print()
            i = end + 1
        else:
            i += 1
    else:
        i += 1

print(f'\nTotal single-brace patterns found: {len(matches)}')
