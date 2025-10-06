#!/bin/bash

# Frontend startup script for Multimodal Video Analysis System

echo "🚀 Starting Frontend Development Server..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run the development server
echo "✅ Starting Vite dev server on http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev
