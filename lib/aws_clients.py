"""Lightweight helpers for obtaining boto3 sessions and clients lazily.

Keep import-time overhead minimal so modules that import this file can be used in local tests
without requiring AWS credentials. Clients are created on demand via the `get_client` helper.
"""
from typing import Optional, Dict, Tuple
import boto3  # type: ignore
from boto3.session import Session  # type: ignore
from botocore.client import BaseClient  # type: ignore
import os
import threading


_session: Optional[Session] = None
_client_cache: Dict[Tuple[str, Optional[str], Optional[str]], BaseClient] = {}
_lock = threading.Lock()

# The client cache is keyed by (service_name, region_name, profile_name).
# We canonicalize empty strings to None so callers that pass "" or None map
# to the same cached client. This allows callers to omit region/profile and
# rely on environment/session defaults while keeping the cache consistent.


def get_boto3_session(profile_name: Optional[str] = None) -> Session:
    """Return a boto3 Session object, creating it lazily.

    Pass `profile_name` to use a specific AWS CLI profile. Avoids creating clients at module import time.
    """
    global _session
    # Protect lazy initialization with a lock for thread-safety
    with _lock:
        if _session is None:
            if profile_name:
                _session = boto3.Session(profile_name=profile_name)
            else:
                _session = boto3.Session()
    return _session


def get_client(service_name: str, region_name: Optional[str] = None, profile_name: Optional[str] = None) -> BaseClient:
    """Return a boto3 client for the given service, using a lazy session.

    This function avoids creating a client until it's actually needed.
    """
    # Use a simple cache keyed by service/region/profile to avoid recreating clients
    # Normalize empty strings -> None so keys are consistent.
    region = region_name if region_name else None
    profile = profile_name if profile_name else None
    key = (service_name, region, profile)
    with _lock:
        client = _client_cache.get(key)
        if client is not None:
            return client
        session = get_boto3_session(profile_name=profile_name)
        if region_name:
            client = session.client(service_name, region_name=region_name)  # type: ignore
        else:
            client = session.client(service_name)  # type: ignore
        _client_cache[key] = client
        return client  # type: ignore


def reset_clients() -> None:
    """Clear the client cache. Useful for tests."""
    with _lock:
        _client_cache.clear()


def reset_session() -> None:
    """Reset the cached boto3 session and clients (test helper)."""
    global _session
    with _lock:
        _session = None
        _client_cache.clear()


def get_ses_client(region_name: Optional[str] = None) -> BaseClient:
    """Convenience for SES client using environment-based region or default.

    Do not create the client until this function is called.
    """
    region = region_name or os.environ.get("AWS_SES_REGION")
    return get_client("ses", region_name=region)


def get_s3_client(region_name: Optional[str] = None) -> BaseClient:
    region = region_name or os.environ.get("AWS_S3_REGION")
    return get_client("s3", region_name=region)


def get_sqs_client(region_name: Optional[str] = None) -> BaseClient:
    """Convenience for SQS client using environment-based region or default.

    Do not create the client until this function is called.
    """
    region = region_name or os.environ.get("AWS_SQS_REGION")
    return get_client("sqs", region_name=region)


def get_dynamodb_client(region_name: Optional[str] = None) -> BaseClient:
    """Convenience for DynamoDB client using environment-based region or default.

    Do not create the client until this function is called.
    """
    region = region_name or os.environ.get("AWS_DYNAMODB_REGION")
    return get_client("dynamodb", region_name=region)


__all__ = ["get_boto3_session", "get_client", "get_ses_client", "get_s3_client", "get_sqs_client", "get_dynamodb_client"]
