"""Unit tests for lib/sqs_utils.py.

Uses pytest and mocks for AWS calls.
"""
import json
import pytest  # type: ignore
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from lib.sqs_utils import (
    get_queue_url,
    validate_message_size,
    send_message,
    validate_batch_messages,
    send_bulk_messages,
    get_queue_attributes,
    check_queue_health
)


def test_get_queue_url():
    """Test getting queue URL."""
    mock_sqs = MagicMock()
    mock_sqs.get_queue_url.return_value = {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'}

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        url = get_queue_url('test-queue')
        assert url == 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
        mock_sqs.get_queue_url.assert_called_once_with(QueueName='test-queue')


def test_send_message_basic():
    """Test sending a basic message."""
    mock_sqs = MagicMock()
    mock_sqs.send_message.return_value = {'MessageId': 'test-msg-id'}

    message_body = {'campaign_id': 'test-123', 'contact_email': 'test@example.com'}

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        response = send_message('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue', message_body)
        assert response['MessageId'] == 'test-msg-id'

        # Verify the call
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args
        assert call_args[1]['QueueUrl'] == 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
        assert json.loads(call_args[1]['MessageBody']) == message_body


def test_send_message_with_attributes():
    """Test sending a message with attributes."""
    mock_sqs = MagicMock()
    mock_sqs.send_message.return_value = {'MessageId': 'test-msg-id'}

    message_body = {'campaign_id': 'test-123', 'contact_email': 'test@example.com'}
    message_attributes = {
        'campaign_id': {'StringValue': 'test-123', 'DataType': 'String'},
        'priority': {'StringValue': 'high', 'DataType': 'String'}
    }

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        response = send_message(
            'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue',
            message_body,
            message_attributes
        )
        assert response['MessageId'] == 'test-msg-id'

        # Verify the call includes attributes
        call_args = mock_sqs.send_message.call_args
        assert call_args[1]['MessageAttributes'] == message_attributes


def test_send_bulk_messages():
    """Test sending multiple messages in batch."""
    mock_sqs = MagicMock()
    mock_sqs.send_message_batch.return_value = {
        'Successful': [
            {'Id': '0', 'MessageId': 'msg-1'},
            {'Id': '1', 'MessageId': 'msg-2'}
        ],
        'Failed': []
    }

    messages: List[Dict[str, Any]] = [
        {
            'body': {'campaign_id': 'test-123', 'contact_email': 'user1@example.com'},
            'attributes': {'priority': {'StringValue': 'high', 'DataType': 'String'}}
        },
        {
            'body': {'campaign_id': 'test-123', 'contact_email': 'user2@example.com'}
        }
    ]

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        response = send_bulk_messages('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue', messages)

        assert len(response['Successful']) == 2
        assert response['Successful'][0]['MessageId'] == 'msg-1'
        assert response['Successful'][1]['MessageId'] == 'msg-2'

        # Verify the batch call
        mock_sqs.send_message_batch.assert_called_once()
        call_args = mock_sqs.send_message_batch.call_args
        assert call_args[1]['QueueUrl'] == 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'

        entries = call_args[1]['Entries']
        assert len(entries) == 2
        assert json.loads(entries[0]['MessageBody']) == messages[0]['body']
        assert entries[0]['MessageAttributes'] == messages[0]['attributes']
        assert json.loads(entries[1]['MessageBody']) == messages[1]['body']


def test_send_bulk_messages_partial_failure():
    """Test bulk send with some failures."""
    mock_sqs = MagicMock()
    mock_sqs.send_message_batch.return_value = {
        'Successful': [
            {'Id': '0', 'MessageId': 'msg-1'}
        ],
        'Failed': [
            {'Id': '1', 'SenderFault': True, 'Code': 'InvalidParameterValue', 'Message': 'Invalid message'}
        ]
    }

    messages = [
        {'body': {'campaign_id': 'test-123', 'contact_email': 'user1@example.com'}},
        {'body': {'campaign_id': 'test-123', 'contact_email': 'user2@example.com'}}
    ]

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        response = send_bulk_messages('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue', messages)

        assert len(response['Successful']) == 1
        assert len(response['Failed']) == 1
        assert response['Failed'][0]['Code'] == 'InvalidParameterValue'


def test_validate_message_size_valid():
    """Test message size validation for valid messages."""
    message_body = {'campaign_id': 'test-123', 'contact_email': 'test@example.com'}
    is_valid, error_msg = validate_message_size(message_body)
    assert is_valid
    assert error_msg == ""


def test_validate_message_size_too_large():
    """Test message size validation for oversized messages."""
    # Create a message larger than 256KB
    large_data = 'x' * (300 * 1024)  # 300KB
    message_body = {'data': large_data}

    is_valid, error_msg = validate_message_size(message_body)
    assert not is_valid
    assert "exceeds SQS limit" in error_msg


def test_validate_message_size_too_many_attributes():
    """Test validation with too many message attributes."""
    message_body = {'test': 'data'}
    message_attributes = {f'attr{i}': {'StringValue': f'value{i}', 'DataType': 'String'} for i in range(15)}

    is_valid, error_msg = validate_message_size(message_body, message_attributes)
    assert not is_valid
    assert "Too many message attributes" in error_msg


def test_validate_message_size_attribute_too_long():
    """Test validation with oversized attribute name/value."""
    message_body = {'test': 'data'}
    message_attributes = {
        'x' * 300: {'StringValue': 'test', 'DataType': 'String'}  # Name too long
    }

    is_valid, error_msg = validate_message_size(message_body, message_attributes)
    assert not is_valid
    assert "attribute name" in error_msg and "too long" in error_msg


def test_send_message_size_validation_failure():
    """Test that send_message validates size and fails appropriately."""
    # Create oversized message
    large_data = 'x' * (300 * 1024)  # 300KB
    message_body = {'data': large_data}

    with pytest.raises(ValueError, match="exceeds SQS limit"):  # type: ignore
        send_message('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue', message_body)


def test_validate_batch_messages_valid():
    """Test batch validation for valid messages."""
    messages = [
        {'body': {'campaign_id': 'test-123', 'contact_email': 'user1@example.com'}},
        {'body': {'campaign_id': 'test-123', 'contact_email': 'user2@example.com'}}
    ]

    is_valid, error_msg = validate_batch_messages(messages)
    assert is_valid
    assert error_msg == ""


def test_validate_batch_messages_too_many():
    """Test batch validation with too many messages."""
    messages = [{'body': {'test': 'data'}} for _ in range(15)]  # 15 messages

    is_valid, error_msg = validate_batch_messages(messages)
    assert not is_valid
    assert "Too many messages in batch" in error_msg


def test_validate_batch_messages_total_size_too_large():
    """Test batch validation with total size exceeding limit."""
    # Create messages that individually are OK but collectively too large
    large_data = 'x' * (100 * 1024)  # 100KB each
    messages = [
        {'body': {'data': large_data}},
        {'body': {'data': large_data}},
        {'body': {'data': large_data}}  # Total ~300KB
    ]

    is_valid, error_msg = validate_batch_messages(messages)
    assert not is_valid
    assert "Total batch size" in error_msg and "exceeds SQS limit" in error_msg


def test_send_bulk_messages_validation_failure():
    """Test that send_bulk_messages validates and fails appropriately."""
    # Create batch with too many messages
    messages = [{'body': {'test': 'data'}} for _ in range(15)]

    with pytest.raises(ValueError, match="Too many messages in batch"):  # type: ignore
        send_bulk_messages('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue', messages)


def test_get_queue_attributes():
    """Test getting queue attributes."""
    mock_sqs = MagicMock()
    mock_sqs.get_queue_attributes.return_value = {
        'Attributes': {
            'ApproximateNumberOfMessages': '5',
            'VisibilityTimeout': '300'
        }
    }

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        attributes = get_queue_attributes('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue', ['ApproximateNumberOfMessages', 'VisibilityTimeout'])

        assert attributes['ApproximateNumberOfMessages'] == '5'
        assert attributes['VisibilityTimeout'] == '300'

        mock_sqs.get_queue_attributes.assert_called_once()


def test_check_queue_health():
    """Test queue health checking."""
    mock_sqs = MagicMock()
    mock_sqs.get_queue_attributes.return_value = {
        'Attributes': {
            'ApproximateNumberOfMessages': '10',
            'ApproximateNumberOfMessagesNotVisible': '2',
            'ApproximateNumberOfMessagesDelayed': '1'
        }
    }

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        health = check_queue_health('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue')

        assert health['healthy'] is True
        assert health['visible_messages'] == 10
        assert health['in_flight_messages'] == 2
        assert health['delayed_messages'] == 1
        assert health['total_pending'] == 13


def test_check_queue_health_error():
    """Test queue health checking with error."""
    mock_sqs = MagicMock()
    mock_sqs.get_queue_attributes.side_effect = Exception("Queue not found")

    with patch('lib.sqs_utils.get_sqs_client', return_value=mock_sqs):
        health = check_queue_health('https://sqs.us-east-1.amazonaws.com/123456789012/test-queue')

        assert health['healthy'] is False
        assert 'error' in health
        assert 'Queue not found' in health['error']