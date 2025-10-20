#!/bin/bash

# Run both load tests and compare results
# This script runs normal endpoint test first, then coalesced endpoint test

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         Request Coalescing Performance Comparison               ║"
echo "║                                                                  ║"
echo "║  This will run load tests against both endpoints:               ║"
echo "║  1. Normal endpoint (no coalescing)                             ║"
echo "║  2. Coalesced endpoint (with shared-call-py)                    ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if server is running
echo "🔍 Checking if server is running..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Server is not running!${NC}"
    echo ""
    echo "Please start the server in another terminal:"
    echo "  cd examples/fastapi"
    echo "  python main.py"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Wait a moment
sleep 2

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                  TEST 1: NORMAL ENDPOINT                       ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Run normal endpoint test
bash load_test_normal.sh

echo ""
echo "⏸️  Waiting 5 seconds before next test..."
sleep 5
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                TEST 2: COALESCED ENDPOINT                      ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Run coalesced endpoint test
bash load_test_coalesced.sh

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    COMPARISON COMPLETE                        ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "🎉 Both tests completed!"
echo ""
echo "💡 Key Takeaways:"
echo "   • Normal endpoint: Every request hits the database"
echo "   • Coalesced endpoint: Requests share database queries"
echo "   • Result: Massive reduction in database load (usually 99%+)"
echo ""
echo "📊 Check the statistics above to see the performance difference!"
