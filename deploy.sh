#!/bin/bash

# Jenkins UI - Alternative Interface
# Deployment Script

set -e

echo "Jenkins UI - Alternative Interface"
echo "=================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null; then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

echo "✅ Python and pip are installed"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your Jenkins configuration"
    echo "   - JENKINS_URL: Your Jenkins server URL"
    echo "   - JENKINS_USERNAME: Your Jenkins username"
    echo "   - JENKINS_PASSWORD: Your Jenkins password"
    echo "   - SECRET_KEY: A random secret key"
    echo ""
    echo "Press Enter to continue after editing .env file..."
    read
fi

# Test connection
echo "🔗 Testing Jenkins connection..."
python run.py --test-only 2>/dev/null || {
    echo "⚠️  Warning: Could not connect to Jenkins"
    echo "   Make sure your Jenkins server is running and credentials are correct"
    echo "   You can still run the application, but some features may not work"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
}

echo "🚀 Starting Jenkins UI..."
echo "   Access the application at: http://localhost:5000"
echo "   Press Ctrl+C to stop the server"
echo ""

# Run the application
python run.py 