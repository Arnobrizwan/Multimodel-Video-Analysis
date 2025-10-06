#!/bin/bash

# Backend startup script for Multimodal Video Analysis System

echo "🚀 Starting Backend Server..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "📝 Please edit .env and add your GEMINI_API_KEY"
    exit 1
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed by verifying requirements.txt timestamp
REQUIREMENTS_FILE="requirements.txt"
VENV_INSTALLED_FLAG="venv/.dependencies_installed"

if [ ! -f "$VENV_INSTALLED_FLAG" ] || [ "$REQUIREMENTS_FILE" -nt "$VENV_INSTALLED_FLAG" ]; then
    echo "📦 Installing/updating dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        touch "$VENV_INSTALLED_FLAG"
        echo "✅ Dependencies installed successfully"
    else
        echo "❌ Failed to install dependencies"
        exit 1
    fi
else
    echo "✅ Dependencies already installed"
fi

# Run the server
echo "✅ Starting FastAPI server on http://localhost:8000"
echo "📡 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
