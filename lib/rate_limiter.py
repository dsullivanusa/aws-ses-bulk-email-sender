"""Rate limiting utilities.

This module provides simple rate limiting functionality that can be used
across different parts of the application to enforce sending rates.
"""
import time
from typing import Optional


class RateLimiter:
    """Simple rate limiter for controlling operation frequency."""

    def __init__(self, rate_per_second: Optional[float] = None):
        """Initialize rate limiter.

        Args:
            rate_per_second: Maximum operations per second. If None, no limiting.
        """
        self.rate_per_second = rate_per_second
        self.last_operation_time: Optional[float] = None

    def wait_if_needed(self):
        """Sleep if rate limit would be exceeded."""
        if not self.rate_per_second:
            return
        current_time = time.time()
        if self.last_operation_time is not None:
            min_interval = 1.0 / self.rate_per_second
            time_since_last = current_time - self.last_operation_time
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
        self.last_operation_time = time.time()


__all__ = ["RateLimiter"]