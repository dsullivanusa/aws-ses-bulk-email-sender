"""Unit tests for lib/rate_limiter.py.

Tests the RateLimiter class functionality.
"""
from unittest.mock import patch
from lib.rate_limiter import RateLimiter


def test_rate_limiter_no_limit():
    """Test rate limiter with no limit set."""
    limiter = RateLimiter()
    with patch('lib.rate_limiter.time.sleep') as mock_sleep:
        limiter.wait_if_needed()
        mock_sleep.assert_not_called()


def test_rate_limiter_with_limit_no_wait():
    """Test rate limiter that doesn't need to wait (first call)."""
    limiter = RateLimiter(10.0)  # 10 per second
    with patch('lib.rate_limiter.time.sleep') as mock_sleep, \
         patch('lib.rate_limiter.time.time', return_value=0.0):
        limiter.wait_if_needed()
        mock_sleep.assert_not_called()


def test_rate_limiter_with_limit_wait():
    """Test rate limiter that needs to wait."""
    limiter = RateLimiter(10.0)  # 10 per second, 0.1s interval
    limiter.last_operation_time = 0.0  # Simulate previous operation
    with patch('lib.rate_limiter.time.sleep') as mock_sleep, \
         patch('lib.rate_limiter.time.time', side_effect=[0.05, 0.15]):
        limiter.wait_if_needed()  # current 0.05, time_since 0.05, min_interval 0.1, sleep 0.05
        mock_sleep.assert_called_once_with(0.05)