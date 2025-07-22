#!/bin/bash

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found! Please run setup.sh first."
    exit 1
fi

# Start backend and frontend
echo "Starting RAG Chatbot..."

# Start backend in background
echo "Starting FastAPI backend..."
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 5

# Start frontend
echo "Starting Streamlit frontend..."
streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo "Services started!"
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:8501"
echo "API Docs: http://localhost:8000/docs"

# Wait for user input to stop services
read -p "Press Enter to stop services..."

# Kill background processes
kill $BACKEND_PID $FRONTEND_PID
echo "Services stopped."