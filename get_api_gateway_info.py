#!/usr/bin/env python3
"""
Get API Gateway Information
Display details about existing API Gateway
"""

import boto3
import json

REGION = 'us-gov-west-1'
API_NAME = 'bulk-email-api'

def get_api_info(api_id=None):
    """Get API Gateway information"""
    apigateway = boto3.client('apigateway', region_name=REGION)
    
    try:
        # If no API ID provided, search by name
        if not api_id:
            response = apigateway.get_rest_apis(limit=500)
            apis = response.get('items', [])
            
            # Find API by name
            matching_apis = [api for api in apis if API_NAME in api['name'].lower()]
            
            if not matching_apis:
                print(f"❌ No API Gateway found with name containing: {API_NAME}")
                return None
            
            if len(matching_apis) > 1:
                print(f"Found {len(matching_apis)} APIs matching '{API_NAME}':")
                for i, api in enumerate(matching_apis, 1):
                    print(f"  {i}. {api['name']} ({api['id']})")
                
                choice = input("\nSelect API (1-{len(matching_apis)}): ").strip()
                api = matching_apis[int(choice) - 1]
            else:
                api = matching_apis[0]
            
            api_id = api['id']
        else:
            api = apigateway.get_rest_api(restApiId=api_id)
        
        # Get resources
        resources_response = apigateway.get_resources(restApiId=api_id, limit=500)
        resources = resources_response.get('items', [])
        
        # Get deployments
        deployments_response = apigateway.get_deployments(restApiId=api_id)
        deployments = deployments_response.get('items', [])
        
        # Get stages
        stages_response = apigateway.get_stages(restApiId=api_id)
        stages = stages_response.get('item', [])
        
        print("\n" + "="*80)
        print("API GATEWAY INFORMATION")
        print("="*80)
        print(f"\nAPI ID:       {api['id']}")
        print(f"API Name:     {api['name']}")
        print(f"Description:  {api.get('description', 'N/A')}")
        print(f"Created:      {api.get('createdDate', 'N/A')}")
        print(f"Region:       {REGION}")
        
        # Display stages
        if stages:
            print(f"\n" + "-"*80)
            print("STAGES:")
            print("-"*80)
            for stage in stages:
                stage_name = stage['stageName']
                api_url = f"https://{api['id']}.execute-api.{REGION}.amazonaws.com/{stage_name}"
                print(f"\nStage: {stage_name}")
                print(f"  URL:     {api_url}")
                print(f"  Deployed: {stage.get('createdDate', 'N/A')}")
        
        # Display resources/endpoints
        print(f"\n" + "-"*80)
        print(f"ENDPOINTS ({len(resources)} resources):")
        print("-"*80)
        
        for resource in sorted(resources, key=lambda x: x.get('path', '')):
            path = resource.get('path', '/')
            methods = resource.get('resourceMethods', {})
            
            if methods:
                for method in sorted(methods.keys()):
                    if method != 'OPTIONS':  # Skip CORS
                        stage_name = stages[0]['stageName'] if stages else 'prod'
                        full_url = f"https://{api['id']}.execute-api.{REGION}.amazonaws.com/{stage_name}{path}"
                        print(f"{method:<8} {full_url}")
        
        print("\n" + "="*80)
        
        # Save to file
        info = {
            'api_id': api['id'],
            'api_name': api['name'],
            'region': REGION,
            'resources': len(resources),
            'deployments': len(deployments),
            'stages': [s['stageName'] for s in stages] if stages else []
        }
        
        if stages:
            stage_name = stages[0]['stageName']
            info['api_url'] = f"https://{api['id']}.execute-api.{REGION}.amazonaws.com/{stage_name}"
        
        with open('current_api_info.json', 'w') as f:
            json.dump(info, f, indent=2)
        
        print(f"\nInformation saved to: current_api_info.json")
        print("="*80)
        
        return info
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    import sys
    
    api_id = sys.argv[1] if len(sys.argv) > 1 else None
    get_api_info(api_id)

if __name__ == '__main__':
    main()

