#!/usr/bin/env python3
"""
Find {type} occurrences
"""

with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

matches = []
for i, line in enumerate(lines, 1):
    if '{type}' in line and '${{type}}' not in line and '{{type}}' not in line:
        matches.append((i, line.rstrip()))

print(f'Found {len(matches)} {{type}} occurrences (not escaped):')
for num, line in matches[:10]:
    print(f'Line {num}: {line[:150]}')
