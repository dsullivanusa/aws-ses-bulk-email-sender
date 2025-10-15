"""Shared utility library for AWS SES bulk email sender.

This package contains reusable utilities and helpers for the bulk email system.
All modules are designed to be lightweight and avoid creating AWS clients at import time,
making them safe for use in test environments and local development.

Modules:
    aws_clients: Lazy-loaded AWS client management with caching
    dynamodb_utils: DynamoDB table operations, data conversion utilities, batch operations with retry logic, and error handling
    html_utils: HTML cleaning and email content processing utilities
    mime_utils: MIME message building and email construction utilities
    quill_utils: Utilities for processing Quill.js editor content
    rate_limiter: Rate limiting and throttling utilities
    ses_utils: AWS SES-specific operations and validations
    sqs_utils: SQS queue operations with edge case handling

Design Principles:
    - Lightweight imports (no AWS client creation at import time)
    - Comprehensive error handling and validation
    - Type-safe with proper annotations
    - Testable without AWS credentials
    - Production-ready with monitoring and logging
"""