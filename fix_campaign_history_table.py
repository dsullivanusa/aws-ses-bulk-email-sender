#!/usr/bin/env python3
"""
Fix Campaign History table styling for better readability
"""

def fix_campaign_history_table():
    """Improve the Campaign History table colors and readability"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Fix table styling
    old_table = 'id="historyTable" style="width: 100%; border-collapse: collapse;"'
    new_table = 'id="historyTable" style="width: 100%; border-collapse: collapse; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-radius: 8px; overflow: hidden;"'
    
    if old_table in content:
        content = content.replace(old_table, new_table)
        print('✅ Updated table container styling')
    
    # 2. Fix header styling - make it dark blue with white text
    old_header = 'padding: 12px; text-align: left; background: #f3f4f6; border-bottom: 2px solid #e5e7eb;'
    new_header = 'padding: 16px; text-align: left; background: linear-gradient(135deg, #1e40af, #1e3a8a); color: white; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 3px solid #3b82f6;'
    
    if old_header in content:
        content = content.replace(old_header, new_header)
        print('✅ Updated table header styling')
    
    # 3. Fix row styling - make text darker and more readable
    old_row_style = 'row.style.borderBottom = \'1px solid #e5e7eb\';'
    new_row_style = '''row.style.borderBottom = '1px solid #e5e7eb';
                    row.style.backgroundColor = '#ffffff';
                    row.style.transition = 'all 0.2s ease';
                    row.onmouseover = function() {{ 
                        this.style.backgroundColor = '#f8fafc'; 
                        this.style.transform = 'scale(1.01)';
                        this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                    }};
                    row.onmouseout = function() {{ 
                        this.style.backgroundColor = '#ffffff'; 
                        this.style.transform = 'scale(1)';
                        this.style.boxShadow = 'none';
                    }};'''
    
    if old_row_style in content:
        content = content.replace(old_row_style, new_row_style)
        print('✅ Updated row hover effects')
    
    # 4. Fix cell styling - make text darker and more readable
    old_cell_style = 'padding: 12px;'
    new_cell_style = 'padding: 16px; color: #1f2937; font-size: 14px; font-weight: 500; border-right: 1px solid #f3f4f6;'
    
    # Only replace in the campaign row innerHTML section
    campaign_row_section = content[content.find('row.innerHTML = `'):content.find('`;', content.find('row.innerHTML = `')) + 2]
    
    if old_cell_style in campaign_row_section:
        new_campaign_row_section = campaign_row_section.replace(old_cell_style, new_cell_style)
        content = content.replace(campaign_row_section, new_campaign_row_section)
        print('✅ Updated cell styling for better readability')
    
    # 5. Improve button styling
    old_button = 'padding: 6px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;'
    new_button = 'padding: 8px 16px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);'
    
    if old_button in content:
        content = content.replace(old_button, new_button)
        print('✅ Updated button styling')
    
    # Write back the fixed content
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('✅ Campaign History table styling improved for better readability!')
    return True

if __name__ == "__main__":
    fix_campaign_history_table()