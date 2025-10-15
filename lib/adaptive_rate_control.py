"""
Adaptive Rate Control Module
Provides intelligent rate limiting for AWS services with attachment-aware delays
and automatic throttle detection/recovery.
"""

import time
import logging
import os
from typing import List, Dict, Any, Optional


class AdaptiveRateControl:
    """
    Adaptive rate control for AWS service operations.

    This class provides intelligent rate limiting that:
    - Adjusts delays based on attachment sizes
    - Detects and handles service throttling
    - Gradually recovers from throttle events
    - Maintains configurable delay bounds
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        # Base rate control settings
        self.base_delay = float(os.environ.get('BASE_DELAY_SECONDS', '0.1'))  # Base delay between emails
        self.max_delay = float(os.environ.get('MAX_DELAY_SECONDS', '5.0'))   # Maximum delay allowed
        self.min_delay = float(os.environ.get('MIN_DELAY_SECONDS', '0.01'))  # Minimum delay allowed

        # Attachment size thresholds (in bytes)
        self.small_attachment_threshold = 1024 * 1024      # 1MB
        self.medium_attachment_threshold = 5 * 1024 * 1024  # 5MB
        self.large_attachment_threshold = 10 * 1024 * 1024  # 10MB

        # Rate adjustment factors
        self.small_attachment_factor = 1.5    # 50% slower for small attachments
        self.medium_attachment_factor = 2.0   # 100% slower for medium attachments
        self.large_attachment_factor = 3.0    # 200% slower for large attachments

        # Throttle detection and recovery
        self.throttle_detection_window = 10   # Look for throttles in last N emails
        self.throttle_backoff_factor = 2.0    # Double delay when throttled
        self.throttle_recovery_time = 60      # Seconds to wait before reducing delay
        self.max_throttle_backoffs = 5        # Maximum consecutive throttle backoffs

        # Rate control state
        self.current_delay: float = self.base_delay
        self.recent_throttles: List[float] = []  # Track recent throttle events
        self.last_throttle_time: Optional[float] = None
        self.consecutive_throttles: int = 0

        # Logger setup
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info("Adaptive Rate Control initialized:")
        self.logger.info(f"  Base delay: {self.base_delay}s")
        self.logger.info(f"  Delay range: {self.min_delay}s - {self.max_delay}s")
        self.logger.info(f"  Attachment thresholds: {self.small_attachment_threshold//1024//1024}MB, {self.medium_attachment_threshold//1024//1024}MB, {self.large_attachment_threshold//1024//1024}MB")

    def calculate_attachment_delay(self, attachments: List[Dict[str, Any]], s3_client: Optional[Any] = None, attachments_bucket: str = 'jcdc-ses-contact-list') -> float:
        """Calculate delay based on attachment sizes"""
        if not attachments:
            return self.base_delay

        total_size = 0
        for attachment in attachments:
            try:
                # Try to get file size from S3 metadata
                s3_key = attachment.get('s3_key')
                if s3_key and s3_client:
                    response = s3_client.head_object(Bucket=attachments_bucket, Key=s3_key)
                    file_size = response.get('ContentLength', 0)
                    total_size += file_size
                    self.logger.debug(f"Attachment {attachment.get('filename', 'unknown')}: {file_size} bytes")
            except Exception as e:
                self.logger.warning(f"Could not get size for attachment {attachment.get('filename', 'unknown')}: {str(e)}")
                # Estimate based on filename if we can't get actual size
                total_size += 1024 * 1024  # Assume 1MB if unknown

        # Determine rate factor based on total attachment size
        if total_size <= self.small_attachment_threshold:
            factor = self.small_attachment_factor
            size_category = "small"
        elif total_size <= self.medium_attachment_threshold:
            factor = self.medium_attachment_factor
            size_category = "medium"
        else:
            factor = self.large_attachment_factor
            size_category = "large"

        delay = self.base_delay * factor
        self.logger.info(f"Attachment size: {total_size//1024//1024}MB ({size_category}), delay factor: {factor}x, calculated delay: {delay:.3f}s")

        return min(delay, self.max_delay)

    def detect_throttle_exception(self, exception: Exception) -> bool:
        """Detect if an exception is a throttle/rate limit exception"""
        throttle_indicators = [
            'throttle',
            'rate limit',
            'rate exceeded',
            'too many requests',
            'quota exceeded',
            'service unavailable',
            'slow down'
        ]

        error_message = str(exception).lower()
        for indicator in throttle_indicators:
            if indicator in error_message:
                return True

        # Check for specific AWS SES throttle errors
        try:
            if hasattr(exception, 'response'):
                error_code = exception.response.get('Error', {}).get('Code', '')  # type: ignore
                if error_code in ['Throttling', 'ServiceUnavailable', 'SlowDown']:
                    return True
        except AttributeError:
            pass

        return False

    def handle_throttle_detected(self) -> float:
        """Handle throttle detection by adjusting rate"""
        current_time = time.time()
        self.recent_throttles.append(current_time)
        self.last_throttle_time = current_time
        self.consecutive_throttles += 1

        # Clean old throttle events
        cutoff_time = current_time - self.throttle_detection_window
        self.recent_throttles = [t for t in self.recent_throttles if t > cutoff_time]

        # Apply backoff
        if self.consecutive_throttles <= self.max_throttle_backoffs:
            self.current_delay = min(
                self.current_delay * self.throttle_backoff_factor,
                self.max_delay
            )
            self.logger.warning(f"Throttle detected! Increasing delay to {self.current_delay:.3f}s (backoff #{self.consecutive_throttles})")
        else:
            self.logger.error(f"Maximum throttle backoffs ({self.max_throttle_backoffs}) reached. Keeping delay at {self.current_delay:.3f}s")

        return self.current_delay

    def recover_from_throttle(self) -> float:
        """Gradually recover from throttle by reducing delay"""
        current_time = time.time()

        # Only start recovery if enough time has passed since last throttle
        if (self.last_throttle_time and
            current_time - self.last_throttle_time > self.throttle_recovery_time and
            self.current_delay > self.base_delay):

            # Gradually reduce delay
            recovery_factor = 0.9  # Reduce delay by 10%
            self.current_delay = max(
                self.current_delay * recovery_factor,
                self.base_delay
            )

            if self.current_delay <= self.base_delay:
                self.consecutive_throttles = 0
                self.logger.info("Recovered from throttle - back to base delay")
            else:
                self.logger.info(f"Recovering from throttle - reducing delay to {self.current_delay:.3f}s")

        return self.current_delay

    def get_delay_for_email(self, attachments: List[Dict[str, Any]], exception: Optional[Exception] = None, s3_client: Optional[Any] = None, attachments_bucket: str = 'jcdc-ses-contact-list') -> float:
        """Get the appropriate delay for the next email"""
        # Handle throttle exceptions
        if exception and self.detect_throttle_exception(exception):
            return self.handle_throttle_detected()

        # Check for throttle recovery
        self.recover_from_throttle()

        # Calculate delay based on attachments
        attachment_delay = self.calculate_attachment_delay(attachments, s3_client, attachments_bucket)

        # Use the higher of attachment delay or current throttle delay
        final_delay = max(attachment_delay, self.current_delay)

        # Ensure delay is within bounds
        final_delay = max(self.min_delay, min(final_delay, self.max_delay))

        return final_delay