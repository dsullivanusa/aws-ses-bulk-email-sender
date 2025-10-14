#!/usr/bin/env python3
"""
Fix Campaign History status badge styling
"""

def fix_status_badge():
    """Improve the status badge styling"""
    
    # Read the file
    with open('bulk_email_api_lambda.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix status badge styling
    old_badge = 'padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;'
    new_badge = 'padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'
    
    if old_badge in content:
        content = content.replace(old_badge, new_badge)
        print('✅ Updated status badge padding and styling')
    
    # Fix status badge colors to use gradients with white text
    old_colors = "background: ${{status === 'completed' ? '#d1fae5' : status === 'processing' ? '#fef3c7' : '#e5e7eb'}};       \n                                color: ${{status === 'completed' ? '#059669' : status === 'processing' ? '#d97706' : '#6b7280'}};"
    new_colors = "background: ${{status === 'completed' ? 'linear-gradient(135deg, #10b981, #059669)' : status === 'processing' ? 'linear-gradient(135deg, #f59e0b, #d97706)' : 'linear-gradient(135deg, #6b7280, #4b5563)'}};       \n                                color: white;"
    
    if old_colors in content:
        content = content.replace(old_colors, new_colors)
        print('✅ Updated status badge colors to use gradients with white text')
    
    # Write back the fixed content
    with open('bulk_email_api_lambda.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('✅ Status badge styling improved!')
    return True

if __name__ == "__main__":
    fix_status_badge()