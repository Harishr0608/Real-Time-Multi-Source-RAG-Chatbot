# 🤖 Real-Time Multi-Source RAG Chatbot

A comprehensive RAG (Retrieval-Augmented Generation) chatbot that supports multiple document types and real-time embedding management using LangGraph agents, ChromaDB, FastAPI, and Streamlit.

## 🚀 Features

- **Multi-Source Support**: PDFs, DOCX, Excel, HTML, YouTube videos, and web pages
- **Real-Time Processing**: Upload, process, and delete documents dynamically
- **LangGraph Agents**: Modular agent-based architecture for processing pipeline
- **Vector Store**: ChromaDB for efficient similarity search
- **Modern UI**: Clean Streamlit interface with chat functionality
- **RESTful API**: FastAPI backend with comprehensive endpoints
- **Docker Support**: Containerized deployment option

## 🏗️ Architecture

```
[Streamlit UI] → [FastAPI Backend] → [LangGraph Agents] → [ChromaDB]
                      ↓
                [Document Processing Pipeline]
                      ↓
              [Embedding Generation & Storage]
                      ↓
                [Query Processing & RAG]
```

## 📋 Prerequisites

- Python 3.10.16
- OpenAI API key
- YouTube API key (optional, for YouTube support)
- Docker (optional, for containerized deployment)

## 🛠️ Installation

### Option 1: Local Setup

1. **Clone and Setup**
   ```bash
   git clone https://github.com/Harishr0608/Real-Time-Multi-Source-RAG-Chatbot.git
   cd Real-Time-Multi-Source-RAG-Chatbot
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Configure Environment**
   - Update `.env` file with your API keys:
   ```env
   OPENAI_API_KEY=your-openai-key-here
   YOUTUBE_API_KEY=your-youtube-key-here
   ```

3. **Run Application**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

### Option 2: Docker Setup

1. **Configure Environment**
   - Create `.env` file with your API keys

2. **Run with Docker**
   ```bash
   chmod +x run_docker.sh
   ./run_docker.sh
   ```

## 🎯 Usage

1. **Access the Application**
   - Frontend UI: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

2. **Upload Documents**
   - Use the sidebar to upload PDF, DOCX, or Excel files
   - Add YouTube URLs or web page links
   - Documents are processed and stored automatically

3. **Chat with Your Data**
   - Ask questions in the chat interface
   - Get responses based on your uploaded content
   - View source documents for each response

4. **Manage Knowledge Base**
   - Delete specific files or links
   - View statistics about your knowledge base
   - Clear chat history as needed

## 🔧 API Endpoints

- `POST /upload_file` - Upload and process file
- `POST /upload_link` - Process web link or YouTube URL
- `POST /query` - Query the knowledge base
- `DELETE /delete_file/{hash}` - Delete specific file
- `DELETE /delete_link/{hash}` - Delete specific link
- `GET /health` - Health check

## 🧠 Agent Architecture

The system uses LangGraph agents for modular processing:

- **FileIngestionAgent**: Processes uploaded files
- **LinkIngestionAgent**: Handles web links and YouTube URLs
- **EmbeddingAgent**: Generates and stores embeddings
- **RetrieverAgent**: Retrieves relevant documents
- **AnswerSynthesisAgent**: Generates final responses
- **DeletionAgent**: Manages document deletion

## 📊 Supported File Types

- **Documents**: PDF, DOCX, Excel (XLSX, XLS)
- **Web Content**: HTML pages, web articles
- **Video**: YouTube videos (via transcripts)
- **Links**: Any web URL with text content

## 🔒 Configuration

Key settings in `configs/config.yaml`:

```yaml
embedding:
  model: "openai"
  chunk_size: 500
  overlap: 50

retrieval:
  type: hybrid
  top_k: 5

llm:
  model: "gpt-4o"
  temperature: 0.7
```

## 🚨 Troubleshooting

1. **API Key Issues**
   - Ensure OPENAI_API_KEY is set correctly
   - Check API key permissions and quota

2. **ChromaDB Issues**
   - Ensure write permissions to chroma_storage directory
   - Clear ChromaDB if corrupted: `rm -rf chroma_storage/*`

3. **YouTube Processing**
   - Some videos may not have transcripts available
   - Ensure YOUTUBE_API_KEY is set for enhanced functionality

4. **Memory Issues**
   - Adjust chunk_size in config for large documents
   - Consider using smaller embedding models for limited resources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 Screenshot

<img width="1920" height="1134" alt="Screenshot 2025-07-22 at 19 01 26" src="https://github.com/user-attachments/assets/d68835f4-796b-45d5-bba1-798c893f31c1" />

## 🔗 Links

- [LangChain Documentation](https://docs.langchain.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
