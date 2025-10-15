"""Unit tests for lib/dynamodb_utils.py.

Uses pytest and mocks for AWS calls.
"""
import pytest  # type: ignore
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
from lib.dynamodb_utils import (
    get_dynamodb_table,
    put_item,
    get_item,
    update_item,
    delete_item,
    scan_table,
    query_table,
    batch_write_items,
    batch_get_items,
    batch_delete_items,
    convert_decimals_to_json,
    prepare_item_for_dynamodb,
    get_table_item_count,
    table_exists,
    create_table,
    delete_table,
    describe_table,
    list_tables,
    update_table,
    wait_for_table_status,
    get_table_status,
    enable_table_backup,
    batch_write_with_retry,
    batch_delete_with_retry,
    batch_get_with_retry,
    is_throttling_error,
    is_conditional_check_error,
    is_validation_error,
    is_resource_not_found_error,
    retry_on_throttling,
    safe_dynamodb_operation
)


def test_get_dynamodb_table():
    """Test getting a DynamoDB table resource."""
    mock_client = MagicMock()
    mock_table = MagicMock()

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        mock_client.Table.return_value = mock_table
        table = get_dynamodb_table('test-table')
        assert table == mock_table
        mock_client.Table.assert_called_once_with('test-table')


def test_put_item():
    """Test putting an item into DynamoDB."""
    mock_table = MagicMock()
    mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        item = {'id': 'test', 'data': 'value'}
        response = put_item('test-table', item)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        mock_table.put_item.assert_called_once_with(Item=item)


def test_get_item():
    """Test getting an item from DynamoDB."""
    mock_table = MagicMock()
    mock_table.get_item.return_value = {'Item': {'id': 'test', 'data': 'value'}}

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        key = {'id': 'test'}
        item = get_item('test-table', key)
        assert item == {'id': 'test', 'data': 'value'}
        mock_table.get_item.assert_called_once_with(Key=key)


def test_get_item_not_found():
    """Test getting an item that doesn't exist."""
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        key = {'id': 'nonexistent'}
        item = get_item('test-table', key)
        assert item is None


def test_update_item():
    """Test updating an item in DynamoDB."""
    mock_table = MagicMock()
    mock_table.update_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        key = {'id': 'test'}
        response = update_item('test-table', key, 'SET #data = :val', {':val': 'new_value'}, {'#data': 'data'})
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        mock_table.update_item.assert_called_once()


def test_delete_item():
    """Test deleting an item from DynamoDB."""
    mock_table = MagicMock()
    mock_table.delete_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        key = {'id': 'test'}
        response = delete_item('test-table', key)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        mock_table.delete_item.assert_called_once_with(Key=key)


def test_scan_table():
    """Test scanning a DynamoDB table."""
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        'Items': [{'id': '1'}, {'id': '2'}],
        'LastEvaluatedKey': {'id': '2'}
    }

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        items, last_key = scan_table('test-table', limit=10)
        assert len(items) == 2
        assert last_key == {'id': '2'}
        mock_table.scan.assert_called_once()


def test_query_table():
    """Test querying a DynamoDB table."""
    mock_table = MagicMock()
    mock_table.query.return_value = {
        'Items': [{'id': '1'}, {'id': '2'}],
        'LastEvaluatedKey': {'id': '2'}
    }

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        items, last_key = query_table('test-table', 'id = :id', {':id': 'test'})
        assert len(items) == 2
        assert last_key == {'id': '2'}
        mock_table.query.assert_called_once()


def test_batch_write_items():
    """Test batch writing items to DynamoDB."""
    mock_table = MagicMock()

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        items = [{'id': '1'}, {'id': '2'}]
        response = batch_write_items('test-table', items)
        assert response == {'UnprocessedItems': {}}


def test_batch_write_items_too_many():
    """Test batch write with too many items."""
    items = [{'id': str(i)} for i in range(26)]  # 26 items

    with pytest.raises(ValueError, match="Batch write cannot exceed 25 items"):  # type: ignore
        batch_write_items('test-table', items)


def test_batch_get_items():
    """Test batch getting items from DynamoDB."""
    mock_table = MagicMock()
    mock_table.batch_get_item.return_value = {
        'Responses': {
            'test-table': [{'id': '1'}, {'id': '2'}]
        }
    }

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        keys = [{'id': '1'}, {'id': '2'}]
        items = batch_get_items('test-table', keys)
        assert len(items) == 2
        mock_table.batch_get_item.assert_called_once()


def test_batch_get_items_too_many():
    """Test batch get with too many keys."""
    keys = [{'id': str(i)} for i in range(101)]  # 101 keys

    with pytest.raises(ValueError, match="Batch get cannot exceed 100 items"):  # type: ignore
        batch_get_items('test-table', keys)


def test_batch_delete_items():
    """Test batch deleting items from DynamoDB."""
    mock_table = MagicMock()

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        keys = [{'id': '1'}, {'id': '2'}]
        response = batch_delete_items('test-table', keys)
        assert response == {'UnprocessedItems': {}}


def test_batch_delete_items_too_many():
    """Test batch delete with too many keys."""
    keys = [{'id': str(i)} for i in range(26)]  # 26 keys

    with pytest.raises(ValueError, match="Batch delete cannot exceed 25 items"):  # type: ignore
        batch_delete_items('test-table', keys)


def test_convert_decimals_to_json():
    """Test converting Decimal objects to JSON-serializable types."""
    # Test Decimal to int
    assert convert_decimals_to_json(Decimal('5')) == 5

    # Test Decimal to float
    assert convert_decimals_to_json(Decimal('5.5')) == 5.5

    # Test nested structures
    data: Dict[str, Any] = {
        'count': Decimal('10'),
        'price': Decimal('19.99'),
        'items': [Decimal('1'), Decimal('2.5')],
        'nested': {'value': Decimal('100')}
    }
    result = convert_decimals_to_json(data)
    assert result['count'] == 10
    assert result['price'] == 19.99
    assert result['items'] == [1, 2.5]
    assert result['nested']['value'] == 100


def test_prepare_item_for_dynamodb():
    """Test preparing an item for DynamoDB operations."""
    item: Dict[str, Any] = {
        'id': 'test',
        'count': Decimal('5'),
        'price': Decimal('10.99')
    }
    prepared = prepare_item_for_dynamodb(item)
    assert prepared['count'] == 5
    assert prepared['price'] == 10.99


def test_get_table_item_count():
    """Test getting table item count."""
    mock_table = MagicMock()
    mock_table.scan.return_value = {'Count': 42}

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        count = get_table_item_count('test-table')
        assert count == 42
        mock_table.scan.assert_called_once_with(Select='COUNT')


def test_table_exists():
    """Test checking if a table exists."""
    mock_table = MagicMock()

    with patch('lib.dynamodb_utils.get_dynamodb_table', return_value=mock_table):
        exists = table_exists('test-table')
        assert exists is True


def test_table_exists_not_found():
    """Test checking if a table doesn't exist."""
    with patch('lib.dynamodb_utils.get_dynamodb_table', side_effect=Exception('Table not found')):
        exists = table_exists('nonexistent-table')
        assert exists is False


def test_create_table():
    """Test creating a DynamoDB table."""
    mock_client = MagicMock()
    mock_client.create_table.return_value = {'TableDescription': {'TableName': 'test-table'}}

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        key_schema = [{'AttributeName': 'id', 'KeyType': 'HASH'}]
        attr_defs = [{'AttributeName': 'id', 'AttributeType': 'S'}]

        response = create_table('test-table', key_schema, attr_defs)
        assert response['TableDescription']['TableName'] == 'test-table'
        mock_client.create_table.assert_called_once()


def test_delete_table():
    """Test deleting a DynamoDB table."""
    mock_client = MagicMock()
    mock_client.delete_table.return_value = {'TableDescription': {'TableName': 'test-table'}}

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        response = delete_table('test-table')
        assert response['TableDescription']['TableName'] == 'test-table'
        mock_client.delete_table.assert_called_once_with(TableName='test-table')


def test_describe_table():
    """Test describing a DynamoDB table."""
    mock_client = MagicMock()
    mock_client.describe_table.return_value = {
        'Table': {
            'TableName': 'test-table',
            'TableStatus': 'ACTIVE'
        }
    }

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        response = describe_table('test-table')
        assert response['Table']['TableName'] == 'test-table'
        assert response['Table']['TableStatus'] == 'ACTIVE'
        mock_client.describe_table.assert_called_once_with(TableName='test-table')


def test_list_tables():
    """Test listing DynamoDB tables."""
    mock_client = MagicMock()
    mock_client.list_tables.return_value = {
        'TableNames': ['table1', 'table2'],
        'LastEvaluatedTableName': 'table2'
    }

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        tables, last_key = list_tables(limit=10)
        assert tables == ['table1', 'table2']
        assert last_key == 'table2'
        mock_client.list_tables.assert_called_once_with(Limit=10)


def test_update_table():
    """Test updating a DynamoDB table."""
    mock_client = MagicMock()
    mock_client.update_table.return_value = {'TableDescription': {'TableName': 'test-table'}}

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        response = update_table('test-table', billing_mode='PAY_PER_REQUEST')
        assert response['TableDescription']['TableName'] == 'test-table'
        mock_client.update_table.assert_called_once()


def test_get_table_status():
    """Test getting table status."""
    with patch('lib.dynamodb_utils.describe_table') as mock_describe:
        mock_describe.return_value = {'Table': {'TableStatus': 'ACTIVE'}}
        status = get_table_status('test-table')
        assert status == 'ACTIVE'
        mock_describe.assert_called_once_with('test-table')


def test_get_table_status_not_found():
    """Test getting status of non-existent table."""
    with patch('lib.dynamodb_utils.describe_table', side_effect=Exception('Table not found')):
        status = get_table_status('nonexistent-table')
        assert status is None


def test_enable_table_backup():
    """Test enabling table backup."""
    mock_client = MagicMock()
    mock_client.create_backup.return_value = {'BackupDetails': {'BackupName': 'test-backup'}}

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        response = enable_table_backup('test-table', 'test-backup')
        assert response['BackupDetails']['BackupName'] == 'test-backup'
        mock_client.create_backup.assert_called_once()


def test_wait_for_table_status():
    """Test waiting for table status."""
    with patch('lib.dynamodb_utils.describe_table') as mock_describe:
        mock_describe.return_value = {'Table': {'TableStatus': 'ACTIVE'}}

        result = wait_for_table_status('test-table', 'ACTIVE', timeout=1)
        assert result is True
        mock_describe.assert_called_once_with('test-table')


def test_batch_write_with_retry_success():
    """Test batch write with retry - success on first attempt."""
    mock_client = MagicMock()
    mock_client.batch_write_item.return_value = {'UnprocessedItems': {}}

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        items = [{'id': '1', 'data': 'test1'}, {'id': '2', 'data': 'test2'}]
        result = batch_write_with_retry('test-table', items)

        assert result['processed_count'] == 2
        assert result['unprocessed_items'] == []
        mock_client.batch_write_item.assert_called_once()


def test_batch_write_with_retry_unprocessed():
    """Test batch write with retry - handles unprocessed items."""
    mock_client = MagicMock()
    # First call returns unprocessed items, second call succeeds
    mock_client.batch_write_item.side_effect = [
        {'UnprocessedItems': {'test-table': [{'PutRequest': {'Item': {'id': '1', 'data': 'test1'}}}]}},
        {'UnprocessedItems': {}}
    ]

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client), \
         patch('time.sleep') as mock_sleep:
        items = [{'id': '1', 'data': 'test1'}, {'id': '2', 'data': 'test2'}]
        result = batch_write_with_retry('test-table', items, max_retries=1)

        assert result['processed_count'] == 2
        assert result['unprocessed_items'] == []
        assert mock_client.batch_write_item.call_count == 2
        mock_sleep.assert_called_once()


def test_batch_delete_with_retry_success():
    """Test batch delete with retry - success on first attempt."""
    mock_client = MagicMock()
    mock_client.batch_write_item.return_value = {'UnprocessedItems': {}}

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        keys = [{'id': '1'}, {'id': '2'}]
        result = batch_delete_with_retry('test-table', keys)

        assert result['processed_count'] == 2
        assert result['unprocessed_keys'] == []
        mock_client.batch_write_item.assert_called_once()


def test_batch_get_with_retry_success():
    """Test batch get with retry - success on first attempt."""
    mock_client = MagicMock()
    mock_client.batch_get_item.return_value = {
        'Responses': {'test-table': [{'id': '1', 'data': 'test1'}]},
        'UnprocessedKeys': {}
    }

    with patch('lib.dynamodb_utils.get_dynamodb_client', return_value=mock_client):
        keys = [{'id': '1'}]
        result = batch_get_with_retry('test-table', keys)

        assert len(result) == 1
        assert result[0]['id'] == '1'
        mock_client.batch_get_item.assert_called_once()


def test_is_throttling_error():
    """Test throttling error detection."""
    throttling_errors: List[Exception] = [
        Exception("Throttling exception"),
        Exception("Throughput exceeded"),
        Exception("Rate exceeded"),
        Exception("ProvisionedThroughputExceeded")
    ]

    for error in throttling_errors:
        assert is_throttling_error(error)

    non_throttling_errors: List[Exception] = [
        Exception("Validation error"),
        Exception("Resource not found"),
        ValueError("Invalid input")
    ]

    for error in non_throttling_errors:
        assert not is_throttling_error(error)


def test_is_conditional_check_error():
    """Test conditional check error detection."""
    conditional_errors = [
        Exception("ConditionalCheckFailed"),
        Exception("Conditional check failed")
    ]

    for error in conditional_errors:
        assert is_conditional_check_error(error)

    non_conditional_errors = [
        Exception("Throttling error"),
        Exception("Validation error")
    ]

    for error in non_conditional_errors:
        assert not is_conditional_check_error(error)


def test_is_validation_error():
    """Test validation error detection."""
    validation_errors = [
        Exception("Validation exception"),
        Exception("Invalid parameter"),
        Exception("Malformed request")
    ]

    for error in validation_errors:
        assert is_validation_error(error)

    non_validation_errors = [
        Exception("Throttling error"),
        Exception("Resource not found")
    ]

    for error in non_validation_errors:
        assert not is_validation_error(error)


def test_is_resource_not_found_error():
    """Test resource not found error detection."""
    not_found_errors = [
        Exception("Resource not found"),
        Exception("Table does not exist"),
        Exception("Not found")
    ]

    for error in not_found_errors:
        assert is_resource_not_found_error(error)

    found_errors = [
        Exception("Throttling error"),
        Exception("Validation error")
    ]

    for error in found_errors:
        assert not is_resource_not_found_error(error)


def test_retry_on_throttling_decorator():
    """Test retry on throttling decorator."""
    call_count = 0

    @retry_on_throttling(max_retries=2, base_delay=0.01)
    def failing_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Throttling exception")
        return "success"

    with patch('time.sleep') as mock_sleep:
        result = failing_function()
        assert result == "success"
        assert call_count == 3
        assert mock_sleep.call_count == 2


def test_safe_dynamodb_operation_success():
    """Test safe DynamoDB operation - success case."""
    def mock_operation():
        return "success"

    result, error = safe_dynamodb_operation(mock_operation)
    assert result == "success"
    assert error is None


def test_safe_dynamodb_operation_throttling_retry():
    """Test safe DynamoDB operation - throttling with retry."""
    call_count = 0

    def mock_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Throttling exception")
        return "success"

    with patch('time.sleep') as mock_sleep:
        result, error = safe_dynamodb_operation(mock_operation, max_retries=1, base_delay=0.01)
        assert result == "success"
        assert error is None
        assert call_count == 2
        mock_sleep.assert_called_once()


def test_safe_dynamodb_operation_validation_error():
    """Test safe DynamoDB operation - validation error (no retry)."""
    def mock_operation():
        raise Exception("Validation exception")

    result, error = safe_dynamodb_operation(mock_operation)
    assert result is None
    assert error == "Validation exception"