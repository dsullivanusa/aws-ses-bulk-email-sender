"""Shared email utilities for cleaning HTML and preparing inlining helpers.

This module contains small, pure-Python helpers that can be unit-tested locally.
Keep heavy AWS/boto3 usage out of import-time code.
"""
from typing import List
import re

__all__ = ["clean_quill_html_for_email", "extract_image_srcs", "build_mime_message_stub"]


def clean_quill_html_for_email(html: str) -> str:
    """Perform lightweight normalization of Quill-produced HTML for email.

    - Remove common Quill wrapper(s) like <div class="ql-editor">...<div>
    - Strip Quill-specific classes and data-* attributes
    - Remove empty paragraphs (only whitespace or &nbsp; or <br>)
    - Collapse consecutive <br> runs into a single <br/>
    - Trim whitespace inside <p>...</p>

    This intentionally avoids heavy HTML parsing dependencies so it remains
    usable in lambda cold-start light-weight contexts. It's not a full HTML
    sanitizer; use more robust tooling if you need full sanitization.
    """
    if not html:
        return ""

    s = html
    # Remove Quill wrapper divs like <div class="ql-editor">...</div>
    s = re.sub(r"<div[^>]*class=[\"']?ql-editor[\"']?[^>]*>(.*?)</div>", r"\1", s, flags=re.I | re.S)

    # Remove classes that start with ql- and data- attributes
    s = re.sub(r"\sclass=[\"'][^\"']*ql-[^\"']*[\"']", "", s, flags=re.I)
    s = re.sub(r"\sdata-[a-zA-Z0-9_-]+=(?:\"[^\"]*\"|'[^']*')", "", s, flags=re.I)

    # Trim whitespace between tags
    s = re.sub(r">\s+<", "><", s)

    # Normalize &nbsp; to a non-breaking space placeholder so we can detect empties
    s = s.replace("&nbsp;", "\u00A0")

    # Remove empty paragraphs: <p>   </p>, <p>&nbsp;</p>, <p><br></p>
    s = re.sub(r"<p(?: [^>]*)?>\s*(?:\u00A0|&nbsp;|<br\s*/?>|\s)*\s*</p>", "", s, flags=re.I)

    # Trim whitespace inside <p>...</p>
    def _trim_p(m: re.Match) -> str:
        inner = m.group(1).strip()
        return f"<p>{inner}</p>"

    s = re.sub(r"<p(?: [^>]*)?>(.*?)</p>", _trim_p, s, flags=re.I | re.S)

    # Collapse consecutive <br> runs into a single <br/>
    s = re.sub(r"(?:<br\s*/?>\s*){2,}", "<br/>", s, flags=re.I)

    # Restore &nbsp; (leave as-is) — keep unicode NBSP if it remained
    # Final strip
    s = s.strip()
    return s


def extract_image_srcs(html: str) -> List[str]:
    """Return a list of all image src values found in the HTML (order-preserving)."""
    if not html:
        return []
    # Very small, permissive regex to capture src attribute values
    matches = re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.I)
    return matches


def build_mime_message_stub(*args, **kwargs):
    """Placeholder for a future shared MIME assembly routine.

    This stub is intentionally minimal so callers can import it during refactors.
    Implementing a full, SES-safe MIME builder belongs to a later phase.
    """
    raise NotImplementedError("build_mime_message_stub is a placeholder; implement later")
