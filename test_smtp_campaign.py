import requests
import json
import time

def test_smtp_campaign(function_url):
    """Test SMTP bulk email campaign"""
    
    # Test 1: Save SMTP configuration
    print("1. Testing SMTP configuration...")
    smtp_config = {
        "action": "save_smtp_config",
        "smtp_server": "192.168.1.100",
        "smtp_port": 25,
        "from_email": "sender@domain.com",
        "username": "",
        "password": "",
        "use_tls": False
    }
    
    response = requests.post(function_url, json=smtp_config)
    print(f"SMTP Config Response: {response.status_code} - {response.text}")
    
    # Test 2: Add test contacts
    print("\\n2. Adding test contacts...")
    test_contacts = [
        {"email": "test1@example.com", "first_name": "John", "last_name": "Doe", "company": "Test Corp"},
        {"email": "test2@example.com", "first_name": "Jane", "last_name": "Smith", "company": "Demo Inc"},
        {"email": "test3@example.com", "first_name": "Bob", "last_name": "Johnson", "company": "Sample LLC"}
    ]
    
    for contact in test_contacts:
        contact_data = {"action": "add_contact", "contact": contact}
        response = requests.post(function_url, json=contact_data)
        print(f"Added contact {contact['email']}: {response.status_code}")
    
    # Test 3: Get contacts
    print("\\n3. Getting contacts...")
    get_contacts = {"action": "get_contacts"}
    response = requests.post(function_url, json=get_contacts)
    print(f"Contacts Response: {response.status_code}")
    if response.status_code == 200:
        contacts = response.json()
        print(f"Total contacts: {contacts['count']}")
    
    # Test 4: Send campaign with rate limiting
    print("\\n4. Sending test campaign...")
    campaign_data = {
        "action": "send_campaign",
        "campaign_name": "Test SMTP Campaign",
        "subject": "Hello {{first_name}}!",
        "body": "Dear {{first_name}} {{last_name}},\\n\\nThis is a test email from {{company}}.\\n\\nBest regards",
        "emails_per_minute": 120,  # 2 emails per second
        "batch_size": 5
    }
    
    response = requests.post(function_url, json=campaign_data)
    print(f"Campaign Response: {response.status_code} - {response.text}")
    
    if response.status_code == 200:
        campaign_result = response.json()
        campaign_id = campaign_result['campaign_id']
        
        # Test 5: Check campaign status
        print("\\n5. Checking campaign status...")
        status_data = {"action": "get_campaign_status", "campaign_id": campaign_id}
        response = requests.post(function_url, json=status_data)
        print(f"Status Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # Replace with your actual Function URL
    function_url = input("Enter your Lambda Function URL: ")
    test_smtp_campaign(function_url)