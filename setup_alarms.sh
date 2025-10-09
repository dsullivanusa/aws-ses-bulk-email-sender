git #!/bin/bash
# Simple script to create all CloudWatch alarms

echo "🚨 Creating CloudWatch Alarms for Email Monitoring"
echo "=================================================="

REGION="us-gov-west-1"

# Replace these with your actual resource names
FUNCTION_NAME="email-worker-function"  # Change to your actual function name
QUEUE_NAME="bulk-email-queue"          # Change to your actual queue name  
DLQ_NAME="bulk-email-dlq"              # Change to your actual DLQ name

echo "Using function: $FUNCTION_NAME"
echo "Using queue: $QUEUE_NAME"
echo "Using DLQ: $DLQ_NAME"
echo ""

# Email Worker Function Alarms
echo "📊 Creating Email Worker Alarms..."

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-FunctionErrors \
  --alarm-description "Email Worker Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1.0 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-HighDuration \
  --alarm-description "Email Worker Lambda function taking too long" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 600000.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-NoActivity \
  --alarm-description "Email Worker Lambda function has no activity" \
  --metric-name Invocations \
  --namespace AWS/Lambda \
  --statistic Sum \
  --dimensions Name=FunctionName,Value=$FUNCTION_NAME \
  --period 600 \
  --evaluation-periods 3 \
  --threshold 1.0 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data breaching \
  --region $REGION

# Custom Metrics Alarms
echo "📈 Creating Custom Metrics Alarms..."

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-ThrottleExceptions \
  --alarm-description "Email Worker detected throttle exceptions" \
  --metric-name ThrottleExceptions \
  --namespace EmailWorker/Custom \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1.0 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-IncompleteCampaigns \
  --alarm-description "Email campaigns not completed within expected time" \
  --metric-name IncompleteCampaigns \
  --namespace EmailWorker/Custom \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1.0 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-HighAttachmentDelays \
  --alarm-description "High attachment delays detected" \
  --metric-name AttachmentDelays \
  --namespace EmailWorker/Custom \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

# Campaign Monitor Alarms
echo "🔍 Creating Campaign Monitor Alarms..."

aws cloudwatch put-metric-alarm \
  --alarm-name CampaignMonitor-StuckCampaigns \
  --alarm-description "Campaign Monitor detected stuck campaigns" \
  --metric-name StuckCampaigns \
  --namespace EmailWorker/CampaignMonitor \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

# SQS Queue Alarms
echo "📬 Creating SQS Queue Alarms..."

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-QueueBacklog \
  --alarm-description "SQS queue has too many messages" \
  --metric-name ApproximateNumberOfVisibleMessages \
  --namespace AWS/SQS \
  --statistic Average \
  --dimensions Name=QueueName,Value=$QUEUE_NAME \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 100.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-DLQMessages \
  --alarm-description "Dead Letter Queue has messages" \
  --metric-name ApproximateNumberOfVisibleMessages \
  --namespace AWS/SQS \
  --statistic Sum \
  --dimensions Name=QueueName,Value=$DLQ_NAME \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

echo ""
echo "✅ All CloudWatch alarms created successfully!"
echo ""
echo "🔍 Verify with: aws cloudwatch describe-alarms --region $REGION"
