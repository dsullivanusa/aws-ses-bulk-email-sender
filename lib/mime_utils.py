"""MIME message building utilities for email construction.

This module handles the construction of MIME multipart messages for email sending.
Separated from email_utils.py to maintain single responsibility principle.
"""
from typing import Dict, List, Optional, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os

__all__ = ["build_mime_message", "attach_inline_image", "attach_file"]


def build_mime_message(
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    to_emails: Optional[List[str]] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> MIMEMultipart:
    """Build a complete MIME multipart message for email sending.

    Args:
        subject: Email subject line
        html_body: HTML content for the email
        text_body: Optional plain text alternative
        from_email: Sender email address
        to_emails: List of recipient email addresses
        cc_emails: List of CC email addresses
        bcc_emails: List of BCC email addresses
        reply_to: Reply-to email address
        headers: Additional email headers

    Returns:
        Complete MIMEMultipart message ready for sending
    """
    # Create the root message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject

    if from_email:
        msg['From'] = from_email

    if to_emails:
        msg['To'] = ', '.join(to_emails)

    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)

    if reply_to:
        msg['Reply-To'] = reply_to

    # Add custom headers
    if headers:
        for key, value in headers.items():
            msg[key] = value

    # Add the text/plain part (if provided)
    if text_body:
        text_part = MIMEText(text_body, 'plain', 'utf-8')
        msg.attach(text_part)

    # Add the text/html part (required)
    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(html_part)

    return msg


def attach_inline_image(
    msg: MIMEMultipart,
    image_data: bytes,
    content_id: str,
    filename: Optional[str] = None,
    content_type: str = 'image/png'
) -> None:
    """Attach an inline image to a MIME message.

    Args:
        msg: The MIMEMultipart message to attach to
        image_data: Raw image bytes
        content_id: Content-ID for inline referencing (e.g., 'image1')
        filename: Optional filename for the attachment
        content_type: MIME content type (default: image/png)
    """
    # Create image attachment
    image = MIMEImage(image_data, _subtype=content_type.split('/')[1])
    image.add_header('Content-ID', f'<{content_id}>')
    image.add_header('Content-Disposition', 'inline')

    if filename:
        image.add_header('Content-Disposition', f'inline; filename="{filename}"')

    msg.attach(image)


def attach_file(
    msg: MIMEMultipart,
    file_path: str,
    filename: Optional[str] = None,
    content_type: Optional[str] = None
) -> None:
    """Attach a file to a MIME message.

    Args:
        msg: The MIMEMultipart message to attach to
        file_path: Path to the file to attach
        filename: Display name for the attachment (defaults to basename)
        content_type: MIME content type (auto-detected if not provided)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Attachment file not found: {file_path}")

    # Determine filename and content type
    if not filename:
        filename = os.path.basename(file_path)

    if not content_type:
        # Simple content type detection based on extension
        ext = os.path.splitext(filename)[1].lower()
        content_type_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.zip': 'application/zip',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')

    # Read file data
    with open(file_path, 'rb') as f:
        file_data = f.read()

    # Create attachment
    main_type, sub_type = content_type.split('/', 1)
    attachment = MIMEBase(main_type, sub_type)
    attachment.set_payload(file_data)
    encoders.encode_base64(attachment)

    attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    attachment.add_header('Content-Type', f'{content_type}; name="{filename}"')

    msg.attach(attachment)


def get_message_size(msg: MIMEMultipart) -> int:
    """Get the size of a MIME message in bytes.

    Args:
        msg: The MIME message to measure

    Returns:
        Size in bytes
    """
    return len(msg.as_string().encode('utf-8'))


def validate_message_size(msg: MIMEMultipart, max_size_bytes: int = 10485760) -> Tuple[bool, str]:
    """Validate that a MIME message is within size limits.

    Args:
        msg: The MIME message to validate
        max_size_bytes: Maximum allowed size (default: 10MB for SES)

    Returns:
        Tuple of (is_valid, error_message)
    """
    size = get_message_size(msg)
    if size > max_size_bytes:
        return False, f"Message size {size} bytes exceeds limit of {max_size_bytes} bytes"
    return True, ""