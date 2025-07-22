#!/bin/bash

# # Create project structure
# mkdir -p rag_chatbot/{backend/{api/{routes,services,agents},utils},frontend,configs,logs,uploads,chroma_storage}

# # Create virtual environment
# python -m venv venv
# source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install requirements
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
OPENAI_API_KEY=""
CHROMADB_DIR=""
EMBEDDING_MODEL=""
YOUTUBE_API_KEY=""
FASTAPI_HOST="0.0.0.0"
FASTAPI_PORT="8000"
STREAMLIT_PORT="8501"
EOL
    echo "Please update .env file with your API keys!"
fi

echo "Setup complete! Please update your .env file with proper API keys."