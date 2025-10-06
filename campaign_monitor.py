#!/usr/bin/env python3
"""
Campaign Monitor Lambda Function
Monitors email campaigns for completion status and sends alerts for stuck campaigns
This can be run as a scheduled Lambda function or standalone script
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb', region_name='us-gov-west-1')
campaigns_table = dynamodb.Table('EmailCampaigns')
cloudwatch = boto3.client('cloudwatch', region_name='us-gov-west-1')

def check_stuck_campaigns():
    """Check for campaigns that appear to be stuck or incomplete"""
    
    logger.info("Starting campaign completion check...")
    
    # Get all active campaigns
    try:
        response = campaigns_table.scan(
            FilterExpression='#status IN (:processing, :sending)',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':processing': 'processing',
                ':sending': 'sending'
            }
        )
        
        campaigns = response['Items']
        logger.info(f"Found {len(campaigns)} active campaigns to check")
        
        stuck_campaigns = []
        current_time = datetime.now()
        
        for campaign in campaigns:
            campaign_id = campaign.get('campaign_id')
            campaign_name = campaign.get('campaign_name', 'Unnamed Campaign')
            
            # Convert Decimal types
            total_contacts = int(campaign.get('total_contacts', 0))
            sent_count = int(campaign.get('sent_count', 0))
            failed_count = int(campaign.get('failed_count', 0))
            
            # Calculate completion percentage
            total_processed = sent_count + failed_count
            if total_contacts > 0:
                completion_percentage = (total_processed / total_contacts) * 100
            else:
                completion_percentage = 100
            
            # Check if campaign is stuck
            is_stuck = False
            stuck_reason = ""
            
            # Check creation time
            created_at_str = campaign.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    time_since_creation = (current_time - created_at.replace(tzinfo=None)).total_seconds()
                    
                    # If campaign is older than 1 hour and less than 90% complete
                    if time_since_creation > 3600 and completion_percentage < 90:
                        is_stuck = True
                        stuck_reason = f"Created {time_since_creation/3600:.1f} hours ago, only {completion_percentage:.1f}% complete"
                    
                except Exception as e:
                    logger.warning(f"Error parsing created_at for campaign {campaign_id}: {str(e)}")
            
            # Check last activity (sent_at timestamp)
            sent_at_str = campaign.get('sent_at')
            if sent_at_str and not is_stuck:
                try:
                    sent_at = datetime.fromisoformat(sent_at_str.replace('Z', '+00:00'))
                    time_since_activity = (current_time - sent_at.replace(tzinfo=None)).total_seconds()
                    
                    # If no activity for more than 30 minutes
                    if time_since_activity > 1800:
                        is_stuck = True
                        stuck_reason = f"No activity for {time_since_activity/60:.1f} minutes"
                        
                except Exception as e:
                    logger.warning(f"Error parsing sent_at for campaign {campaign_id}: {str(e)}")
            
            if is_stuck:
                stuck_campaigns.append({
                    'campaign_id': campaign_id,
                    'campaign_name': campaign_name,
                    'total_contacts': total_contacts,
                    'sent_count': sent_count,
                    'failed_count': failed_count,
                    'completion_percentage': completion_percentage,
                    'stuck_reason': stuck_reason
                })
                
                logger.warning(f"Stuck campaign detected: {campaign_name} ({campaign_id})")
                logger.warning(f"  Reason: {stuck_reason}")
                logger.warning(f"  Progress: {sent_count + failed_count}/{total_contacts} ({completion_percentage:.1f}%)")
                
                # Send CloudWatch metric
                try:
                    cloudwatch.put_metric_data(
                        Namespace='EmailWorker/CampaignMonitor',
                        MetricData=[{
                            'MetricName': 'StuckCampaigns',
                            'Value': 1,
                            'Unit': 'Count',
                            'Timestamp': current_time,
                            'Dimensions': [
                                {'Name': 'CampaignId', 'Value': campaign_id},
                                {'Name': 'CampaignName', 'Value': campaign_name},
                                {'Name': 'CompletionPercentage', 'Value': f"{completion_percentage:.1f}"}
                            ]
                        }]
                    )
                except Exception as e:
                    logger.error(f"Failed to send CloudWatch metric for stuck campaign {campaign_id}: {str(e)}")
        
        logger.info(f"Campaign check complete. Found {len(stuck_campaigns)} stuck campaigns")
        
        return stuck_campaigns
        
    except Exception as e:
        logger.error(f"Error checking campaigns: {str(e)}")
        return []

def check_queue_health():
    """Check SQS queue health and send metrics"""
    
    logger.info("Checking SQS queue health...")
    
    try:
        sqs = boto3.client('sqs', region_name='us-gov-west-1')
        
        # Get queue URLs
        queues = sqs.list_queues()
        queue_metrics = {}
        
        for queue_url in queues.get('QueueUrls', []):
            queue_name = queue_url.split('/')[-1]
            
            if 'bulk-email' in queue_name:
                # Get queue attributes
                response = sqs.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
                )
                
                visible_messages = int(response['Attributes'].get('ApproximateNumberOfMessages', 0))
                in_flight_messages = int(response['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
                
                queue_metrics[queue_name] = {
                    'visible': visible_messages,
                    'in_flight': in_flight_messages,
                    'total': visible_messages + in_flight_messages
                }
                
                logger.info(f"Queue {queue_name}: {visible_messages} visible, {in_flight_messages} in-flight")
                
                # Send CloudWatch metrics
                current_time = datetime.now()
                
                cloudwatch.put_metric_data(
                    Namespace='EmailWorker/QueueHealth',
                    MetricData=[
                        {
                            'MetricName': 'QueueDepth',
                            'Value': visible_messages,
                            'Unit': 'Count',
                            'Timestamp': current_time,
                            'Dimensions': [
                                {'Name': 'QueueName', 'Value': queue_name},
                                {'Name': 'MessageType', 'Value': 'Visible'}
                            ]
                        },
                        {
                            'MetricName': 'QueueDepth',
                            'Value': in_flight_messages,
                            'Unit': 'Count',
                            'Timestamp': current_time,
                            'Dimensions': [
                                {'Name': 'QueueName', 'Value': queue_name},
                                {'Name': 'MessageType', 'Value': 'InFlight'}
                            ]
                        }
                    ]
                )
        
        return queue_metrics
        
    except Exception as e:
        logger.error(f"Error checking queue health: {str(e)}")
        return {}

def send_summary_metrics():
    """Send summary metrics about the email system"""
    
    logger.info("Sending summary metrics...")
    
    try:
        current_time = datetime.now()
        
        # Get campaign statistics
        response = campaigns_table.scan()
        campaigns = response['Items']
        
        total_campaigns = len(campaigns)
        active_campaigns = 0
        completed_campaigns = 0
        failed_campaigns = 0
        
        total_emails_sent = 0
        total_emails_failed = 0
        
        for campaign in campaigns:
            status = campaign.get('status', 'unknown')
            
            if status in ['processing', 'sending']:
                active_campaigns += 1
            elif status == 'completed':
                completed_campaigns += 1
            elif status == 'failed':
                failed_campaigns += 1
            
            total_emails_sent += int(campaign.get('sent_count', 0))
            total_emails_failed += int(campaign.get('failed_count', 0))
        
        # Send summary metrics
        cloudwatch.put_metric_data(
            Namespace='EmailWorker/Summary',
            MetricData=[
                {
                    'MetricName': 'TotalCampaigns',
                    'Value': total_campaigns,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'ActiveCampaigns',
                    'Value': active_campaigns,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'CompletedCampaigns',
                    'Value': completed_campaigns,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'TotalEmailsSent',
                    'Value': total_emails_sent,
                    'Unit': 'Count',
                    'Timestamp': current_time
                },
                {
                    'MetricName': 'TotalEmailsFailed',
                    'Value': total_emails_failed,
                    'Unit': 'Count',
                    'Timestamp': current_time
                }
            ]
        )
        
        logger.info(f"Summary metrics sent: {total_campaigns} campaigns, {active_campaigns} active, {completed_campaigns} completed")
        
    except Exception as e:
        logger.error(f"Error sending summary metrics: {str(e)}")

def lambda_handler(event, context):
    """Lambda handler for campaign monitoring"""
    
    logger.info("Starting campaign monitoring check...")
    
    try:
        # Check for stuck campaigns
        stuck_campaigns = check_stuck_campaigns()
        
        # Check queue health
        queue_metrics = check_queue_health()
        
        # Send summary metrics
        send_summary_metrics()
        
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'stuck_campaigns': len(stuck_campaigns),
                'queue_metrics': queue_metrics,
                'timestamp': datetime.now().isoformat()
            })
        }
        
        if stuck_campaigns:
            logger.warning(f"Found {len(stuck_campaigns)} stuck campaigns that may need attention")
            result['stuck_campaigns_details'] = stuck_campaigns
        
        return result
        
    except Exception as e:
        logger.error(f"Campaign monitoring failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def main():
    """Main function for standalone execution"""
    
    print("🔍 Campaign Monitor - Checking Email System Health")
    print("=" * 60)
    
    try:
        # Check for stuck campaigns
        stuck_campaigns = check_stuck_campaigns()
        
        if stuck_campaigns:
            print(f"\n⚠️ Found {len(stuck_campaigns)} stuck campaigns:")
            for campaign in stuck_campaigns:
                print(f"  📧 {campaign['campaign_name']} ({campaign['campaign_id']})")
                print(f"     Progress: {campaign['sent_count'] + campaign['failed_count']}/{campaign['total_contacts']} ({campaign['completion_percentage']:.1f}%)")
                print(f"     Reason: {campaign['stuck_reason']}")
        else:
            print("\n✅ No stuck campaigns found")
        
        # Check queue health
        queue_metrics = check_queue_health()
        
        if queue_metrics:
            print(f"\n📬 Queue Health:")
            for queue_name, metrics in queue_metrics.items():
                print(f"  {queue_name}: {metrics['visible']} visible, {metrics['in_flight']} in-flight")
        
        # Send summary metrics
        send_summary_metrics()
        
        print("\n✅ Campaign monitoring complete")
        
    except Exception as e:
        print(f"\n❌ Campaign monitoring failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
