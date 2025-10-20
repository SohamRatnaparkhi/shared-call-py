#!/bin/bash

# Quick start script for the FastAPI example
# This script helps you get up and running quickly

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     FastAPI + PostgreSQL Request Coalescing - Quick Start       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check Python version
echo "🔍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.12"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo ""
    echo "Please create .env file with your database URL:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your DATABASE_URL"
    echo ""
    echo "Example DATABASE_URL formats:"
    echo "  Local:    postgresql://postgres:password@localhost:5432/shared_call_demo"
    echo "  Docker:   postgresql://postgres:password@postgres:5432/shared_call_demo"
    echo "  Supabase: postgresql://postgres:[PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment exists${NC}"
fi
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Initialize database
echo "🗄️  Initializing database..."
if python init_db.py; then
    echo -e "${GREEN}✅ Database initialized${NC}"
else
    echo -e "${RED}❌ Failed to initialize database${NC}"
    echo ""
    echo "Common issues:"
    echo "  • Check your DATABASE_URL in .env"
    echo "  • Make sure PostgreSQL is running"
    echo "  • Verify database credentials"
    exit 1
fi
echo ""

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                         READY TO GO!                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "🎉 Setup complete! Here's what to do next:"
echo ""
echo "1️⃣  Start the server (in this terminal):"
echo -e "   ${GREEN}python main.py${NC}"
echo ""
echo "2️⃣  Run load tests (in another terminal):"
echo -e "   ${GREEN}cd examples/fastapi${NC}"
echo -e "   ${GREEN}bash run_comparison.sh${NC}"
echo ""
echo "   Or run tests individually:"
echo -e "   ${GREEN}bash load_test_normal.sh${NC}     # Normal endpoint"
echo -e "   ${GREEN}bash load_test_coalesced.sh${NC}  # Coalesced endpoint"
echo ""
echo "3️⃣  View API documentation:"
echo "   Open: http://localhost:8000/docs"
echo ""
echo "💡 Tips:"
echo "   • Check stats: curl http://localhost:8000/stats"
echo "   • Health check: curl http://localhost:8000/health"
echo "   • Reset stats: curl -X POST http://localhost:8000/stats/reset"
echo ""
