#!/usr/bin/env python3
"""
Find CloudWatch Error Metrics Script

This script searches CloudWatch logs for error metrics sent by the email worker Lambda function.
"""

import argparse
import json
import re
from datetime import datetime, timedelta

import boto3


def find_error_metrics_in_logs(log_group_name, hours_back=24, region="us-gov-west-1"):
    """
    Search CloudWatch logs for error metrics

    Args:
        log_group_name (str): CloudWatch log group name (e.g., '/aws/lambda/email-worker')
        hours_back (int): How many hours back to search
        region (str): AWS region
    """

    print(f"🔍 Searching CloudWatch Logs for Error Metrics")
    print("=" * 60)
    print(f"Log Group: {log_group_name}")
    print(f"Time Range: Last {hours_back} hours")
    print(f"Region: {region}")
    print()

    # Initialize CloudWatch Logs client
    try:
        logs_client = boto3.client("logs", region_name=region)
    except Exception as e:
        print(f"❌ Error connecting to CloudWatch: {str(e)}")
        return False

    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)

    # Convert to milliseconds since epoch
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)

    print(
        f"🕐 Searching from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print()

    # Define search queries for different error metrics
    queries = {
        "All Error Metrics": {
            "query": """
                fields @timestamp, @message, @requestId
                | filter @message like /📊 ERROR METRIC/
                | sort @timestamp desc
                | limit 100
            """,
            "description": "All error metrics sent to CloudWatch",
        },
        "Failed Emails": {
            "query": """
                fields @timestamp, @message, @requestId
                | filter @message like /EmailsFailed/
                | sort @timestamp desc
                | limit 50
            """,
            "description": "Failed email metrics",
        },
        "Throttle Exceptions": {
            "query": """
                fields @timestamp, @message, @requestId
                | filter @message like /ThrottleExceptions/
                | sort @timestamp desc
                | limit 50
            """,
            "description": "SES throttle/rate limit exceptions",
        },
        "Incomplete Campaigns": {
            "query": """
                fields @timestamp, @message, @requestId
                | filter @message like /IncompleteCampaigns/
                | sort @timestamp desc
                | limit 50
            """,
            "description": "Campaigns that didn't complete properly",
        },
        "CC Duplication Issues": {
            "query": """
                fields @timestamp, @message, @requestId
                | filter @message like /CC DUPLICATION DEBUG/ or @message like /EXCLUDING/ or @message like /duplicate/
                | sort @timestamp desc
                | limit 50
            """,
            "description": "CC duplication related messages",
        },
    }

    results = {}

    for query_name, query_info in queries.items():
        print(f"🔍 Running Query: {query_name}")
        print(f"   Description: {query_info['description']}")

        try:
            # Start the query
            response = logs_client.start_query(
                logGroupName=log_group_name,
                startTime=start_time_ms,
                endTime=end_time_ms,
                queryString=query_info["query"],
            )

            query_id = response["queryId"]

            # Wait for query to complete
            import time

            max_wait = 30  # seconds
            wait_time = 0

            while wait_time < max_wait:
                query_response = logs_client.get_query_results(queryId=query_id)

                if query_response["status"] == "Complete":
                    break
                elif query_response["status"] == "Failed":
                    print(f"   ❌ Query failed: {query_response.get('status')}")
                    break

                time.sleep(1)
                wait_time += 1

            if query_response["status"] == "Complete":
                query_results = query_response["results"]
                results[query_name] = query_results
                print(f"   ✅ Found {len(query_results)} results")
            else:
                print(f"   ⚠️  Query timed out or failed")
                results[query_name] = []

        except Exception as e:
            print(f"   ❌ Error running query: {str(e)}")
            results[query_name] = []

        print()

    # Display results
    print("📊 RESULTS SUMMARY")
    print("=" * 60)

    total_errors = 0
    for query_name, query_results in results.items():
        count = len(query_results)
        total_errors += count
        print(f"{query_name}: {count} results")

    print(f"\nTotal Error Events Found: {total_errors}")
    print()

    # Display detailed results
    for query_name, query_results in results.items():
        if query_results:
            print(f"📋 {query_name.upper()} - DETAILED RESULTS")
            print("-" * 50)

            for i, result in enumerate(query_results[:10], 1):  # Show first 10 results
                # Extract fields from result
                timestamp = ""
                message = ""
                request_id = ""

                for field in result:
                    if field["field"] == "@timestamp":
                        timestamp = field["value"]
                    elif field["field"] == "@message":
                        message = field["value"]
                    elif field["field"] == "@requestId":
                        request_id = field["value"]

                print(f"{i}. {timestamp}")
                if request_id:
                    print(f"   Request ID: {request_id}")
                print(f"   Message: {message}")
                print()

            if len(query_results) > 10:
                print(f"   ... and {len(query_results) - 10} more results")
                print()

    # Analysis and recommendations
    print("🔍 ANALYSIS & RECOMMENDATIONS")
    print("=" * 60)

    if results["Failed Emails"]:
        print("❌ FAILED EMAILS DETECTED:")
        print("   - Check for specific error messages in the logs")
        print("   - Look for patterns in failed email addresses")
        print("   - Consider deploying the CC duplication fix")
        print()

    if results["Throttle Exceptions"]:
        print("⚠️  THROTTLE EXCEPTIONS DETECTED:")
        print("   - SES rate limits are being exceeded")
        print("   - Consider reducing sending rate")
        print("   - Check SES sending limits in AWS console")
        print()

    if results["Incomplete Campaigns"]:
        print("📊 INCOMPLETE CAMPAIGNS DETECTED:")
        print("   - Some campaigns are not completing properly")
        print("   - Check for stuck processing or errors")
        print("   - Monitor campaign completion rates")
        print()

    if results["CC Duplication Issues"]:
        print("📧 CC DUPLICATION ACTIVITY DETECTED:")
        print("   - CC duplication debug logging is active")
        print("   - Check if CC recipients are being properly excluded")
        print("   - Verify the CC duplication fix is working")
        print()

    if total_errors == 0:
        print("✅ NO ERROR METRICS FOUND!")
        print("   - Your email system appears to be running smoothly")
        print("   - No CloudWatch error alarms should be triggered")
        print()

    return results


def save_results_to_file(results, filename="cloudwatch_error_metrics_results.json"):
    """Save results to a JSON file"""
    try:
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Results saved to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving results: {str(e)}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Find CloudWatch Error Metrics")
    parser.add_argument(
        "--log-group",
        required=True,
        help="CloudWatch log group name (e.g., /aws/lambda/email-worker)",
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="Hours back to search (default: 24)"
    )
    parser.add_argument(
        "--region", default="us-gov-west-1", help="AWS region (default: us-gov-west-1)"
    )
    parser.add_argument("--save", action="store_true", help="Save results to JSON file")

    args = parser.parse_args()

    # Run the search
    results = find_error_metrics_in_logs(
        log_group_name=args.log_group, hours_back=args.hours, region=args.region
    )

    # Save results if requested
    if args.save and results:
        save_results_to_file(results)

    print("🎯 NEXT STEPS:")
    print("1. Review the error messages above")
    print("2. Deploy the CC duplication fix if you see EmailsFailed")
    print("3. Check SES limits if you see ThrottleExceptions")
    print("4. Monitor campaigns if you see IncompleteCampaigns")
    print("5. Run this script again after fixes to verify improvements")


if __name__ == "__main__":
    # Example usage if run without arguments
    import sys

    if len(sys.argv) == 1:
        print("📋 USAGE EXAMPLES:")
        print(
            "python find_cloudwatch_error_metrics.py --log-group /aws/lambda/email-worker"
        )
        print(
            "python find_cloudwatch_error_metrics.py --log-group /aws/lambda/email-worker --hours 6"
        )
        print(
            "python find_cloudwatch_error_metrics.py --log-group /aws/lambda/email-worker --save"
        )
        print(
            "python find_cloudwatch_error_metrics.py --log-group /aws/lambda/email-worker --region us-east-1"
        )
        print()
        print("Replace 'email-worker' with your actual Lambda function name")
    else:
        main()
