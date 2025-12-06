#!/bin/bash
# Start the Spoonos Butler API Bridge

echo "🚀 Starting Spoonos Butler API Bridge..."

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements-api.txt

echo "✅ Starting API server..."
python spoonos_butler_api.py
