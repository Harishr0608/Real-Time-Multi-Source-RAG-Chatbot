#!/bin/bash

# Build and run with Docker Compose
echo "Building and starting RAG Chatbot with Docker..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found! Please create it with your API keys."
    exit 1
fi

# Build and start services
docker-compose up --build

echo "Services started with Docker!"
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:8501"
echo "API Docs: http://localhost:8000/docs"