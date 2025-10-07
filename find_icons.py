#!/usr/bin/env python3
"""
Find {icons...} references
"""

import re

with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    content = f.read()

html_start = content.find('html_content = """')
html_end = content.find('""".format(api_url=api_url)', html_start)
html_template = content[html_start + 18:html_end]

# Find references to {icons
matches = list(re.finditer(r'{icons', html_template))

print(f'Found {len(matches)} icons references:')
for m in matches[:10]:
    line_num = html_template[:m.start()].count('\n') + 1
    context_start = max(0, m.start() - 30)
    context_end = min(len(html_template), m.end() + 50)
    context = html_template[context_start:context_end]
    print(f'\nLine ~{line_num}:')
    print(f'  {context}')
