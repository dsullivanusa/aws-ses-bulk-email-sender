#!/bin/bash
# Test API Gateway with curl commands
# Replace YOUR_API_GATEWAY_URL with your actual API Gateway URL

# Set your API Gateway URL here
API_URL="https://your-api-id.execute-api.us-gov-west-1.amazonaws.com/prod"

echo "================================================================================"
echo "🧪 API Gateway Curl Test Commands"
echo "================================================================================"
echo ""
echo "⚠️  IMPORTANT: Update API_URL variable in this script with your actual URL"
echo ""
echo "Current API_URL: $API_URL"
echo ""

# Test 1: Health check (GET /)
echo "================================================================================"
echo "Test 1: Health Check (GET /)"
echo "================================================================================"
echo ""
echo "Command:"
echo "curl -X GET \"$API_URL/\" -H \"Content-Type: application/json\" -v"
echo ""
read -p "Press Enter to run this test (or Ctrl+C to skip)..."
curl -X GET "$API_URL/" -H "Content-Type: application/json" -v
echo ""
echo ""

# Test 2: Get contacts (GET /contacts)
echo "================================================================================"
echo "Test 2: Get Contacts (GET /contacts)"
echo "================================================================================"
echo ""
echo "Command:"
echo "curl -X GET \"$API_URL/contacts?limit=5\" -H \"Content-Type: application/json\""
echo ""
read -p "Press Enter to run this test..."
curl -X GET "$API_URL/contacts?limit=5" -H "Content-Type: application/json" | python -m json.tool
echo ""
echo ""

# Test 3: Add a contact (POST /contacts)
echo "================================================================================"
echo "Test 3: Add Contact (POST /contacts)"
echo "================================================================================"
echo ""
echo "Command:"
cat << 'EOF'
curl -X POST "$API_URL/contacts" \
  -H "Content-Type: application/json" \
  -d '{
    "contact": {
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User",
      "company": "Test Company"
    }
  }'
EOF
echo ""
read -p "Press Enter to run this test..."
curl -X POST "$API_URL/contacts" \
  -H "Content-Type: application/json" \
  -d '{
    "contact": {
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User",
      "company": "Test Company"
    }
  }' | python -m json.tool
echo ""
echo ""

# Test 4: Get distinct values (GET /contacts/distinct)
echo "================================================================================"
echo "Test 4: Get Distinct Values (GET /contacts/distinct)"
echo "================================================================================"
echo ""
echo "Command:"
echo "curl -X GET \"$API_URL/contacts/distinct?field=company\" -H \"Content-Type: application/json\""
echo ""
read -p "Press Enter to run this test..."
curl -X GET "$API_URL/contacts/distinct?field=company" -H "Content-Type: application/json" | python -m json.tool
echo ""
echo ""

# Test 5: Send campaign (POST /campaign)
echo "================================================================================"
echo "Test 5: Send Campaign (POST /campaign)"
echo "================================================================================"
echo ""
echo "⚠️  This will actually send emails! Make sure emails are verified in SES."
echo ""
echo "Command:"
cat << 'EOF'
curl -X POST "$API_URL/campaign" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Curl Test Campaign",
    "subject": "Test Email",
    "body": "<p>This is a test email from curl</p>",
    "target_contacts": ["test@example.com"],
    "filter_description": "Test"
  }'
EOF
echo ""
read -p "Press Enter to run this test (or Ctrl+C to skip)..."
curl -X POST "$API_URL/campaign" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_name": "Curl Test Campaign",
    "subject": "Test Email",
    "body": "<p>This is a test email from curl</p>",
    "target_contacts": ["test@example.com"],
    "filter_description": "Test"
  }' | python -m json.tool
echo ""
echo ""

echo "================================================================================"
echo "✅ API Gateway Tests Complete!"
echo "================================================================================"
echo ""
echo "💡 Tips:"
echo "   - Add -v flag to curl for verbose output (shows headers)"
echo "   - Add -i flag to see response headers"
echo "   - Use jq instead of 'python -m json.tool' for better formatting"
echo ""
