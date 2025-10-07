#!/bin/bash
# Ready-to-use API Gateway Tests
# Your API URL: https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod

API_URL="https://yi6ss4dsoe.execute-api.us-gov-west-1.amazonaws.com/prod"

echo "================================================================================"
echo "🧪 Testing API Gateway: $API_URL"
echo "================================================================================"
echo ""

# Test 1: Health Check
echo "1️⃣  Testing Health Check (GET /)..."
echo "Command: curl -X GET \"$API_URL/\""
curl -X GET "$API_URL/" -H "Content-Type: application/json"
echo -e "\n"

# Test 2: Get Contacts
echo "================================================================================"
echo "2️⃣  Testing Get Contacts (GET /contacts)..."
echo "Command: curl -X GET \"$API_URL/contacts?limit=5\""
curl -X GET "$API_URL/contacts?limit=5" -H "Content-Type: application/json"
echo -e "\n"

# Test 3: Get Distinct Values
echo "================================================================================"
echo "3️⃣  Testing Get Distinct Values (GET /contacts/distinct)..."
echo "Command: curl -X GET \"$API_URL/contacts/distinct?field=company\""
curl -X GET "$API_URL/contacts/distinct?field=company" -H "Content-Type: application/json"
echo -e "\n"

echo "================================================================================"
echo "✅ Basic API Tests Complete!"
echo "================================================================================"
echo ""
echo "💡 To add a contact, run:"
echo "   curl -X POST \"$API_URL/contacts\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"contact\":{\"email\":\"test@test.com\",\"first_name\":\"Test\"}}'"
echo ""
echo "💡 To send a campaign, run:"
echo "   curl -X POST \"$API_URL/campaign\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"campaign_name\":\"Test\",\"subject\":\"Hi\",\"body\":\"<p>Test</p>\",\"target_contacts\":[\"your-email@example.com\"],\"filter_description\":\"Test\"}'"
echo ""
