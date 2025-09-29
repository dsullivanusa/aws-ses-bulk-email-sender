import boto3
from datetime import datetime, timedelta

def check_lambda_logs():
    logs_client = boto3.client('logs', region_name='us-gov-west-1')
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    # Get Lambda functions
    functions = lambda_client.list_functions()
    function_names = [f['FunctionName'] for f in functions['Functions']]
    
    # Find web UI function
    web_ui_functions = [name for name in function_names if 'web' in name.lower()]
    
    if not web_ui_functions:
        print("No web UI Lambda function found")
        return
    
    function_name = web_ui_functions[0]
    log_group_name = f'/aws/lambda/{function_name}'
    
    print(f"Checking logs for {function_name}...")
    
    try:
        # Get recent log events
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000)
        )
        
        print("Recent log events:")
        for event in response['events'][-10:]:  # Last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"{timestamp}: {event['message']}")
            
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    check_lambda_logs()