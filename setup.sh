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
OPENAI_API_KEY="sk-svcacct-vMN3fZyJx0PUnL_9KhloMD0WZM5qypD_W9mUxR07n_IVldQXFGdMTwFCBSGDQk2iWmVu2T3BlbkFJjIyZemVl4jAdYz-vR5yRMA5MiNpFkckynt-ywztlEe_OSmkfciGs2-LFShyPCjOKJCKAA"
CHROMADB_DIR="/Users/harishr/Desktop/RAG/home/vectorstore"
EMBEDDING_MODEL="text-embedding-3-large"
YOUTUBE_API_KEY="AIzaSyBNByfL278oLayLydyR_6dEojRlY7NTFWw"
FASTAPI_HOST="0.0.0.0"
FASTAPI_PORT="8000"
STREAMLIT_PORT="8501"
EOL
    echo "Please update .env file with your API keys!"
fi

echo "Setup complete! Please update your .env file with proper API keys."