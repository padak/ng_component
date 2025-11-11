#!/bin/bash
# Start the Web UI backend server
#
# Usage:
#   ./web_ui/start.sh
#
# Or from web_ui directory:
#   ./start.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Agent-Based Integration System${NC}"
echo -e "${BLUE}Web UI Backend Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "agent_executor.py" ]; then
    if [ -f "../agent_executor.py" ]; then
        echo -e "${YELLOW}Changing to parent directory...${NC}"
        cd ..
    else
        echo -e "${RED}Error: Must run from examples/e2b_mockup/ directory${NC}"
        echo "Please run: cd examples/e2b_mockup && ./web_ui/start.sh"
        exit 1
    fi
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo ""
    echo "Please create .env file with:"
    echo "  E2B_API_KEY=your_e2b_api_key_here"
    echo "  SF_API_URL=http://localhost:8000"
    echo "  SF_API_KEY=test_key_12345"
    echo ""
    exit 1
fi

# Check for E2B_API_KEY
if ! grep -q "E2B_API_KEY=" .env || grep -q "E2B_API_KEY=$" .env; then
    echo -e "${RED}Error: E2B_API_KEY not set in .env file${NC}"
    echo ""
    echo "Please add your E2B API key to .env:"
    echo "  E2B_API_KEY=your_e2b_api_key_here"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} Found .env file"
echo -e "${GREEN}✓${NC} E2B_API_KEY is set"
echo ""

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo -e "${RED}Error: uvicorn not installed${NC}"
    echo ""
    echo "Please install dependencies:"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} uvicorn is installed"
echo ""

# Check if port 8080 is available
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port 8080 is already in use${NC}"
    echo "Please stop the other process or use a different port:"
    echo "  uvicorn web_ui.app:app --reload --port 8081"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} Port 8080 is available"
echo ""

echo -e "${BLUE}Starting server...${NC}"
echo ""
echo -e "WebSocket endpoint: ${GREEN}ws://localhost:8080/chat${NC}"
echo -e "Web interface:      ${GREEN}http://localhost:8080/static/${NC}"
echo -e "Health check:       ${GREEN}http://localhost:8080/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# Start uvicorn
uvicorn web_ui.app:app --reload --port 8080
