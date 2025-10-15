"""Unit tests for lib/ses_utils.py.

Uses pytest and mocks for AWS calls.
"""
import os
import pytest  # type: ignore
from unittest.mock import patch, MagicMock
from lib.ses_utils import send_raw_email


def test_send_raw_email_success():
    """Test successful send."""
    mock_ses = MagicMock()
    mock_ses.send_raw_email.return_value = {"MessageId": "test-id"}

    with patch('lib.ses_utils.get_ses_client', return_value=mock_ses):
        response = send_raw_email(b"test email")
        assert response["MessageId"] == "test-id"
        mock_ses.send_raw_email.assert_called_once()

def test_send_raw_email_size_limit():
    """Test size limit enforcement."""
    large_email = b"x" * (41 * 1024 * 1024)  # 41MB
    with pytest.raises(ValueError, match="exceeds SES limit"):  # type: ignore
        send_raw_email(large_email)

def test_send_raw_email_debug_dump():
    """Test debug dump to S3."""
    mock_s3 = MagicMock()
    mock_ses = MagicMock()
    mock_ses.send_raw_email.return_value = {"MessageId": "test-id"}

    with patch.dict(os.environ, {"DEBUG_EMAIL_BUCKET": "test-bucket"}), \
         patch('lib.ses_utils.get_s3_client', return_value=mock_s3), \
         patch('lib.ses_utils.get_ses_client', return_value=mock_ses):
        response = send_raw_email(b"test", debug_dump=True)
        assert response["MessageId"] == "test-id"
        mock_s3.put_object.assert_called_once()
        mock_ses.send_raw_email.assert_called_once()

def test_send_raw_email_debug_no_bucket():
    """Test debug dump skipped if no bucket env var."""
    mock_ses = MagicMock()
    mock_ses.send_raw_email.return_value = {"MessageId": "test-id"}

    with patch.dict(os.environ, {}, clear=True), \
         patch('lib.ses_utils.get_ses_client', return_value=mock_ses):
        response = send_raw_email(b"test", debug_dump=True)
        assert response["MessageId"] == "test-id"
        mock_ses.send_raw_email.assert_called_once()

def test_send_raw_email_rate_limit():
    """Test rate limiting sleeps when needed."""
    mock_ses = MagicMock()
    mock_ses.send_raw_email.return_value = {"MessageId": "test-id"}
    mock_limiter = MagicMock()
    mock_limiter.wait_if_needed = MagicMock()

    with patch('lib.ses_utils.get_ses_client', return_value=mock_ses), \
         patch('lib.ses_utils.RateLimiter', return_value=mock_limiter):
        response = send_raw_email(b"test", rate_limit_per_second=10.0)
        assert response["MessageId"] == "test-id"
        mock_limiter.wait_if_needed.assert_called_once()
        mock_ses.send_raw_email.assert_called_once()

def test_send_raw_email_no_rate_limit():
    """Test no sleep when rate limit not exceeded."""
    mock_ses = MagicMock()
    mock_ses.send_raw_email.return_value = {"MessageId": "test-id"}

    with patch('lib.ses_utils.get_ses_client', return_value=mock_ses):
        response = send_raw_email(b"test")  # No rate limit
        assert response["MessageId"] == "test-id"
        mock_ses.send_raw_email.assert_called_once()