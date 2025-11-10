#!/bin/bash

# Test script for Salesforce REST API Mock Server
# This script demonstrates all the available API endpoints

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "Salesforce REST API Mock Server Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Root endpoint
echo -e "${BLUE}Test 1: Root Endpoint${NC}"
echo "GET /"
curl -s "${BASE_URL}/" | python3 -m json.tool
echo -e "\n"

# Test 2: List all SObjects
echo -e "${BLUE}Test 2: List All SObjects${NC}"
echo "GET /sobjects"
curl -s "${BASE_URL}/sobjects" | python3 -m json.tool
echo -e "\n"

# Test 3: Describe Lead object
echo -e "${BLUE}Test 3: Describe Lead Object${NC}"
echo "GET /sobjects/Lead/describe"
curl -s "${BASE_URL}/sobjects/Lead/describe" | python3 -m json.tool | head -50
echo "... (output truncated)"
echo -e "\n"

# Test 4: Simple query
echo -e "${BLUE}Test 4: Simple Query${NC}"
echo "GET /query?q=SELECT * FROM Lead LIMIT 5"
curl -s "${BASE_URL}/query?q=SELECT%20*%20FROM%20Lead%20LIMIT%205" | python3 -m json.tool
echo -e "\n"

# Test 5: Query with WHERE clause
echo -e "${BLUE}Test 5: Query with WHERE Clause${NC}"
echo "GET /query?q=SELECT Id, FirstName, LastName, Status FROM Lead WHERE Status='New' LIMIT 3"
curl -s "${BASE_URL}/query?q=SELECT%20Id%2C%20FirstName%2C%20LastName%2C%20Status%20FROM%20Lead%20WHERE%20Status%3D%27New%27%20LIMIT%203" | python3 -m json.tool
echo -e "\n"

# Test 6: Query with date comparison
echo -e "${BLUE}Test 6: Query with Date Comparison${NC}"
echo "GET /query?q=SELECT Id, FirstName, LastName, CreatedDate FROM Lead WHERE CreatedDate > '2024-01-01' LIMIT 3"
curl -s "${BASE_URL}/query?q=SELECT%20Id%2C%20FirstName%2C%20LastName%2C%20CreatedDate%20FROM%20Lead%20WHERE%20CreatedDate%20%3E%20%272024-01-01%27%20LIMIT%203" | python3 -m json.tool
echo -e "\n"

# Test 7: Query Opportunities
echo -e "${BLUE}Test 7: Query Opportunities${NC}"
echo "GET /query?q=SELECT * FROM Opportunity LIMIT 3"
curl -s "${BASE_URL}/query?q=SELECT%20*%20FROM%20Opportunity%20LIMIT%203" | python3 -m json.tool
echo -e "\n"

# Test 8: Create a new Lead (mock)
echo -e "${BLUE}Test 8: Create New Lead (Mock)${NC}"
echo "POST /sobjects/Lead"
curl -s -X POST "${BASE_URL}/sobjects/Lead" \
  -H "Content-Type: application/json" \
  -d '{
    "FirstName": "John",
    "LastName": "Doe",
    "Company": "Acme Corp",
    "Status": "New",
    "Email": "john.doe@example.com"
  }' | python3 -m json.tool
echo -e "\n"

# Test 9: Health check
echo -e "${BLUE}Test 9: Health Check${NC}"
echo "GET /health"
curl -s "${BASE_URL}/health" | python3 -m json.tool
echo -e "\n"

# Test 10: Error handling - Invalid SObject
echo -e "${BLUE}Test 10: Error Handling - Invalid SObject${NC}"
echo "GET /sobjects/InvalidObject/describe"
curl -s "${BASE_URL}/sobjects/InvalidObject/describe" | python3 -m json.tool
echo -e "\n"

# Test 11: Error handling - Invalid SOQL
echo -e "${BLUE}Test 11: Error Handling - Invalid SOQL${NC}"
echo "GET /query?q=INVALID QUERY"
curl -s "${BASE_URL}/query?q=INVALID%20QUERY" | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN}=========================================="
echo "All tests completed!"
echo -e "==========================================${NC}"
