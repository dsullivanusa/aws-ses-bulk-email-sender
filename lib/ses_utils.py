"""SES-specific utilities for sending emails.

This module handles SES operations like sending raw emails, size validation,
rate limiting, and optional debug dumps. It uses lib/aws_clients for client management.
"""
import os
import time
from typing import Optional, Dict, Any
from lib.aws_clients import get_ses_client, get_s3_client
from lib.rate_limiter import RateLimiter


def send_raw_email(raw_email_bytes: bytes, debug_dump: bool = False, rate_limit_per_second: Optional[float] = None) -> Dict[str, Any]:
    """Send a raw email via SES with optional rate limiting.

    Args:
        raw_email_bytes: The raw MIME email as bytes.
        debug_dump: If True, dump the raw email to S3 for debugging (requires DEBUG_EMAIL_BUCKET env var).
        rate_limit_per_second: Max sends per second (e.g., 10.0). If exceeded, sleeps to comply.

    Returns:
        SES response dict.

    Raises:
        ValueError: If email size exceeds SES limit (40MB).
        Exception: For SES errors.
    """
    # Rate limiting
    limiter = RateLimiter(rate_limit_per_second)
    limiter.wait_if_needed()

    # Check size limit (SES raw email limit is 40MB)
    max_size = 40 * 1024 * 1024  # 40MB
    if len(raw_email_bytes) > max_size:
        raise ValueError(f"Email size {len(raw_email_bytes)} bytes exceeds SES limit of {max_size} bytes")

    # Optional debug dump to S3
    if debug_dump:
        bucket = os.environ.get("DEBUG_EMAIL_BUCKET")
        if bucket:
            key = f"debug_email_{int(time.time())}.eml"
            s3_client = get_s3_client()
            s3_client.put_object(Bucket=bucket, Key=key, Body=raw_email_bytes)  # type: ignore
            print(f"Debug email dumped to s3://{bucket}/{key}")

    # Send via SES
    ses_client = get_ses_client()
    response = ses_client.send_raw_email(RawMessage={'Data': raw_email_bytes})  # type: ignore
    return response  # type: ignore


__all__ = ["send_raw_email"]