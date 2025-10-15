"""DynamoDB-specific utilities for table operations.

This module handles DynamoDB operations like CRUD, batch operations,
and data conversion. It uses lib/aws_clients for client management.
"""
import time
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from lib.aws_clients import get_dynamodb_client


def get_dynamodb_table(table_name: str) -> Any:
    """Get a DynamoDB table resource.

    Args:
        table_name: Name of the DynamoDB table.

    Returns:
        DynamoDB table resource.

    Raises:
        Exception: If table doesn't exist or other DynamoDB errors.
    """
   
    dynamodb = get_dynamodb_client()
    return dynamodb.Table(table_name)  # type: ignore


def put_item(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Put an item into a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        item: Item to put into the table.

    Returns:
        DynamoDB response dict.

    Raises:
        Exception: For DynamoDB errors.
    """
   
    table = get_dynamodb_table(table_name)
    response = table.put_item(Item=item)  # type: ignore
    return response  # type: ignore


def get_item(table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get an item from a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        key: Primary key of the item to retrieve.

    Returns:
        Item dict if found, None if not found.

    Raises:
        Exception: For DynamoDB errors.
    """
   
    table = get_dynamodb_table(table_name)
    response = table.get_item(Key=key)  # type: ignore
    return response.get('Item')  # type: ignore


def update_item(
    table_name: str,
    key: Dict[str, Any],
    update_expression: str,
    expression_attribute_values: Optional[Dict[str, Any]] = None,
    expression_attribute_names: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Update an item in a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        key: Primary key of the item to update.
        update_expression: DynamoDB update expression.
        expression_attribute_values: Values for the update expression.
        expression_attribute_names: Names for the update expression.

    Returns:
        DynamoDB response dict.

    Raises:
        Exception: For DynamoDB errors.
    """
   
    table = get_dynamodb_table(table_name)
    update_params: Dict[str, Any] = {
        'Key': key,
        'UpdateExpression': update_expression
    }

    if expression_attribute_values:
        update_params['ExpressionAttributeValues'] = expression_attribute_values
    if expression_attribute_names:
        update_params['ExpressionAttributeNames'] = expression_attribute_names

    response = table.update_item(**update_params)  # type: ignore
    return response  # type: ignore


def delete_item(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an item from a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        key: Primary key of the item to delete.

    Returns:
        DynamoDB response dict.

    Raises:
        Exception: For DynamoDB errors.
    """
   
    table = get_dynamodb_table(table_name)
    response = table.delete_item(Key=key)  # type: ignore
    return response  # type: ignore


def scan_table(
    table_name: str,
    filter_expression: Optional[str] = None,
    expression_attribute_values: Optional[Dict[str, Any]] = None,
    expression_attribute_names: Optional[Dict[str, str]] = None,
    limit: Optional[int] = None,
    exclusive_start_key: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Scan a DynamoDB table with optional filtering and pagination.

    Args:
        table_name: Name of the DynamoDB table.
        filter_expression: DynamoDB filter expression.
        expression_attribute_values: Values for the filter expression.
        expression_attribute_names: Names for the filter expression.
        limit: Maximum number of items to return.
        exclusive_start_key: Key to start scanning from for pagination.

    Returns:
        Tuple of (items list, last_evaluated_key for pagination).

    Raises:
        Exception: For DynamoDB errors.
    """
    
    table = get_dynamodb_table(table_name)
    scan_params: Dict[str, Any] = {}

    if filter_expression:
        scan_params['FilterExpression'] = filter_expression
    if expression_attribute_values:
        scan_params['ExpressionAttributeValues'] = expression_attribute_values
    if expression_attribute_names:
        scan_params['ExpressionAttributeNames'] = expression_attribute_names
    if limit:
        scan_params['Limit'] = limit
    if exclusive_start_key:
        scan_params['ExclusiveStartKey'] = exclusive_start_key

    response = table.scan(**scan_params)  # type: ignore
    return response['Items'], response.get('LastEvaluatedKey')  # type: ignore


def query_table(
    table_name: str,
    key_condition_expression: str,
    expression_attribute_values: Optional[Dict[str, Any]] = None,
    expression_attribute_names: Optional[Dict[str, str]] = None,
    filter_expression: Optional[str] = None,
    limit: Optional[int] = None,
    exclusive_start_key: Optional[Dict[str, Any]] = None,
    scan_index_forward: bool = True
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Query a DynamoDB table with key conditions and optional filtering.

    Args:
        table_name: Name of the DynamoDB table.
        key_condition_expression: DynamoDB key condition expression.
        expression_attribute_values: Values for expressions.
        expression_attribute_names: Names for expressions.
        filter_expression: DynamoDB filter expression.
        limit: Maximum number of items to return.
        exclusive_start_key: Key to start querying from for pagination.
        scan_index_forward: Sort order for range keys.

    Returns:
        Tuple of (items list, last_evaluated_key for pagination).

    Raises:
        Exception: For DynamoDB errors.
    """

    table = get_dynamodb_table(table_name)
    query_params: Dict[str, Any] = {
        'KeyConditionExpression': key_condition_expression
    }

    if expression_attribute_values:
        query_params['ExpressionAttributeValues'] = expression_attribute_values
    if expression_attribute_names:
        query_params['ExpressionAttributeNames'] = expression_attribute_names
    if filter_expression:
        query_params['FilterExpression'] = filter_expression
    if limit:
        query_params['Limit'] = limit
    if exclusive_start_key:
        query_params['ExclusiveStartKey'] = exclusive_start_key
    if not scan_index_forward:
        query_params['ScanIndexForward'] = scan_index_forward

    response = table.query(**query_params)  # type: ignore
    return response['Items'], response.get('LastEvaluatedKey')  # type: ignore


def batch_write_items(table_name: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Batch write items to a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        items: List of items to write.

    Returns:
        DynamoDB response dict with batch results.

    Raises:
        ValueError: If batch exceeds DynamoDB limits.
        Exception: For DynamoDB errors.
    """
  
    if len(items) > 25:
        raise ValueError(f"Batch write cannot exceed 25 items, got {len(items)}")

    table = get_dynamodb_table(table_name)

    with table.batch_writer() as batch:  # type: ignore
        for item in items:
            batch.put_item(Item=item)

    # Return success response (batch_writer doesn't return response)
    return {'UnprocessedItems': {}}


def batch_get_items(table_name: str, keys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Batch get items from a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        keys: List of primary keys to retrieve.

    Returns:
        List of retrieved items.

    Raises:
        ValueError: If batch exceeds DynamoDB limits.
        Exception: For DynamoDB errors.
    """
 
    if len(keys) > 100:
        raise ValueError(f"Batch get cannot exceed 100 items, got {len(keys)}")

    table = get_dynamodb_table(table_name)
    response = table.batch_get_item(RequestItems={table_name: {'Keys': keys}})  # type: ignore
    return response['Responses'][table_name]  # type: ignore


def batch_delete_items(table_name: str, keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Batch delete items from a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.
        keys: List of primary keys to delete.

    Returns:
        DynamoDB response dict with batch results.

    Raises:
        ValueError: If batch exceeds DynamoDB limits.
        Exception: For DynamoDB errors.
    """
  
    if len(keys) > 25:
        raise ValueError(f"Batch delete cannot exceed 25 items, got {len(keys)}")

    table = get_dynamodb_table(table_name)

    with table.batch_writer() as batch:  # type: ignore
        for key in keys:
            batch.delete_item(Key=key)

    # Return success response (batch_writer doesn't return response)
    return {'UnprocessedItems': {}}


def convert_decimals_to_json(obj: Any) -> Any:
    """Convert Decimal objects to JSON-serializable types.

    Args:
        obj: Object that may contain Decimal values.

    Returns:
        Object with Decimal values converted to int/float.
    """
 
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, list):
        return [convert_decimals_to_json(item) for item in obj]  # type: ignore
    elif isinstance(obj, dict):
        return {str(key): convert_decimals_to_json(value) for key, value in obj.items()}  # type: ignore
    else:
        return obj


def prepare_item_for_dynamodb(item: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare an item for DynamoDB by handling special data types.

    Args:
        item: Item dict to prepare.

    Returns:
        Item dict ready for DynamoDB operations.
    """

    # Convert any nested structures and handle special types
    return convert_decimals_to_json(item)


def get_table_item_count(table_name: str) -> int:
 
    """Get the approximate item count for a DynamoDB table.

    Args:
        table_name: Name of the DynamoDB table.

    Returns:
        Approximate number of items in the table.

    Raises:
        Exception: For DynamoDB errors.
    """
    table = get_dynamodb_table(table_name)
    response = table.scan(Select='COUNT')  # type: ignore
    return response['Count']  # type: ignore


def table_exists(table_name: str) -> bool:

    """Check if a DynamoDB table exists.

    Args:
        table_name: Name of the DynamoDB table.

    Returns:
        True if table exists, False otherwise.
    """
    try:
        table = get_dynamodb_table(table_name)
        table.load()  # This will raise an exception if table doesn't exist
        return True
    except Exception:
        return False


def create_table(
    table_name: str,
    key_schema: List[Dict[str, str]],
    attribute_definitions: List[Dict[str, str]],
    billing_mode: str = 'PAY_PER_REQUEST',
    provisioned_throughput: Optional[Dict[str, int]] = None,
    global_secondary_indexes: Optional[List[Dict[str, Any]]] = None,
    local_secondary_indexes: Optional[List[Dict[str, Any]]] = None,
    stream_specification: Optional[Dict[str, Any]] = None,
    tags: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Create a new DynamoDB table.

    Args:
        table_name: Name of the table to create.
        key_schema: List of key schema elements (partition/sort keys).
        attribute_definitions: List of attribute definitions for keys.
        billing_mode: 'PAY_PER_REQUEST' or 'PROVISIONED'.
        provisioned_throughput: Read/write capacity units (for PROVISIONED mode).
        global_secondary_indexes: List of GSI definitions.
        local_secondary_indexes: List of LSI definitions.
        stream_specification: Stream configuration.
        tags: List of tags to apply to the table.

    Returns:
        DynamoDB response dict with table description.

    Raises:
        Exception: For DynamoDB errors.
    """
 
    dynamodb = get_dynamodb_client()

    create_params: Dict[str, Any] = {
        'TableName': table_name,
        'KeySchema': key_schema,
        'AttributeDefinitions': attribute_definitions,
        'BillingMode': billing_mode
    }

    if provisioned_throughput and billing_mode == 'PROVISIONED':
        create_params['ProvisionedThroughput'] = provisioned_throughput

    if global_secondary_indexes:
        create_params['GlobalSecondaryIndexes'] = global_secondary_indexes

    if local_secondary_indexes:
        create_params['LocalSecondaryIndexes'] = local_secondary_indexes

    if stream_specification:
        create_params['StreamSpecification'] = stream_specification

    if tags:
        create_params['Tags'] = tags

    response = dynamodb.create_table(**create_params)  # type: ignore
    return response  # type: ignore


def delete_table(table_name: str) -> Dict[str, Any]:
    """Delete a DynamoDB table.

    Args:
        table_name: Name of the table to delete.

    Returns:
        DynamoDB response dict.

    Raises:
        Exception: For DynamoDB errors.
    """
 
    dynamodb = get_dynamodb_client()
    response = dynamodb.delete_table(TableName=table_name)  # type: ignore
    return response  # type: ignore


def describe_table(table_name: str) -> Dict[str, Any]:
 
    """Get detailed information about a DynamoDB table.

    Args:
        table_name: Name of the table to describe.

    Returns:
        DynamoDB table description.

    Raises:
        Exception: For DynamoDB errors.
    """
    dynamodb = get_dynamodb_client()
    response = dynamodb.describe_table(TableName=table_name)  # type: ignore
    return response  # type: ignore


def list_tables(exclusive_start_table_name: Optional[str] = None, limit: Optional[int] = None) -> Tuple[List[str], Optional[str]]:
    """List DynamoDB tables.

    Args:
        exclusive_start_table_name: Table name to start listing from.
        limit: Maximum number of tables to return.

    Returns:
        Tuple of (table names list, last_evaluated_table_name for pagination).

    Raises:
        Exception: For DynamoDB errors.
    """
 
    dynamodb = get_dynamodb_client()
    list_params: Dict[str, Any] = {}

    if exclusive_start_table_name:
        list_params['ExclusiveStartTableName'] = exclusive_start_table_name
    if limit:
        list_params['Limit'] = limit

    response = dynamodb.list_tables(**list_params)  # type: ignore
    return response['TableNames'], response.get('LastEvaluatedTableName')  # type: ignore


def update_table(
    table_name: str,
    attribute_definitions: Optional[List[Dict[str, str]]] = None,
    billing_mode: Optional[str] = None,
    provisioned_throughput: Optional[Dict[str, int]] = None,
    global_secondary_indexes: Optional[List[Dict[str, Any]]] = None,
    stream_specification: Optional[Dict[str, Any]] = None,
    sse_specification: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Update a DynamoDB table configuration.

    Args:
        table_name: Name of the table to update.
        attribute_definitions: New attribute definitions.
        billing_mode: New billing mode.
        provisioned_throughput: New provisioned throughput.
        global_secondary_indexes: Updated GSI configurations.
        stream_specification: Updated stream configuration.
        sse_specification: Server-side encryption configuration.

    Returns:
        DynamoDB response dict with table description.

    Raises:
        Exception: For DynamoDB errors.
    """
  
    dynamodb = get_dynamodb_client()
    update_params: Dict[str, Any] = {
        'TableName': table_name
    }

    if attribute_definitions:
        update_params['AttributeDefinitions'] = attribute_definitions
    if billing_mode:
        update_params['BillingMode'] = billing_mode
    if provisioned_throughput:
        update_params['ProvisionedThroughput'] = provisioned_throughput
    if global_secondary_indexes:
        update_params['GlobalSecondaryIndexes'] = global_secondary_indexes
    if stream_specification:
        update_params['StreamSpecification'] = stream_specification
    if sse_specification:
        update_params['SSESpecification'] = sse_specification

    response = dynamodb.update_table(**update_params)  # type: ignore
    return response  # type: ignore


def wait_for_table_status(table_name: str, status: str, timeout: int = 300) -> bool:
    """Wait for a table to reach a specific status.

    Args:
        table_name: Name of the table to wait for.
        status: Target status ('ACTIVE', 'CREATING', 'UPDATING', 'DELETING').
        timeout: Maximum time to wait in seconds.

    Returns:
        True if table reached the status, False if timeout.

    Raises:
        Exception: For DynamoDB errors.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            table_desc = describe_table(table_name)
            current_status = table_desc['Table']['TableStatus']

            if current_status == status:
                return True

            time.sleep(5)  # Wait 5 seconds before checking again

        except Exception as e:
            # Table might not exist yet during creation
            if status == 'ACTIVE':
                time.sleep(5)
                continue
            else:
                raise e

    return False


def get_table_status(table_name: str) -> Optional[str]:
    """Get the current status of a DynamoDB table.

    Args:
        table_name: Name of the table.

    Returns:
        Table status string or None if table doesn't exist.
    """
    
    try:
        table_desc = describe_table(table_name)
        return table_desc['Table']['TableStatus']
    except Exception:
        return None


def enable_table_backup(table_name: str, backup_name: str) -> Dict[str, Any]:
    """Enable point-in-time recovery for a table.

    Args:
        table_name: Name of the table.
        backup_name: Name for the backup.

    Returns:
        DynamoDB response dict.

    Raises:
        Exception: For DynamoDB errors.
    """
  
    dynamodb = get_dynamodb_client()
    response = dynamodb.create_backup(  # type: ignore
        TableName=table_name,
        BackupName=backup_name
    )
    return response  # type: ignore


def batch_write_with_retry(
    table_name: str,
    items: List[Dict[str, Any]],
    max_retries: int = 3,
    base_delay: float = 0.1
) -> Dict[str, Any]:
    """Batch write items with automatic retry for unprocessed items.

    Args:
        table_name: Name of the DynamoDB table.
        items: List of items to write.
        max_retries: Maximum number of retry attempts for unprocessed items.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        Dict with 'processed_count' and 'unprocessed_items'.

    Raises:
        Exception: For DynamoDB errors after all retries.
    """
    if len(items) > 25:
        raise ValueError(f"Batch write cannot exceed 25 items, got {len(items)}")

    dynamodb = get_dynamodb_client()
    request_items = {table_name: [{'PutRequest': {'Item': item}} for item in items]}

    for attempt in range(max_retries + 1):
        try:
            response = dynamodb.batch_write_item(RequestItems=request_items)  # type: ignore

            unprocessed = response.get('UnprocessedItems', {})
            if not unprocessed or not unprocessed.get(table_name):
                return {
                    'processed_count': len(items),
                    'unprocessed_items': []
                }

            # Prepare for retry with unprocessed items
            unprocessed_items = unprocessed[table_name]
            request_items = {table_name: unprocessed_items}

            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

        except Exception as e:
            if attempt == max_retries:
                raise e
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

    # If we get here, we still have unprocessed items
    unprocessed_count = len(request_items[table_name])  # type: ignore
    return {
        'processed_count': len(items) - unprocessed_count,
        'unprocessed_items': [item['PutRequest']['Item'] for item in request_items[table_name]]  # type: ignore
    }


def batch_delete_with_retry(
    table_name: str,
    keys: List[Dict[str, Any]],
    max_retries: int = 3,
    base_delay: float = 0.1
) -> Dict[str, Any]:
    """Batch delete items with automatic retry for unprocessed items.

    Args:
        table_name: Name of the DynamoDB table.
        keys: List of primary keys to delete.
        max_retries: Maximum number of retry attempts for unprocessed items.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        Dict with 'processed_count' and 'unprocessed_keys'.

    Raises:
        Exception: For DynamoDB errors after all retries.
    """
    if len(keys) > 25:
        raise ValueError(f"Batch delete cannot exceed 25 items, got {len(keys)}")

    dynamodb = get_dynamodb_client()
    request_items = {table_name: [{'DeleteRequest': {'Key': key}} for key in keys]}

    for attempt in range(max_retries + 1):
        try:
            response = dynamodb.batch_write_item(RequestItems=request_items)  # type: ignore

            unprocessed = response.get('UnprocessedItems', {})
            if not unprocessed or not unprocessed.get(table_name):
                return {
                    'processed_count': len(keys),
                    'unprocessed_keys': []
                }

            # Prepare for retry with unprocessed items
            unprocessed_items = unprocessed[table_name]
            request_items = {table_name: unprocessed_items}

            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

        except Exception as e:
            if attempt == max_retries:
                raise e
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

    # If we get here, we still have unprocessed items
    unprocessed_count = len(request_items[table_name])  # type: ignore
    return {
        'processed_count': len(keys) - unprocessed_count,
        'unprocessed_keys': [item['DeleteRequest']['Key'] for item in request_items[table_name]]  # type: ignore
    }


def batch_get_with_retry(
    table_name: str,
    keys: List[Dict[str, Any]],
    max_retries: int = 3,
    base_delay: float = 0.1
) -> List[Dict[str, Any]]:
    """Batch get items with automatic retry for unprocessed keys.

    Args:
        table_name: Name of the DynamoDB table.
        keys: List of primary keys to retrieve.
        max_retries: Maximum number of retry attempts for unprocessed keys.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        List of retrieved items.

    Raises:
        Exception: For DynamoDB errors after all retries.
    """
    if len(keys) > 100:
        raise ValueError(f"Batch get cannot exceed 100 items, got {len(keys)}")

    dynamodb = get_dynamodb_client()
    request_items = {table_name: {'Keys': keys}}

    all_items = []

    for attempt in range(max_retries + 1):
        try:
            response = dynamodb.batch_get_item(RequestItems=request_items)  # type: ignore

            # Collect items from this response
            items = response.get('Responses', {}).get(table_name, [])  # type: ignore
            all_items.extend(items)  # type: ignore

            # Check for unprocessed keys
            unprocessed = response.get('UnprocessedKeys', {})  # type: ignore
            if not unprocessed or not unprocessed.get(table_name, {}).get('Keys'):  # type: ignore
                break

            # Prepare for retry with unprocessed keys
            request_items = unprocessed  # type: ignore

            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

        except Exception as e:
            if attempt == max_retries:
                raise e
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

    return all_items  # type: ignore


def is_throttling_error(error: Exception) -> bool:
    """Check if an exception is a DynamoDB throttling error.

    Args:
        error: Exception to check.

    Returns:
        True if the error is a throttling error.
    """
    error_message = str(error).lower()
    throttling_indicators = [
        'throttling',
        'throughput exceeded',
        'rate exceeded',
        'provisionedthroughputexceeded',
        'throttlingexception',
        'limit exceeded'
    ]
    return any(indicator in error_message for indicator in throttling_indicators)


def is_conditional_check_error(error: Exception) -> bool:
    """Check if an exception is a DynamoDB conditional check failure.

    Args:
        error: Exception to check.

    Returns:
        True if the error is a conditional check failure.
    """
    error_message = str(error).lower()
    return 'conditionalcheckfailed' in error_message or 'conditional check failed' in error_message


def is_validation_error(error: Exception) -> bool:
    """Check if an exception is a DynamoDB validation error.

    Args:
        error: Exception to check.

    Returns:
        True if the error is a validation error.
    """
    error_message = str(error).lower()
    validation_indicators = [
        'validation',
        'validationexception',
        'invalid',
        'malformed'
    ]
    return any(indicator in error_message for indicator in validation_indicators)


def is_resource_not_found_error(error: Exception) -> bool:
    """Check if an exception is a DynamoDB resource not found error.

    Args:
        error: Exception to check.

    Returns:
        True if the error is a resource not found error.
    """
    error_message = str(error).lower()
    return 'not found' in error_message or 'resource not found' in error_message or 'does not exist' in error_message


def retry_on_throttling(
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 30.0
) -> Any:
    """Decorator to retry DynamoDB operations on throttling errors with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds for exponential backoff.
        max_delay: Maximum delay between retries.

    Returns:
        Decorator function.
    """
    def decorator(func: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries or not is_throttling_error(e):
                        raise e

                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


def safe_dynamodb_operation(
    operation_func: Any,
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 0.1,
    **kwargs: Any
) -> Tuple[Any, Optional[str]]:
    """Execute a DynamoDB operation with error handling and optional retry.

    Args:
        operation_func: The DynamoDB operation function to execute.
        *args: Positional arguments for the operation.
        max_retries: Maximum retries for throttling errors.
        base_delay: Base delay for exponential backoff.
        **kwargs: Keyword arguments for the operation.

    Returns:
        Tuple of (result, error_message). Result is None if error occurred.
    """
    for attempt in range(max_retries + 1):
        try:
            result = operation_func(*args, **kwargs)
            return result, None
        except Exception as e:
            error_msg = str(e)

            # Don't retry for certain errors
            if is_conditional_check_error(e) or is_validation_error(e) or is_resource_not_found_error(e):
                return None, error_msg

            # Retry throttling errors
            if attempt < max_retries and is_throttling_error(e):
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue

            # Max retries reached or non-retryable error
            return None, error_msg

    return None, "Max retries exceeded"


__all__ = [
    "get_dynamodb_table",
    "put_item",
    "get_item",
    "update_item",
    "delete_item",
    "scan_table",
    "query_table",
    "batch_write_items",
    "batch_get_items",
    "batch_delete_items",
    "convert_decimals_to_json",
    "prepare_item_for_dynamodb",
    "get_table_item_count",
    "table_exists",
    "create_table",
    "delete_table",
    "describe_table",
    "list_tables",
    "update_table",
    "wait_for_table_status",
    "get_table_status",
    "enable_table_backup",
    "batch_write_with_retry",
    "batch_delete_with_retry",
    "batch_get_with_retry",
    "is_throttling_error",
    "is_conditional_check_error",
    "is_validation_error",
    "is_resource_not_found_error",
    "retry_on_throttling",
    "safe_dynamodb_operation"
]