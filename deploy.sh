#!/bin/bash
# Deployment script for Bulk Email API with CSV Error Logging

set -e

echo "🚀 Deploying Bulk Email API with SAM..."
echo ""

# Check if AWS SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI is not installed."
    echo "Install it from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI is not configured or credentials are invalid."
    echo "Run: aws configure"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Build the SAM application
echo "📦 Building SAM application..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build successful"
echo ""

# Deploy the application
echo "🚢 Deploying to AWS..."
sam deploy \
    --stack-name bulk-email-api \
    --region us-gov-west-1 \
    --capabilities CAPABILITY_IAM \
    --resolve-s3 \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        Environment=production

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

echo ""
echo "✅ Deployment successful!"
echo ""

# Get the API URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name bulk-email-api \
    --region us-gov-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

LOG_CSV_ERROR_URL=$(aws cloudformation describe-stacks \
    --stack-name bulk-email-api \
    --region us-gov-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`LogCsvErrorEndpoint`].OutputValue' \
    --output text)

echo "📋 Deployment Information:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "API Base URL: $API_URL"
echo "CSV Error Logging Endpoint: $LOG_CSV_ERROR_URL"
echo ""
echo "Available Endpoints:"
echo "  - GET  $API_URL              (Web UI)"
echo "  - POST ${API_URL}log-csv-error  (Log CSV errors)"
echo "  - POST ${API_URL}contacts/batch (Batch upload)"
echo "  - POST ${API_URL}campaign       (Send campaign)"
echo "  - GET  ${API_URL}contacts       (List contacts)"
echo ""
echo "CloudWatch Logs:"
echo "  - Log Group: /aws/lambda/bulk-email-api-BulkEmailApiFunction-*"
echo "  - API Access Logs: /aws/apigateway/bulk-email-api-api"
echo ""
echo "🔍 To view logs:"
echo "   aws logs tail /aws/lambda/bulk-email-api-BulkEmailApiFunction-* --follow --region us-gov-west-1"
echo ""
echo "🧪 Test the CSV error endpoint:"
echo "   curl -X POST $LOG_CSV_ERROR_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"row\": 5, \"error\": \"Test error\", \"rawLine\": \"test,line,data\"}'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

