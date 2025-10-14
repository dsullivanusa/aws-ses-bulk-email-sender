#!/usr/bin/env python3
"""
Fix Campaign History table cell styling for better readability
"""

def fix_campaign_cells():
    """Improve the Campaign History table cell colors and readability"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix each cell type individually
    fixes = [
        # Campaign Name - make it bold and dark
        ('style="padding: 12px;">${{campaign.campaign_name', 'style="padding: 16px; color: #1f2937; font-size: 14px; font-weight: 600;">${{campaign.campaign_name'),
        
        # Subject - add ellipsis for long subjects
        ('style="padding: 12px;">${{campaign.subject', 'style="padding: 16px; color: #374151; font-size: 14px; font-weight: 500; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${{campaign.subject || \'No Subject\'}}">${{campaign.subject'),
        
        # Date - use monospace font
        ('style="padding: 12px;">${{formattedDate', 'style="padding: 16px; color: #1f2937; font-size: 14px; font-weight: 500; font-family: \'Monaco\', monospace;">${{formattedDate'),
        
        # Recipients - make it green and centered
        ('style="padding: 12px;">${{recipients', 'style="padding: 16px; color: #059669; font-size: 14px; font-weight: 600; text-align: center;">${{recipients'),
        
        # Launched By - make it readable
        ('style="padding: 12px;">${{launchedBy', 'style="padding: 16px; color: #1f2937; font-size: 14px; font-weight: 500;">${{launchedBy'),
        
        # Actions column - improve padding
        ('style="padding: 12px;">', 'style="padding: 16px; text-align: center;">'),
    ]
    
    fixed_count = 0
    for old_text, new_text in fixes:
        if old_text in content:
            content = content.replace(old_text, new_text)
            fixed_count += 1
            print(f'✅ Fixed: {old_text[:50]}...')
    
    # Write back the fixed content
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'✅ Fixed {fixed_count} cell styling issues for better readability!')
    return True

if __name__ == "__main__":
    fix_campaign_cells()