#!/usr/bin/env python3
"""
Search Lambda CloudWatch Logs for Errors and Map to Source Code
Finds errors, extracts stack traces, and shows the relevant source code
"""

import boto3
import json
import sys
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

class LambdaErrorSearcher:
    def __init__(self, function_name, hours=1, region='us-gov-west-1'):
        self.function_name = function_name
        self.hours = hours
        self.region = region
        self.logs_client = boto3.client('logs', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.log_group_name = f"/aws/lambda/{function_name}"
        
    def get_log_events(self, filter_pattern=''):
        """Fetch log events from CloudWatch Logs"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.hours)
        
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        print(f"🔍 Searching logs from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Log group: {self.log_group_name}")
        print("=" * 80)
        
        events = []
        
        try:
            # Use filter_log_events for better performance
            response = self.logs_client.filter_log_events(
                logGroupName=self.log_group_name,
                startTime=start_timestamp,
                endTime=end_timestamp,
                filterPattern=filter_pattern
            )
            
            events.extend(response.get('events', []))
            
            # Handle pagination
            next_token = response.get('nextToken')
            while next_token:
                response = self.logs_client.filter_log_events(
                    logGroupName=self.log_group_name,
                    startTime=start_timestamp,
                    endTime=end_timestamp,
                    filterPattern=filter_pattern,
                    nextToken=next_token
                )
                events.extend(response.get('events', []))
                next_token = response.get('nextToken')
            
            events.sort(key=lambda x: x['timestamp'])
            return events
            
        except self.logs_client.exceptions.ResourceNotFoundException:
            print(f"❌ Log group not found: {self.log_group_name}")
            print(f"💡 Make sure the Lambda function has been invoked at least once.")
            return []
        except Exception as e:
            print(f"❌ Error fetching logs: {str(e)}")
            return []
    
    def extract_error_info(self, events):
        """Extract error information including file names and line numbers"""
        errors = []
        current_error = None
        
        # Patterns to match
        error_start_patterns = [
            r'❌ FATAL ERROR IN LAMBDA HANDLER',
            r'Task timed out after',
            r'Runtime exited with error',
            r'Exception Type:',
            r'Traceback \(most recent call last\)',
            r'\[ERROR\]',
            r'ERROR:',
        ]
        
        # Pattern to extract file and line number
        file_line_pattern = r'File "([^"]+)", line (\d+)'
        error_type_pattern = r'(\w+Error|\w+Exception):'
        
        for event in events:
            message = event['message']
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            
            # Check if this is the start of an error
            is_error_start = any(re.search(pattern, message, re.IGNORECASE) for pattern in error_start_patterns)
            
            if is_error_start or 'Traceback' in message or 'Exception' in message:
                if current_error is None:
                    current_error = {
                        'timestamp': timestamp,
                        'messages': [],
                        'files': [],
                        'error_type': None,
                        'error_message': None
                    }
                
                current_error['messages'].append(message)
                
                # Extract file and line number
                file_matches = re.findall(file_line_pattern, message)
                for file_path, line_num in file_matches:
                    # Clean up file path (remove /var/task/ prefix for Lambda)
                    clean_path = file_path.replace('/var/task/', '')
                    current_error['files'].append({
                        'file': clean_path,
                        'line': int(line_num)
                    })
                
                # Extract error type
                error_type_match = re.search(error_type_pattern, message)
                if error_type_match and not current_error['error_type']:
                    current_error['error_type'] = error_type_match.group(0)
                
                # Check for error message
                if ':' in message and not current_error['error_message']:
                    parts = message.split(':', 1)
                    if len(parts) > 1:
                        current_error['error_message'] = parts[1].strip()
            
            elif current_error is not None:
                # Check if this is a continuation of the error (indented or similar)
                if message.strip() and (message.startswith('  ') or message.startswith('\t')):
                    current_error['messages'].append(message)
                else:
                    # Error block ended
                    if current_error['files'] or current_error['error_type']:
                        errors.append(current_error)
                    current_error = None
        
        # Don't forget the last error
        if current_error is not None and (current_error['files'] or current_error['error_type']):
            errors.append(current_error)
        
        return errors
    
    def find_timeout_errors(self, events):
        """Find Lambda timeout errors"""
        timeouts = []
        for event in events:
            if 'Task timed out' in event['message']:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                timeouts.append({
                    'timestamp': timestamp,
                    'message': event['message'],
                    'type': 'TIMEOUT'
                })
        return timeouts
    
    def find_memory_errors(self, events):
        """Find out of memory errors"""
        memory_errors = []
        for event in events:
            message = event['message']
            if any(keyword in message.lower() for keyword in ['out of memory', 'memoryerror', 'runtime exited']):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                memory_errors.append({
                    'timestamp': timestamp,
                    'message': message,
                    'type': 'MEMORY'
                })
        return memory_errors
    
    def get_source_code_context(self, file_path, line_num, context_lines=5):
        """Get source code context around the error line"""
        # Try to find the file in the current directory
        possible_paths = [
            file_path,
            f"./{file_path}",
            os.path.join(os.getcwd(), file_path),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    start = max(0, line_num - context_lines - 1)
                    end = min(len(lines), line_num + context_lines)
                    
                    context = []
                    for i in range(start, end):
                        line_number = i + 1
                        prefix = ">>> " if line_number == line_num else "    "
                        context.append(f"{prefix}{line_number:4d} | {lines[i].rstrip()}")
                    
                    return {
                        'found': True,
                        'file': path,
                        'context': '\n'.join(context)
                    }
                except Exception as e:
                    print(f"⚠️  Error reading file {path}: {str(e)}")
        
        return {
            'found': False,
            'file': file_path,
            'context': None
        }
    
    def group_similar_errors(self, errors):
        """Group similar errors together"""
        grouped = defaultdict(list)
        
        for error in errors:
            # Create a key based on error type and primary file
            key_parts = []
            if error['error_type']:
                key_parts.append(error['error_type'])
            if error['files']:
                primary_file = error['files'][-1]  # Last file is usually the actual error location
                key_parts.append(f"{primary_file['file']}:{primary_file['line']}")
            
            key = ' | '.join(key_parts) if key_parts else 'Unknown Error'
            grouped[key].append(error)
        
        return grouped
    
    def print_error_report(self, errors, timeouts, memory_errors):
        """Print comprehensive error report"""
        print("\n" + "=" * 80)
        print("📊 ERROR SUMMARY")
        print("=" * 80)
        print(f"🔴 Stack Trace Errors: {len(errors)}")
        print(f"⏱️  Timeout Errors: {len(timeouts)}")
        print(f"💾 Memory Errors: {len(memory_errors)}")
        print(f"📈 Total Issues: {len(errors) + len(timeouts) + len(memory_errors)}")
        
        # Print timeout errors
        if timeouts:
            print("\n" + "=" * 80)
            print("⏱️  TIMEOUT ERRORS (Lambda Execution Timeout)")
            print("=" * 80)
            for idx, timeout in enumerate(timeouts, 1):
                print(f"\n[{idx}] {timeout['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    {timeout['message'].strip()}")
            print("\n💡 Solution: Increase Lambda timeout or optimize code performance")
        
        # Print memory errors
        if memory_errors:
            print("\n" + "=" * 80)
            print("💾 MEMORY ERRORS (Out of Memory)")
            print("=" * 80)
            for idx, mem_err in enumerate(memory_errors, 1):
                print(f"\n[{idx}] {mem_err['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    {mem_err['message'].strip()}")
            print("\n💡 Solution: Increase Lambda memory allocation")
        
        # Print and group stack trace errors
        if errors:
            grouped = self.group_similar_errors(errors)
            
            print("\n" + "=" * 80)
            print("🔴 STACK TRACE ERRORS WITH SOURCE CODE")
            print("=" * 80)
            
            for idx, (error_key, error_list) in enumerate(sorted(grouped.items()), 1):
                print(f"\n{'=' * 80}")
                print(f"ERROR GROUP #{idx}: {error_key}")
                print(f"Occurrences: {len(error_list)}")
                print(f"{'=' * 80}")
                
                # Show the most recent occurrence
                recent_error = error_list[-1]
                print(f"\n🕐 Most Recent: {recent_error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                if recent_error['error_type']:
                    print(f"🏷️  Error Type: {recent_error['error_type']}")
                
                if recent_error['error_message']:
                    print(f"💬 Message: {recent_error['error_message']}")
                
                # Show all timestamps for this error
                if len(error_list) > 1:
                    print(f"\n📅 All Occurrences:")
                    for err in error_list:
                        print(f"    - {err['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show stack trace with source code
                if recent_error['files']:
                    print(f"\n📍 Stack Trace (from top to bottom):")
                    for file_info in recent_error['files']:
                        print(f"\n  📄 File: {file_info['file']}, Line: {file_info['line']}")
                        
                        # Get source code context
                        code_context = self.get_source_code_context(
                            file_info['file'], 
                            file_info['line']
                        )
                        
                        if code_context['found']:
                            print(f"\n  Source Code Context:")
                            print("  " + "-" * 76)
                            for line in code_context['context'].split('\n'):
                                print(f"  {line}")
                            print("  " + "-" * 76)
                        else:
                            print(f"  ⚠️  Source file not found locally: {file_info['file']}")
                
                # Show full error message
                print(f"\n📝 Full Error Log:")
                print("  " + "-" * 76)
                for msg in recent_error['messages'][:10]:  # Limit to first 10 lines
                    for line in msg.split('\n'):
                        if line.strip():
                            print(f"  {line}")
                print("  " + "-" * 76)
    
    def search(self):
        """Main search function"""
        print("=" * 80)
        print("🔍 Lambda Error Search with Source Code Mapping")
        print("=" * 80)
        print(f"Function: {self.function_name}")
        print(f"Time Range: Last {self.hours} hour(s)")
        print(f"Region: {self.region}")
        print()
        
        # Get all log events
        events = self.get_log_events()
        
        if not events:
            print(f"\n✅ No log events found in the last {self.hours} hour(s)")
            return
        
        print(f"📦 Total log events: {len(events)}")
        
        # Extract different types of errors
        print("\n🔬 Analyzing errors...")
        errors = self.extract_error_info(events)
        timeouts = self.find_timeout_errors(events)
        memory_errors = self.find_memory_errors(events)
        
        # Print comprehensive report
        self.print_error_report(errors, timeouts, memory_errors)
        
        # Save to file option
        total_errors = len(errors) + len(timeouts) + len(memory_errors)
        if total_errors > 0:
            print("\n" + "=" * 80)
            print("💾 Save detailed report to file? (y/n)")
            save = input("> ").strip().lower()
            
            if save == 'y':
                filename = f"lambda_errors_{self.function_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    # Redirect print to file
                    import io
                    from contextlib import redirect_stdout
                    
                    f.write(f"Lambda Error Report\n")
                    f.write(f"Function: {self.function_name}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Time Range: Last {self.hours} hour(s)\n")
                    f.write("=" * 80 + "\n\n")
                    
                    # Write summary
                    f.write(f"Total Errors: {total_errors}\n")
                    f.write(f"  - Stack Trace Errors: {len(errors)}\n")
                    f.write(f"  - Timeout Errors: {len(timeouts)}\n")
                    f.write(f"  - Memory Errors: {len(memory_errors)}\n\n")
                    
                    # Write detailed errors
                    if errors:
                        grouped = self.group_similar_errors(errors)
                        for error_key, error_list in grouped.items():
                            f.write(f"\n{'=' * 80}\n")
                            f.write(f"ERROR: {error_key}\n")
                            f.write(f"Occurrences: {len(error_list)}\n")
                            f.write(f"{'=' * 80}\n\n")
                            
                            recent_error = error_list[-1]
                            for msg in recent_error['messages']:
                                f.write(msg + "\n")
                            
                            if recent_error['files']:
                                f.write("\nStack Trace:\n")
                                for file_info in recent_error['files']:
                                    f.write(f"  File: {file_info['file']}, Line: {file_info['line']}\n")
                                    code_context = self.get_source_code_context(
                                        file_info['file'], 
                                        file_info['line']
                                    )
                                    if code_context['found']:
                                        f.write("\n" + code_context['context'] + "\n\n")
                
                print(f"✅ Saved to {filename}")
        
        print("\n" + "=" * 80)
        print("✅ Error search complete!")


def list_lambda_functions():
    """List available Lambda functions"""
    lambda_client = boto3.client('lambda', region_name='us-gov-west-1')
    
    try:
        response = lambda_client.list_functions()
        functions = response['Functions']
        
        print("\n📋 Available Lambda Functions:")
        print("=" * 80)
        for idx, func in enumerate(functions, 1):
            print(f"{idx}. {func['FunctionName']}")
        
        return [f['FunctionName'] for f in functions]
    except Exception as e:
        print(f"❌ Error listing functions: {str(e)}")
        return []


def main():
    """Main function"""
    print("=" * 80)
    print("🔍 Lambda Error Search with Source Code Mapping")
    print("=" * 80)
    
    # Parse command line arguments
    function_name = None
    hours = 1
    region = 'us-gov-west-1'
    
    if len(sys.argv) > 1:
        function_name = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            hours = int(sys.argv[2])
        except ValueError:
            print("⚠️  Invalid hours value, using default (1 hour)")
    if len(sys.argv) > 3:
        region = sys.argv[3]
    
    # If no function specified, list available functions
    if not function_name:
        functions = list_lambda_functions()
        
        if not functions:
            print("❌ No Lambda functions found")
            return
        
        print(f"\n📝 Enter function number (1-{len(functions)}) or name:")
        user_input = input("> ").strip()
        
        try:
            idx = int(user_input) - 1
            if 0 <= idx < len(functions):
                function_name = functions[idx]
            else:
                print("❌ Invalid number")
                return
        except ValueError:
            function_name = user_input
    
    # Create searcher and run search
    searcher = LambdaErrorSearcher(function_name, hours, region)
    searcher.search()
    
    print("\n💡 Usage: python search_lambda_errors_with_code.py [function-name] [hours] [region]")
    print("   Example: python search_lambda_errors_with_code.py email-worker-function 24 us-gov-west-1")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

