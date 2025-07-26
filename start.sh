#!/bin/bash

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    print_status "Shutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        print_status "FastAPI backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        print_status "Streamlit frontend stopped"
    fi
    print_success "All services stopped successfully!"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_status "Please create a .env file with the following variables:"
    echo ""
    echo "OPENAI_API_KEY=your-openai-api-key-here"
    echo "YOUTUBE_API_KEY=your-youtube-api-key-here"
    echo "CHROMADB_DIR=$(pwd)/data/vectorstore"
    echo "MAX_CHUNK_TOKENS=500"
    echo "CHUNK_OVERLAP=50"
    echo "TOP_K=5"
    echo "LLM_MODEL=gpt-4o"
    echo "EMBED_MODEL=text-embedding-3-large"
    echo "API_BASE_URL=http://localhost:8000/api/v1"
    echo "LOG_LEVEL=INFO"
    echo "ANONYMIZED_TELEMETRY=false"
    echo ""
    exit 1
fi

# Check if required files exist
if [ ! -f "frontend/streamlit_app.py" ]; then
    print_error "frontend/streamlit_app.py not found!"
    print_status "Please ensure your Streamlit app is located at frontend/streamlit_app.py"
    exit 1
fi

if [ ! -f "backend/api/main.py" ]; then
    print_error "backend/api/main.py not found!"
    print_status "Please ensure your FastAPI app is located at backend/api/main.py"
    exit 1
fi

# Check if required directories exist and create them
print_status "Checking required directories..."
directories=("data/uploads" "data/transcripts" "data/chunks" "data/metadata" "data/vectorstore")
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    fi
done

# Check if Python virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "No virtual environment detected. Consider activating your virtual environment first."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if required Python packages are installed
print_status "Checking Python dependencies..."
python -c "import fastapi, streamlit, openai, chromadb, langchain" 2>/dev/null
if [ $? -ne 0 ]; then
    print_error "Some required packages are missing!"
    print_status "Please install dependencies with: pip install -r requirements.txt"
    exit 1
fi

# Check if ports are available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "Port $1 is already in use!"
        print_status "Please stop the service using port $1 or choose a different port."
        return 1
    fi
    return 0
}

print_status "Checking port availability..."
check_port 8000 || exit 1
check_port 8501 || exit 1

print_success "All checks passed!"
echo ""
print_status "Starting RAG Chatbot services..."
echo "═══════════════════════════════════════════"

# Start FastAPI backend
print_status "Starting FastAPI backend on port 8000..."
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start and check if it's running
sleep 3
if kill -0 $BACKEND_PID 2>/dev/null; then
    # Check if backend is responding
    for i in {1..10}; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            print_success "FastAPI backend started successfully!"
            break
        fi
        if [ $i -eq 10 ]; then
            print_error "FastAPI backend failed to start properly!"
            print_status "Check backend.log for details"
            exit 1
        fi
        sleep 1
    done
else
    print_error "Failed to start FastAPI backend!"
    print_status "Check backend.log for details"
    exit 1
fi

# Start Streamlit frontend - FIXED PATH
print_status "Starting Streamlit frontend on port 8501..."
streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3
if kill -0 $FRONTEND_PID 2>/dev/null; then
    print_success "Streamlit frontend started successfully!"
else
    print_error "Failed to start Streamlit frontend!"
    print_status "Check frontend.log for details"
    exit 1
fi

echo ""
print_success "🚀 RAG Chatbot is now running!"
echo "═══════════════════════════════════════════"
echo ""
print_status "Access your application:"
echo "  📱 Frontend UI:    http://localhost:8501"
echo "  🔧 Backend API:    http://localhost:8000"
echo "  📚 API Documentation: http://localhost:8000/docs"
echo "  📊 Health Check:   http://localhost:8000/health"
echo ""
print_status "Logs are being written to:"
echo "  🔴 Backend:  backend.log"
echo "  🔵 Frontend: frontend.log"
echo ""
print_warning "Press Ctrl+C or Enter to stop all services..."

# Wait for user input to stop services
read -p ""