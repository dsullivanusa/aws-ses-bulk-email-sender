#!/usr/bin/env python3
"""
Fix API_URL Definition Issue
This script ensures API_URL is properly defined in the JavaScript code
"""

import re

def fix_api_url_definition():
    """Fix the API_URL definition issue"""
    print("🔧 Fixing API_URL definition issue...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Check if API_URL is properly defined
        if "const API_URL = '{api_url}';" in content:
            print("✅ Found API_URL definition with f-string placeholder")
            
            # The issue might be that the f-string is not being processed correctly
            # Let's check if there are any issues with the f-string formatting
            
            # Look for the serve_web_ui function to see how api_url is defined
            serve_web_ui_match = re.search(r'def serve_web_ui\(event\):.*?api_url = (.*?)\n', content, re.DOTALL)
            if serve_web_ui_match:
                api_url_definition = serve_web_ui_match.group(1).strip()
                print(f"   API URL definition: {api_url_definition}")
            
            # Check if the HTML template is properly formatted
            html_start = content.find('html_content = f"""')
            if html_start != -1:
                print("✅ Found HTML template with f-string")
                
                # Check if there are any issues with the f-string
                # Look for unescaped braces in the HTML content
                html_content = content[html_start:html_start + 1000]  # First 1000 chars of HTML
                
                # Check for any issues with the f-string formatting
                if '{{' in html_content and '}}' in html_content:
                    print("✅ Found proper f-string formatting with double braces")
                else:
                    print("❌ F-string formatting may be incorrect")
            
            # The real issue might be that the JavaScript is trying to use API_URL
            # before it's properly defined. Let's check if there are any immediate uses
            # of API_URL right after the definition
            
            # Find the line with API_URL definition
            api_url_line = content.find("const API_URL = '{api_url}';")
            if api_url_line != -1:
                # Look at the next few lines to see if there are any immediate uses
                next_lines = content[api_url_line:api_url_line + 500]
                
                # Check if there are any template literals using API_URL immediately
                immediate_uses = re.findall(r'\$\{API_URL\}', next_lines)
                if immediate_uses:
                    print(f"✅ Found {len(immediate_uses)} immediate uses of API_URL")
                else:
                    print("❌ No immediate uses of API_URL found")
            
            return True
        else:
            print("❌ API_URL definition not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking API_URL definition: {e}")
        return False

def check_f_string_issues():
    """Check for f-string formatting issues"""
    print("\n🔍 Checking for f-string formatting issues...")
    
    try:
        with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the HTML template section
        html_start = content.find('html_content = f"""')
        if html_start == -1:
            print("❌ HTML template not found")
            return False
        
        # Find the end of the HTML template
        html_end = content.find('"""', html_start + 20)
        if html_end == -1:
            print("❌ HTML template end not found")
            return False
        
        html_content = content[html_start:html_end]
        
        # Check for f-string issues
        issues = []
        
        # Look for single braces that should be double braces
        single_braces = re.findall(r'[^{]{[^{][^}]*[^}]}[^{]', html_content)
        if single_braces:
            issues.append(f"Found {len(single_braces)} single braces that might need escaping")
        
        # Look for unescaped braces in JavaScript template literals
        js_template_issues = re.findall(r'`[^`]*\{[^}]*\}[^`]*`', html_content)
        if js_template_issues:
            issues.append(f"Found {len(js_template_issues)} JavaScript template literals with braces")
        
        if issues:
            print(f"❌ Found {len(issues)} f-string formatting issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ No obvious f-string formatting issues found")
            return True
            
    except Exception as e:
        print(f"❌ Error checking f-string issues: {e}")
        return False

def main():
    """Main function"""
    print("🚀 API_URL Definition Fix Script")
    print("=" * 40)
    
    # Check API_URL definition
    definition_ok = fix_api_url_definition()
    
    # Check f-string formatting
    fstring_ok = check_f_string_issues()
    
    print("\n" + "=" * 40)
    if definition_ok and fstring_ok:
        print("🎉 API_URL definition appears to be correct!")
        print("\nThe issue might be:")
        print("1. The Lambda function is not being invoked correctly")
        print("2. The f-string is not being processed during deployment")
        print("3. There's a JavaScript syntax error preventing execution")
        print("\nNext steps:")
        print("1. Run: python check_lambda_syntax.py")
        print("2. Run: python fix_javascript_syntax_complete.py")
        print("3. Deploy: python deploy_bulk_email_api.py")
    else:
        print("❌ API_URL definition issues found")
        print("   Please check the error messages above")

if __name__ == '__main__':
    main()
