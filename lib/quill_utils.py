"""Pure-Python utilities for cleaning and analyzing Quill-generated HTML.

These functions handle normalization of HTML produced by the Quill editor,
such as removing empty paragraphs, collapsing consecutive <br> tags, and
providing diagnostic counts. No AWS dependencies here.
"""
import re
from typing import Dict, Optional


def clean_quill_html_for_email(html: Optional[str]) -> Optional[str]:
    """Clean and normalize Quill-generated HTML for email sending.

    - Removes empty <p> tags (e.g., <p><br></p>, <p>&nbsp;</p>, <p>  </p>).
    - Collapses multiple consecutive <br> into a single <br>.
    - Trims leading/trailing whitespace inside <p> tags.
    - Strips Quill-specific classes/attributes if present.

    Args:
        html: The raw HTML string from Quill. Can be None.

    Returns:
        Cleaned HTML string, or None if input was None.
    """
    if html is None:
        return None
    if not html:
        return html

    # Remove Quill-specific artifacts (classes, data attributes)
    html = re.sub(r'\s+class="[^"]*"', '', html)
    html = re.sub(r'\s+data-[^=]*="[^"]*"', '', html)

    # Remove empty paragraphs: <p><br></p>, <p>&nbsp;</p>, <p>  </p>, etc.
    html = re.sub(r'<p[^>]*>\s*(<br\s*/?\s*>|&nbsp;|\s*)\s*</p>', '', html, flags=re.IGNORECASE)

    # Collapse multiple consecutive <br> into one
    html = re.sub(r'(<br\s*/?\s*>)\s*\1+', r'\1', html, flags=re.IGNORECASE)

    # Trim whitespace inside <p> tags
    html = re.sub(r'<p([^>]*)>\s*(.*?)\s*</p>', r'<p\1>\2</p>', html, flags=re.IGNORECASE | re.DOTALL)

    # Collapse runs of empty paragraphs (e.g., multiple <p></p> in a row)
    html = re.sub(r'(<p[^>]*></p>\s*)+', '', html, flags=re.IGNORECASE)

    return html.strip()


def analyze_html(html: str) -> Dict[str, int]:
    """Analyze HTML for diagnostic counts.

    Returns a dict with counts of:
    - p_count: Total <p> tags.
    - empty_p_count: Empty or whitespace-only <p> tags.
    - br_runs: Number of consecutive <br> runs (e.g., 2+ in a row).

    Args:
        html: The HTML string to analyze.

    Returns:
        Dict with diagnostic counts.
    """
    if not html:
        return {"p_count": 0, "empty_p_count": 0, "br_runs": 0}

    # Count total <p> tags
    p_count = len(re.findall(r'<p[^>]*>', html, re.IGNORECASE))

    # Count empty <p> tags (after trimming content)
    empty_p_count = len(re.findall(r'<p[^>]*>\s*(<br\s*/?\s*>|&nbsp;|\s*)\s*</p>', html, re.IGNORECASE))

    # Count runs of 2+ consecutive <br>
    br_runs = len(re.findall(r'(<br\s*/?\s*>\s*){2,}', html, re.IGNORECASE))

    return {
        "p_count": p_count,
        "empty_p_count": empty_p_count,
        "br_runs": br_runs
    }


__all__ = ["clean_quill_html_for_email", "analyze_html"]