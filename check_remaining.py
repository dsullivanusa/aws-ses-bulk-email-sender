#!/usr/bin/env python3
"""
Check Remaining Unescaped Variables
"""

import re

with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    content = f.read()

html_start = content.find('html_content = """')
html_end = content.find('""".format(api_url=api_url)', html_start)
html_template = content[html_start + 18:html_end]

# Find ${anything} that is NOT ${{anything}}
matches = list(re.finditer(r'\$\{(?!\{)', html_template))

print(f'Found {len(matches)} remaining unescaped variables:')

for i, m in enumerate(matches[:30]):
    line_num = html_template[:m.start()].count('\n') + 1
    line_start = html_template.rfind('\n', max(0, m.start() - 50), m.start()) + 1
    line_end = html_template.find('\n', m.start(), min(len(html_template), m.start() + 100))
    if line_end == -1:
        line_end = len(html_template)
    context = html_template[line_start:line_end]
    try:
        print(f'\nLine ~{line_num}:')
        print(f'  {context[:100]}')
    except:
        print(f'\nLine ~{line_num}: (unable to print)')

