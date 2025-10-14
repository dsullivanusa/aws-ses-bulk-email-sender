"""
Local helper to inspect and normalize Quill/HTML produced content.
Run from the repository root:
    python scripts\inspect_html.py [input_file]
If no input_file is provided the script uses a built-in sample.

It prints counts of <p> tags, empty paragraphs, consecutive <br> runs, and shows cleaned output.
"""
import sys
import os
import re

# Ensure repository root is on sys.path so we can import project modules when run from scripts/
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    # Try the simple import first (works when dependencies like boto3 are available)
    from email_worker_lambda import clean_quill_html_for_email, personalize_content
except Exception:
    # Fallback: read the file and extract the two function definitions so we don't execute
    # top-level AWS/boto3 initializers in the module when running locally without AWS deps.
    src_path = os.path.join(repo_root, 'email_worker_lambda.py')
    with open(src_path, 'r', encoding='utf-8') as f:
        src = f.read()

    import re as _re

    def _extract_func(name):
        pattern = rf"(def\s+{name}\s*\([^\)]*\):[\s\S]*?)(?=\ndef\s+|\Z)"
        m = _re.search(pattern, src, flags=_re.MULTILINE)
        return m.group(1) if m else None

    func_a = _extract_func('clean_quill_html_for_email')
    func_b = _extract_func('personalize_content')

    if not func_a or not func_b:
        raise ImportError('Could not extract required functions from email_worker_lambda.py')

    # Execute the extracted functions in a minimal namespace
    _ns = {}
    exec(func_a, _ns)
    exec(func_b, _ns)

    clean_quill_html_for_email = _ns['clean_quill_html_for_email']
    personalize_content = _ns['personalize_content']


def analyze_html(html):
    p_tags = re.findall(r'<p\b', html or '', flags=re.IGNORECASE)
    empty_p = re.findall(r'<p[^>]*>\s*(?:&nbsp;|<br\s*/?>|\s)*\s*</p>', html or '', flags=re.IGNORECASE)
    br_runs = re.findall(r'(<br\s*/?>\s*){2,}', html or '', flags=re.IGNORECASE)
    return {
        'p_count': len(p_tags),
        'empty_p_count': len(empty_p),
        'consecutive_br_runs': len(br_runs),
    }


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
    else:
        raw = '''<div class="ql-editor ql-snow">\n  <p>First paragraph</p>\n  <p><br></p>\n  <p>&nbsp;</p>\n  <p>Second paragraph</p>\n  <p>  </p>\n  <p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA">\n  </p>\n  <p>Third paragraph</p>\n  <p><br><br></p>\n</div>'''

    print('\n=== RAW INPUT PREVIEW ===')
    print(raw[:1000])

    before = analyze_html(raw)
    print('\n=== DIAGNOSTICS BEFORE CLEANING ===')
    for k, v in before.items():
        print(f'{k}: {v}')

    cleaned = clean_quill_html_for_email(raw)
    after = analyze_html(cleaned)

    print('\n=== CLEANED PREVIEW (first 800 chars) ===')
    print(cleaned[:800])

    print('\n=== DIAGNOSTICS AFTER CLEANING ===')
    for k, v in after.items():
        print(f'{k}: {v}')

    # Also show personalize_content pass-through (no contact data here)
    personalized = personalize_content(cleaned, {'first_name': 'Alice', 'last_name': 'Doe', 'email': 'a@example.com'})
    print('\n=== PERSONALIZED PREVIEW (first 800 chars) ===')
    print(personalized[:800])
