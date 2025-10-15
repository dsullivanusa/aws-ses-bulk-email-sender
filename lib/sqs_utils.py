"""SQS-specific utilities for queue operations.

This module handles SQS operations like getting queue URLs, sending messages,
and managing message attributes. It uses lib/aws_clients for client management.
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from lib.aws_clients import get_sqs_client


def get_queue_url(queue_name: str) -> str:
    """Get the URL for an SQS queue by name.

    Args:
        queue_name: Name of the SQS queue.

    Returns:
        Queue URL string.

    Raises:
        Exception: If queue doesn't exist or other SQS errors.
    """
    sqs_client = get_sqs_client()
    response = sqs_client.get_queue_url(QueueName=queue_name)  # type: ignore
    return response['QueueUrl']  # type: ignore


def validate_message_size(message_body: Dict[str, Any], message_attributes: Optional[Dict[str, Dict[str, str]]] = None) -> Tuple[bool, str]:
    """Validate message size against SQS limits.

    Args:
        message_body: Dictionary that will be JSON-encoded.
        message_attributes: Optional message attributes.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        # Convert to JSON string to check size
        message_body_json = json.dumps(message_body)
        body_size = len(message_body_json.encode('utf-8'))

        # SQS limit is 256KB per message
        max_size = 256 * 1024

        if body_size > max_size:
            return False, f"Message body size {body_size} bytes exceeds SQS limit of {max_size} bytes"

        # Check message attributes if provided
        if message_attributes:
            if len(message_attributes) > 10:
                return False, f"Too many message attributes: {len(message_attributes)} (max 10)"

            for attr_name, attr_data in message_attributes.items():
                if len(attr_name) > 256:
                    return False, f"Message attribute name '{attr_name}' too long (max 256 chars)"
                if len(attr_data.get('StringValue', '')) > 1024:
                    return False, f"Message attribute '{attr_name}' value too long (max 1024 chars)"

        return True, ""
    except Exception as e:
        return False, f"Message validation error: {str(e)}"


def send_message(queue_url: str, message_body: Dict[str, Any], message_attributes: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
    """Send a message to an SQS queue with size validation.

    Args:
        queue_url: URL of the SQS queue.
        message_body: Dictionary that will be JSON-encoded as the message body.
        message_attributes: Optional message attributes for filtering/routing.

    Returns:
        SQS response dict containing MessageId and other metadata.

    Raises:
        ValueError: If message exceeds size limits.
        Exception: For SQS errors.
    """
    # Validate message size and attributes
    is_valid, error_msg = validate_message_size(message_body, message_attributes)
    if not is_valid:
        raise ValueError(error_msg)

    sqs_client = get_sqs_client()

    # Convert message body to JSON string
    message_body_json = json.dumps(message_body)

    # Prepare the send_message call
    send_params: Dict[str, Any] = {
        'QueueUrl': queue_url,
        'MessageBody': message_body_json
    }

    if message_attributes:
        send_params['MessageAttributes'] = message_attributes

    response = sqs_client.send_message(**send_params)  # type: ignore
    return response  # type: ignore


def validate_batch_messages(messages: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Validate a batch of messages against SQS limits.

    Args:
        messages: List of message dictionaries.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not messages:
        return False, "Empty message batch"

    if len(messages) > 10:
        return False, f"Too many messages in batch: {len(messages)} (max 10)"

    total_size = 0
    for i, message in enumerate(messages):
        body = message.get('body', {})
        attributes = message.get('attributes')

        try:
            message_body_json = json.dumps(body)
            body_size = len(message_body_json.encode('utf-8'))
            total_size += body_size

            # Individual message size check
            if body_size > 256 * 1024:
                return False, f"Message {i} body size {body_size} bytes exceeds SQS limit of 256KB"

            # Message attributes validation
            if attributes:
                if len(attributes) > 10:
                    return False, f"Message {i} has too many attributes: {len(attributes)} (max 10)"

                for attr_name, attr_data in attributes.items():
                    if len(attr_name) > 256:
                        return False, f"Message {i} attribute name '{attr_name}' too long (max 256 chars)"
                    if len(attr_data.get('StringValue', '')) > 1024:
                        return False, f"Message {i} attribute '{attr_name}' value too long (max 1024 chars)"

        except Exception as e:
            return False, f"Message {i} validation error: {str(e)}"

    # Total batch size check (256KB limit for entire batch)
    if total_size > 256 * 1024:
        return False, f"Total batch size {total_size} bytes exceeds SQS limit of 256KB"

    return True, ""


def send_bulk_messages(queue_url: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send multiple messages to an SQS queue in a single batch operation with validation.

    Args:
        queue_url: URL of the SQS queue.
        messages: List of message dictionaries, each containing:
            - 'body': Dict to be JSON-encoded as message body
            - 'attributes': Optional message attributes dict

    Returns:
        SQS response dict with batch results.

    Raises:
        ValueError: If batch exceeds size or count limits.
        Exception: For SQS errors.
    """
    # Validate entire batch
    is_valid, error_msg = validate_batch_messages(messages)
    if not is_valid:
        raise ValueError(error_msg)

    sqs_client = get_sqs_client()

    # Prepare entries for send_message_batch
    entries: List[Dict[str, Any]] = []
    for i, message in enumerate(messages):
        entry = {
            'Id': str(i),
            'MessageBody': json.dumps(message['body'])
        }

        if message.get('attributes'):
            entry['MessageAttributes'] = message['attributes']

        entries.append(entry)

    response = sqs_client.send_message_batch(  # type: ignore
        QueueUrl=queue_url,
        Entries=entries
    )  # type: ignore

    return response  # type: ignore


def get_queue_attributes(queue_url: str, attribute_names: List[str]) -> Dict[str, str]:
    """Get queue attributes for monitoring and diagnostics.

    Args:
        queue_url: URL of the SQS queue.
        attribute_names: List of attribute names to retrieve.

    Returns:
        Dictionary of queue attributes.

    Raises:
        Exception: For SQS errors.
    """
    sqs_client = get_sqs_client()
    response = sqs_client.get_queue_attributes(  # type: ignore
        QueueUrl=queue_url,
        AttributeNames=attribute_names
    )  # type: ignore
    return response.get('Attributes', {})  # type: ignore


def check_queue_health(queue_url: str) -> Dict[str, Any]:
    """Check queue health metrics for monitoring.

    Args:
        queue_url: URL of the SQS queue.

    Returns:
        Dictionary with queue health metrics.
    """
    try:
        attributes = get_queue_attributes(queue_url, [
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible',
            'ApproximateNumberOfMessagesDelayed'
        ])

        return {
            'queue_url': queue_url,
            'visible_messages': int(attributes.get('ApproximateNumberOfMessages', 0)),
            'in_flight_messages': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
            'delayed_messages': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
            'total_pending': int(attributes.get('ApproximateNumberOfMessages', 0)) +
                           int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)) +
                           int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
            'healthy': True
        }
    except Exception as e:
        return {
            'queue_url': queue_url,
            'error': str(e),
            'healthy': False
        }


__all__ = [
    "get_queue_url",
    "validate_message_size",
    "send_message",
    "validate_batch_messages",
    "send_bulk_messages",
    "get_queue_attributes",
    "check_queue_health"
]