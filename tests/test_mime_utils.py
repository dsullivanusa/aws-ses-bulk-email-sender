"""Unit tests for lib/mime_utils.py.

Uses pytest and mocks for email functionality.
"""
import os
import pytest  # type: ignore
import tempfile
from unittest.mock import patch, MagicMock
from email.mime.multipart import MIMEMultipart
from lib.mime_utils import (
    build_mime_message,
    attach_inline_image,
    attach_file,
    get_message_size,
    validate_message_size
)


def test_build_mime_message_basic():
    """Test building a basic MIME message."""
    msg = build_mime_message(
        subject="Test Subject",
        html_body="<h1>Test</h1>",
        from_email="sender@example.com",
        to_emails=["recipient@example.com"]
    )

    assert isinstance(msg, MIMEMultipart)
    assert msg['Subject'] == "Test Subject"
    assert msg['From'] == "sender@example.com"
    assert msg['To'] == "recipient@example.com"

    # Check that HTML part is included
    parts = msg.get_payload()  # type: ignore
    assert len(parts) >= 1
    html_part = parts[-1]  # HTML part should be last  # type: ignore
    assert html_part.get_content_type() == "text/html"  # type: ignore
    assert "<h1>Test</h1>" in html_part.get_payload()  # type: ignore


def test_build_mime_message_with_text():
    """Test building MIME message with both HTML and text parts."""
    msg = build_mime_message(
        subject="Test Subject",
        html_body="<h1>Test</h1>",
        text_body="Plain text version",
        from_email="sender@example.com"
    )

    parts = msg.get_payload()  # type: ignore
    assert len(parts) == 2

    # First part should be text/plain
    text_part = parts[0]  # type: ignore
    assert text_part.get_content_type() == "text/plain"  # type: ignore
    assert "Plain text version" in text_part.get_payload()  # type: ignore

    # Second part should be text/html
    html_part = parts[1]  # type: ignore
    assert html_part.get_content_type() == "text/html"  # type: ignore
    assert "<h1>Test</h1>" in html_part.get_payload()  # type: ignore


def test_build_mime_message_with_cc_bcc():
    """Test building MIME message with CC and BCC."""
    msg = build_mime_message(
        subject="Test Subject",
        html_body="<p>Test</p>",
        cc_emails=["cc@example.com"],
        bcc_emails=["bcc@example.com"]
    )

    assert msg['Cc'] == "cc@example.com"
    assert msg['Bcc'] == "bcc@example.com"


def test_build_mime_message_with_headers():
    """Test building MIME message with custom headers."""
    msg = build_mime_message(
        subject="Test Subject",
        html_body="<p>Test</p>",
        headers={"X-Custom": "value", "X-Priority": "1"}
    )

    assert msg['X-Custom'] == "value"
    assert msg['X-Priority'] == "1"


def test_attach_inline_image():
    """Test attaching an inline image."""
    msg = build_mime_message("Test", "<p>Test</p>")
    image_data = b"fake_png_data"

    attach_inline_image(msg, image_data, "test_image", "test.png")

    parts = msg.get_payload()  # type: ignore
    # Should have HTML part + image part
    assert len(parts) >= 2

    image_part = None
    for part in parts:  # type: ignore
        if part.get_content_type().startswith('image/'):  # type: ignore
            image_part = part
            break

    assert image_part is not None
    assert image_part['Content-ID'] == '<test_image>'  # type: ignore
    assert 'inline' in image_part['Content-Disposition']  # type: ignore


def test_attach_file():
    """Test attaching a file."""
    msg = build_mime_message("Test", "<p>Test</p>")

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test content")
        temp_file = f.name

    try:
        attach_file(msg, temp_file, "test.txt")

        parts = msg.get_payload()  # type: ignore
        # Should have HTML part + file attachment
        assert len(parts) >= 2

        attachment_part = None
        for part in parts:  # type: ignore
            if 'attachment' in part.get('Content-Disposition', ''):  # type: ignore
                attachment_part = part
                break

        assert attachment_part is not None
        assert 'test.txt' in attachment_part['Content-Disposition']  # type: ignore
        assert attachment_part.get_content_type() == "text/plain"  # type: ignore

    finally:
        os.unlink(temp_file)


def test_attach_file_not_found():
    """Test attaching a non-existent file raises error."""
    msg = build_mime_message("Test", "<p>Test</p>")

    with pytest.raises(FileNotFoundError):
        attach_file(msg, "/nonexistent/file.txt")


def test_get_message_size():
    """Test getting message size."""
    msg = build_mime_message("Test", "<h1>Content</h1>")
    size = get_message_size(msg)

    assert isinstance(size, int)
    assert size > 0

    # Size should be reasonable
    message_str = msg.as_string()
    expected_size = len(message_str.encode('utf-8'))
    assert size == expected_size


def test_validate_message_size_valid():
    """Test validating a message within size limits."""
    msg = build_mime_message("Test", "<p>Small content</p>")
    is_valid, error = validate_message_size(msg, max_size_bytes=10000)

    assert is_valid is True
    assert error == ""


def test_validate_message_size_too_large():
    """Test validating a message that exceeds size limits."""
    # Create a message with large content
    large_content = "<p>" + "x" * 10000 + "</p>"
    msg = build_mime_message("Test", large_content)

    is_valid, error = validate_message_size(msg, max_size_bytes=1000)

    assert is_valid is False
    assert "exceeds limit" in error


def test_attach_file_content_types():
    """Test that different file types get correct content types."""
    msg = build_mime_message("Test", "<p>Test</p>")

    test_files = [
        (".pdf", "application/pdf"),
        (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (".txt", "text/plain"),
        (".jpg", "image/jpeg"),
        (".unknown", "application/octet-stream")
    ]

    for ext, expected_type in test_files:
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write("test")
            temp_file = f.name

        try:
            attach_file(msg, temp_file)

            # Find the attachment part
            parts = msg.get_payload()  # type: ignore
            attachment_part = None
            for part in parts:  # type: ignore
                if 'attachment' in part.get('Content-Disposition', ''):  # type: ignore
                    attachment_part = part
                    break

            assert attachment_part is not None
            assert attachment_part.get_content_type() == expected_type  # type: ignore

        finally:
            os.unlink(temp_file)