"""Unit tests for lib.email_utils.

Uses pytest-style tests.
"""
from lib.email_utils import clean_quill_html_for_email, extract_image_srcs


def test_clean_quill_basic():
    html = '<div class="ql-editor"><p>Hi</p><p> </p><p>&nbsp;</p><p>Bye</p><br><br></div>'
    cleaned = clean_quill_html_for_email(html)
    assert '<p>Hi</p>' in cleaned
    assert '<p> </p>' not in cleaned
    assert '<p>&nbsp;</p>' not in cleaned
    assert '<br><br>' not in cleaned


def test_extract_image_srcs():
    html = '<p>Image: <img src="data:image/png;base64,AAAA"/></p><p>Web: <img src="https://example.com/i.png"/></p>'
    srcs = extract_image_srcs(html)
    assert 'data:image/png;base64,AAAA' in srcs
    assert 'https://example.com/i.png' in srcs
