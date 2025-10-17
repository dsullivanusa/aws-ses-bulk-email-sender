import boto3

lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
functions = lambda_client.list_functions()

print("Available Lambda functions:")
for func in functions['Functions']:
    print(f"- {func['FunctionName']}")