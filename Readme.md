# RAG Chatbot

A production-ready Retrieval-Augmented Generation (RAG) chatbot built with FastAPI, Streamlit, LangGraph, and ChromaDB.

## 🚀 Features

- **Multi-format Support**: PDF, DOCX, XLSX, CSV, TXT, MD, YouTube videos, Web pages
- **Real-time Processing**: Async document ingestion with LangGraph agents
- **Smart Chunking**: Token-based text splitting with overlap
- **Vector Search**: ChromaDB for similarity search with proper source attribution
- **Chain-of-Thought**: Step-by-step reasoning with explicit reasoning process
- **Web Interface**: Clean Streamlit UI with source deduplication
- **Source Management**: Proper filename extraction and type detection
- **Docker Ready**: Complete containerization

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Development Setup](#️-development-setup)
- [API Endpoints](#-api-endpoints)
- [Configuration](#️-configuration)
- [Architecture](#️-architecture)
- [Supported Sources](#-supported-sources)
- [Workflow](#-workflow)
- [Source Attribution Features](#️-source-attribution-features)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### 1. Clone and Setup
```bash
git clone https://github.com/your-username/rag-chatbot.git
cd rag-chatbot
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 2. Run with Docker
```bash
docker-compose up --build
```

### 3. Access Applications
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🛠️ Development Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Services
```bash
# Backend
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in another terminal)
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

## 📚 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/upload_file` | Upload document file |
| POST | `/api/v1/upload_link` | Process web link or YouTube URL |
| DELETE | `/api/v1/delete/{source_id}` | Delete source and embeddings |
| POST | `/api/v1/query` | Query documents with Chain-of-Thought |
| POST | `/api/v1/chat` | Chat interface with conversation context |
| GET | `/api/v1/list_sources` | List uploaded sources with status |
| GET | `/api/v1/status/{source_id}` | Get processing status |
| GET | `/api/v1/health` | Health check endpoint |

## ⚙️ Configuration

Environment variables in `.env`:

```text
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (with defaults)
MAX_CHUNK_TOKENS=500
CHUNK_OVERLAP=50
LLM_MODEL=gpt-4o
EMBED_MODEL=text-embedding-3-large
CHROMADB_DIR=./data/vectorstore
API_BASE_URL=http://localhost:8000/api/v1
```

## 🏗️ Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │────│    FastAPI      │────│    ChromaDB     │
│   Frontend      │    │    Backend      │    │  Vector Store   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   LangGraph     │
                       │ Ingestion Agents│
                       └─────────────────┘
```

### Components
- **FastAPI Backend**: REST API with async endpoints and proper error handling
- **LangGraph Agents**: Orchestrate document ingestion workflow (ingest → chunk → embed)
- **ChromaDB**: Persistent vector database with metadata storage
- **Streamlit Frontend**: Interactive web interface with real-time status updates
- **RAG Service**: Enhanced retrieval with metadata loading and source attribution
- **Docker**: Multi-service containerized deployment

## 📄 Supported Sources

### Documents
- **PDF**: Portable Document Format files
- **DOCX**: Microsoft Word documents
- **XLSX**: Microsoft Excel spreadsheets
- **CSV**: Comma-separated values files
- **TXT**: Plain text files
- **MD**: Markdown files

### Web Content
- **YouTube Videos**: Automatic transcript extraction with title and uploader detection
- **Web Pages**: HTML content extraction from any accessible URL

## 🔄 Workflow

### Document Ingestion
1. **Upload** → File/Link received via FastAPI endpoint
2. **Metadata Storage** → Source information saved to JSON files
3. **Extract** → Text extraction using appropriate loader (PDFLoader, YouTubeLoader, etc.)
4. **Clean** → Text normalization and boilerplate removal
5. **Chunk** → Token-based splitting with configurable overlap
6. **Embed** → OpenAI embedding generation with retry logic
7. **Store** → ChromaDB storage with enhanced metadata for source attribution

### Query Processing (Chain-of-Thought RAG)
1. **Embed Query** → Generate query embedding using OpenAI
2. **Retrieve** → Vector similarity search in ChromaDB
3. **Load Metadata** → Fetch source details from metadata JSON files
4. **Aggregate Sources** → Group chunks by source with proper attribution
5. **Construct Context** → Build citations with source information
6. **Chain-of-Thought** → Structured reasoning with explicit steps
7. **Generate Answer** → LLM produces reasoned response with citations
8. **Format Response** → Return answer with sources, reasoning, and proper type detection

## 🏷️ Source Attribution Features

- **Filename Extraction**: Proper filename detection for all source types
- **Type Detection**: Automatic classification (Document, YouTube Video, Web Page)
- **Source Deduplication**: Groups multiple chunks from same source
- **Citation Numbers**: Proper [1], [2], [3] citation format
- **Metadata Preservation**: Maintains source information throughout pipeline

## 📁 Project Structure

```text
rag_chatbot/
│
├── backend/                             # FastAPI + LangGraph agents
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py                # /upload_file, /upload_link
│   │   │   ├── delete.py                # /delete_file_or_link
│   │   │   └── query.py                 # /query
│   │   └── main.py                      # FastAPI app
│   │
│   ├── services/                        # Business logic
│   │   ├── __init__.py
│   │   ├── ingestion_service.py         # file/link → cleaned text
│   │   ├── chunking_service.py          # splits text into token‐limited chunks
│   │   ├── embedding_service.py         # chunk → embed → upsert/delete
│   │   ├── deletion_service.py          # remove embeddings by file_id/link_id
│   │   └── rag_service.py               # retrieve + CoT + answer
│   │
│   ├── agents/                          # LangGraph orchestration
│   │   ├── __init__.py
│   │   ├── graph.py                     # define nodes & DAG
│   │   └── nodes/                       # individual async steps
│   │       ├── __init__.py
│   │       ├── ingest_node.py
│   │       ├── chunk_node.py
│   │       ├── embed_node.py
│   │       ├── delete_node.py
│   │       ├── retrieve_node.py
│   │       └── answer_node.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── loader_factory.py            # detect file type & route 
│       ├── link_parser.py               # HTML scraper / YouTube → transcript
│       └── text_cleaner.py              # whitespace, boilerplate removal
│
├── frontend/                            # Streamlit UI
│   └── streamlit_app.py                # upload widget, link input, query box
│
├── configs/
│   ├── config.yaml                      # chunk_size, overlap, top_k, model names
│   └── logging.yaml                     # uvicorn + agent logging
│
├── .env                                 # secrets & paths
├── data/
│   ├── uploads/                         # raw user files
│   ├── transcripts/                     # raw YouTube text
│   ├── chunks/                          # cached chunked .json per source
│   ├── metadata/                        # mapping file_id↔hash↔status
│   └── vectorstore/                     # ChromaDB storage
│
├── docker/
│   ├── Dockerfile.base                  # Python deps & system libs
│   ├── Dockerfile                       # builds backend + frontend container
│   └── requirements.txt                 # pinned Python packages
│
├── docker-compose.yml                   # spins up backend + Streamlit services
└── README.md
```

## 📊 Monitoring

- **Health Checks**: `/health` endpoint for service monitoring
- **Structured Logging**: Comprehensive logging with source tracking
- **Processing Status**: Real-time status updates (processing, completed, failed)
- **Error Handling**: Graceful error handling with retry mechanisms
- **Auto-refresh**: Frontend auto-updates processing status

## 🔧 Development

### Adding New File Types
1. Create loader class in `backend/utils/loader_factory.py`
2. Register in `LoaderFactory.get_loader()` method
3. Update file type validation in upload endpoints
4. Test with sample files

### Extending RAG Functionality
1. **New Nodes**: Create in `backend/agents/nodes/`
2. **Workflow Updates**: Modify `backend/agents/graph.py`
3. **Service Layer**: Update relevant service classes
4. **API Endpoints**: Add new routes as needed

## 🚨 Troubleshooting

### Common Issues

#### Source Attribution Problems
- Check metadata files in `data/metadata/`
- Verify source_id consistency across pipeline
- Review embedding storage metadata

#### YouTube Processing Errors
- Ensure yt-dlp is installed and updated
- Check video accessibility and transcript availability
- Verify URL format (youtube.com, youtu.be supported)

#### ChromaDB Dimension Mismatch
- Check embedding model consistency
- Clear vector store if changing models
- Verify OpenAI API key has access to chosen model

#### Memory Issues
- Reduce `MAX_CHUNK_TOKENS` for large documents
- Increase `CHUNK_OVERLAP` for better context
- Monitor container memory limits

### Debug Information

Enable debug logging by checking application logs:

```bash
# Docker
docker-compose logs -f rag-backend
docker-compose logs -f rag-frontend

# Local development
# Check console output for detailed source attribution logs
```

### Data Persistence
- **ChromaDB**: Stored in `data/vectorstore/`
- **Metadata**: JSON files in `data/metadata/`
- **Uploads**: Original files in `data/uploads/`

To reset all data:
```bash
rm -rf data/
```

## ⚡ Performance Optimization

- **Async Processing**: Non-blocking document ingestion
- **Connection Pooling**: Optimized OpenAI API usage
- **Caching**: Metadata file caching for faster retrieval
- **Chunking Strategy**: Balanced chunk size for optimal retrieval

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for the embedding and language models
- [ChromaDB](https://www.trychroma.com/) for the vector database
- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Streamlit](https://streamlit.io/) for the web interface
