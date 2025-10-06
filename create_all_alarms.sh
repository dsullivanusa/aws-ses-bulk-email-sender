#!/bin/bash
# Create all CloudWatch alarms for email monitoring system

echo "🚨 Creating CloudWatch Alarms for Email Monitoring System"
echo "========================================================="

# Set region
REGION="us-gov-west-1"

# Get the actual email worker function name
echo "🔍 Finding email worker function name..."
FUNCTION_NAME=$(aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `email-worker`)].FunctionName' --output text | head -n1)

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Could not find email worker function"
    exit 1
fi

echo "✅ Found email worker function: $FUNCTION_NAME"

# Get SQS queue names
echo "🔍 Finding SQS queue names..."
QUEUE_NAME=$(aws sqs list-queues --region $REGION --query 'QueueUrls[?contains(@, `bulk-email-queue`) && !contains(@, `dlq`)]' --output text | xargs basename)
DLQ_NAME=$(aws sqs list-queues --region $REGION --query 'QueueUrls[?contains(@, `bulk-email-dlq`) || contains(@, `dlq`)]' --output text | xargs basename)

echo "✅ Found main queue: $QUEUE_NAME"
echo "✅ Found DLQ: $DLQ_NAME"

echo ""
echo "📊 Creating Email Worker Function Alarms..."

# 1. Function Errors Alarm
echo "Creating EmailWorker-FunctionErrors..."
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

# 2. High Duration Alarm
echo "Creating EmailWorker-HighDuration..."
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

# 3. No Activity Alarm
echo "Creating EmailWorker-NoActivity..."
aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-NoActivity \
  --alarm-description "Email Worker Lambda function has no activity (potential stop)" \
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

echo ""
echo "📈 Creating Custom Metrics Alarms..."

# 4. Throttle Exceptions Alarm
echo "Creating EmailWorker-ThrottleExceptions..."
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

# 5. Incomplete Campaigns Alarm
echo "Creating EmailWorker-IncompleteCampaigns..."
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

# 6. High Attachment Delays Alarm
echo "Creating EmailWorker-HighAttachmentDelays..."
aws cloudwatch put-metric-alarm \
  --alarm-name EmailWorker-HighAttachmentDelays \
  --alarm-description "High attachment delays detected (large files)" \
  --metric-name AttachmentDelays \
  --namespace EmailWorker/Custom \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --region $REGION

echo ""
echo "🔍 Creating Campaign Monitor Alarms..."

# 7. Stuck Campaigns Alarm
echo "Creating CampaignMonitor-StuckCampaigns..."
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

echo ""
echo "📬 Creating SQS Queue Alarms..."

# 8. Queue Backlog Alarm
if [ ! -z "$QUEUE_NAME" ]; then
    echo "Creating EmailWorker-QueueBacklog for $QUEUE_NAME..."
    aws cloudwatch put-metric-alarm \
      --alarm-name EmailWorker-QueueBacklog \
      --alarm-description "SQS queue has too many messages (potential processing stop)" \
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
fi

# 9. Dead Letter Queue Alarm
if [ ! -z "$DLQ_NAME" ]; then
    echo "Creating EmailWorker-DLQMessages for $DLQ_NAME..."
    aws cloudwatch put-metric-alarm \
      --alarm-name EmailWorker-DLQMessages \
      --alarm-description "Dead Letter Queue has messages (email processing failures)" \
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
fi

echo ""
echo "✅ All CloudWatch alarms created successfully!"
echo ""
echo "🔍 Verify alarms with:"
echo "aws cloudwatch describe-alarms --region $REGION"
echo ""
echo "📊 View alarm states with:"
echo "aws cloudwatch describe-alarms --region $REGION --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue}' --output table"
