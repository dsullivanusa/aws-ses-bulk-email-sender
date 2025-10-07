#!/usr/bin/env python3
"""
Final Test
"""

with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
    content = f.read()

html_start = content.find('html_content = """')
html_end = content.find('""".format(api_url=api_url)', html_start)
html_template = content[html_start + 18:html_end]

try:
    test_url = 'https://jcdcmail.cisa.dhs.gov'
    result = html_template.format(api_url=test_url)
    print('SUCCESS! HTML formatting works!')
    print(f'Result length: {len(result)} characters')
    
    # Check if API_URL is properly defined
    check_string = f"const API_URL = '{test_url}';"
    if check_string in result:
        print(f'API_URL is properly defined: {test_url}')
    else:
        print('API_URL is not properly defined')
    
    # Save the output
    with open('lambda_html_output.html', 'w', encoding='utf-8') as f:
        f.write(result)
    print('Saved output to: lambda_html_output.html')
    
except KeyError as e:
    print(f'KeyError: Missing key {e}')
    print('\nSearching for this key in the template...')
    key_name = str(e).strip("'")
    # Find occurrences
    import re
    pattern = f'{{{key_name}}}'
    matches = [(m.start(), html_template[max(0, m.start()-30):min(len(html_template), m.end()+30)]) for m in re.finditer(re.escape(pattern), html_template)]
    print(f'Found {len(matches)} occurrences of {{{key_name}}}:')
    for pos, context in matches[:5]:
        line_num = html_template[:pos].count('\n') + 1
        print(f'  Line ~{line_num}: ...{context}...')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

