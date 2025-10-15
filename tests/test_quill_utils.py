"""Unit tests for lib/quill_utils.py.

Run with pytest: pytest tests/test_quill_utils.py
"""
import pytest  # type: ignore
from lib.quill_utils import clean_quill_html_for_email, analyze_html


def test_clean_quill_html_basic():
    """Test basic cleaning of Quill HTML."""
    input_html = '<p class="ql-align-center">Hello {{first_name}}</p><p><br></p><p>&nbsp;</p>'
    expected = '<p>Hello {{first_name}}</p>'
    result = clean_quill_html_for_email(input_html)
    assert result == expected


def test_clean_quill_html_collapse_br():
    """Test collapsing multiple <br> tags."""
    input_html = '<p>Line1<br><br><br>Line2</p>'
    expected = '<p>Line1<br>Line2</p>'
    result = clean_quill_html_for_email(input_html)
    assert result == expected


def test_clean_quill_html_trim_whitespace():
    """Test trimming whitespace inside <p>."""
    input_html = '<p>  Hello  </p>'
    expected = '<p>Hello</p>'
    result = clean_quill_html_for_email(input_html)
    assert result == expected


def test_clean_quill_html_empty():
    """Test handling of empty or None input."""
    assert clean_quill_html_for_email('') == ''
    assert clean_quill_html_for_email(None) == None


def test_analyze_html_counts():
    """Test diagnostic counts."""
    html = '<p>Hello</p><p><br></p><p>&nbsp;</p><p>World<br><br><br></p>'
    result = analyze_html(html)
    assert result["p_count"] == 4
    assert result["empty_p_count"] == 2  # <p><br></p> and <p>&nbsp;</p>
    assert result["br_runs"] == 1  # One run of 3 <br>


def test_analyze_html_empty():
    """Test analysis of empty HTML."""
    result = analyze_html('')
    assert result == {"p_count": 0, "empty_p_count": 0, "br_runs": 0}