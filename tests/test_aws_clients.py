"""Basic tests for lib.aws_clients to ensure import and function signatures.

These tests are lightweight and avoid network calls.
"""
from lib.aws_clients import get_boto3_session, get_client, get_ses_client, get_sqs_client


def test_get_boto3_session():
    sess = get_boto3_session()
    assert sess is not None


def test_get_client_signature():
    # Do not actually call AWS; just ensure we can get a client object type
    client = get_client.__annotations__  # type: ignore
    assert callable(get_client)


def test_get_ses_client_callable():
    assert callable(get_ses_client)


def test_get_sqs_client_callable():
    assert callable(get_sqs_client)
