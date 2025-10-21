# PowerShell Deployment script for Bulk Email API with CSV Error Logging

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Bulk Email API with SAM..." -ForegroundColor Cyan
Write-Host ""

# Check if AWS SAM CLI is installed
if (!(Get-Command sam -ErrorAction SilentlyContinue)) {
    Write-Host "❌ AWS SAM CLI is not installed." -ForegroundColor Red
    Write-Host "Install it from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
}

# Check if AWS CLI is configured
try {
    aws sts get-caller-identity | Out-Null
} catch {
    Write-Host "❌ AWS CLI is not configured or credentials are invalid." -ForegroundColor Red
    Write-Host "Run: aws configure"
    exit 1
}

Write-Host "✅ Prerequisites check passed" -ForegroundColor Green
Write-Host ""

# Build the SAM application
Write-Host "📦 Building SAM application..." -ForegroundColor Yellow
sam build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build successful" -ForegroundColor Green
Write-Host ""

# Deploy the application
Write-Host "🚢 Deploying to AWS..." -ForegroundColor Yellow
sam deploy `
    --stack-name bulk-email-api `
    --region us-gov-west-1 `
    --capabilities CAPABILITY_IAM `
    --resolve-s3 `
    --no-fail-on-empty-changeset `
    --parameter-overrides Environment=production

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Deployment successful!" -ForegroundColor Green
Write-Host ""

# Get the API URL
$API_URL = aws cloudformation describe-stacks `
    --stack-name bulk-email-api `
    --region us-gov-west-1 `
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' `
    --output text

$LOG_CSV_ERROR_URL = aws cloudformation describe-stacks `
    --stack-name bulk-email-api `
    --region us-gov-west-1 `
    --query 'Stacks[0].Outputs[?OutputKey==`LogCsvErrorEndpoint`].OutputValue' `
    --output text

Write-Host "📋 Deployment Information:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "API Base URL: $API_URL" -ForegroundColor White
Write-Host "CSV Error Logging Endpoint: $LOG_CSV_ERROR_URL" -ForegroundColor White
Write-Host ""
Write-Host "Available Endpoints:"
Write-Host "  - GET  $API_URL              (Web UI)"
Write-Host "  - POST ${API_URL}log-csv-error  (Log CSV errors)"
Write-Host "  - POST ${API_URL}contacts/batch (Batch upload)"
Write-Host "  - POST ${API_URL}campaign       (Send campaign)"
Write-Host "  - GET  ${API_URL}contacts       (List contacts)"
Write-Host ""
Write-Host "CloudWatch Logs:"
Write-Host "  - Log Group: /aws/lambda/bulk-email-api-BulkEmailApiFunction-*"
Write-Host "  - API Access Logs: /aws/apigateway/bulk-email-api-api"
Write-Host ""
Write-Host "🔍 To view logs:"
Write-Host "   aws logs tail /aws/lambda/bulk-email-api-BulkEmailApiFunction-* --follow --region us-gov-west-1"
Write-Host ""
Write-Host "🧪 Test the CSV error endpoint:"
Write-Host "   Invoke-WebRequest -Method POST -Uri '$LOG_CSV_ERROR_URL' ``"
Write-Host "     -ContentType 'application/json' ``"
Write-Host "     -Body '{\"row\": 5, \"error\": \"Test error\", \"rawLine\": \"test,line,data\"}'"
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

