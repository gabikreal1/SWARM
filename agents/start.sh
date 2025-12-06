#!/bin/bash
# Quick start script for Butler system

echo "🚀 Starting Butler Agent System"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "   Please create .env with required variables"
    echo "   See .env.example for template"
    exit 1
fi

# Check Python
if ! command -v python &> /dev/null; then
    echo "❌ Python not found!"
    exit 1
fi

echo "✅ Environment OK"
echo ""
echo "📋 Choose what to run:"
echo ""
echo "1) Butler CLI (interactive interface)"
echo "2) Worker Agent (job executor)"
echo "3) Test NeoFS connection"
echo "4) Both (Butler + Worker in separate terminals)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🤖 Starting Butler CLI..."
        python butler_cli.py
        ;;
    2)
        echo ""
        echo "👷 Starting Worker Agent..."
        python simple_worker.py
        ;;
    3)
        echo ""
        echo "🧪 Testing NeoFS..."
        python -c "from neofs_helper import test_neofs; test_neofs()"
        ;;
    4)
        echo ""
        echo "🚀 Starting both components..."
        echo ""
        echo "Please open TWO terminals and run:"
        echo ""
        echo "Terminal 1: python simple_worker.py"
        echo "Terminal 2: python butler_cli.py"
        echo ""
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
