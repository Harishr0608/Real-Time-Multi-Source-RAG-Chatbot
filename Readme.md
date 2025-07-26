# RAG Chatbot

A production-ready Retrieval-Augmented Generation (RAG) chatbot built with FastAPI, Streamlit, LangGraph, and ChromaDB.

## Features

- **Multi-format Support**: PDF, DOCX, XLSX, CSV, TXT, HTML, YouTube videos
- **Real-time Processing**: Async document ingestion with LangGraph
- **Smart Chunking**: Token-based text splitting with overlap
- **Vector Search**: ChromaDB for similarity search
- **Chain-of-Thought**: Reasoning-based answer generation
- **Web Interface**: Clean Streamlit UI
- **Docker Ready**: Complete containerization

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd rag_chatbot
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Run with Docker**
   ```bash
   docker-compose up --build
   ```

3. **Access Applications**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Development Setup

1. **Install Dependencies**
   ```bash
   pip install -r docker/requirements.txt
   ```

2. **Run Services**
   ```bash
   # Backend
   uvicorn backend.api.main:app --reload

   # Frontend
   streamlit run frontend/streamlit_app.py
   ```

## API Endpoints

- `POST /api/v1/upload_file` - Upload document
- `POST /api/v1/upload_link` - Process web link
- `DELETE /api/v1/delete/{source_id}` - Delete source
- `POST /api/v1/query` - Query documents
- `GET /api/v1/list_sources` - List uploaded sources

## Configuration

Edit `configs/config.yaml` or environment variables:

- `MAX_CHUNK_TOKENS`: Maximum tokens per chunk (default: 500)
- `CHUNK_OVERLAP`: Token overlap between chunks (default: 50)
- `TOP_K`: Number of chunks to retrieve (default: 5)
- `LLM_MODEL`: OpenAI model for answers (default: gpt-3.5-turbo)
- `EMBED_MODEL`: OpenAI embedding model (default: text-embedding-ada-002)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │────│    FastAPI      │────│    ChromaDB     │
│   Frontend      │    │    Backend      │    │  Vector Store   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   LangGraph     │
                       │    Agents       │
                       └─────────────────┘
```

### Components

1. **FastAPI Backend**: REST API with async endpoints
2. **LangGraph Agents**: Orchestrate ingestion and RAG workflows
3. **ChromaDB**: Vector database for embeddings
4. **Streamlit Frontend**: Interactive web interface
5. **Docker**: Containerized deployment

## Supported Sources

- **Documents**: PDF, DOCX, XLSX, CSV, TXT, MD
- **Web Pages**: Any HTML page via URL
- **YouTube**: Video transcripts via yt-dlp

## Workflow

### Document Ingestion
1. **Upload** → File/Link received
2. **Extract** → Text extraction via appropriate loader
3. **Clean** → Remove boilerplate and normalize
4. **Chunk** → Split into token-limited segments
5. **Embed** → Generate embeddings via OpenAI
6. **Store** → Save to ChromaDB with metadata

### Query Processing
1. **Embed Query** → Generate query embedding
2. **Retrieve** → Find similar chunks via vector search
3. **Reason** → Chain-of-Thought prompt construction
4. **Generate** → LLM produces reasoned answer
5. **Present** → Return answer with sources

## Monitoring

- Health checks at `/health`
- Structured logging with rotation
- Processing status tracking
- Error handling and retries

## Development

### Project Structure
```
backend/
├── api/routes/          # FastAPI endpoints
├── services/            # Business logic
├── agents/              # LangGraph workflows
└── utils/               # Helper utilities

frontend/
└── streamlit_app.py     # UI application

configs/
├── config.yaml          # Application settings
└── logging.yaml         # Logging configuration
```

### Adding New File Types

1. Create loader in `backend/utils/loader_factory.py`
2. Register in `LoaderFactory.loaders` dict
3. Update supported types in config

### Extending Agents

1. Create new node in `backend/agents/nodes/`
2. Add to workflow in `backend/agents/graph.py`
3. Update service layer as needed

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies installed
2. **API Key Errors**: Check `.env` file configuration
3. **Memory Issues**: Reduce `MAX_CHUNK_TOKENS` for large documents
4. **YouTube Errors**: Verify `yt-dlp` installation and video accessibility

### Logs

Check application logs:
```bash
# Docker
docker-compose logs rag-backend
docker-compose logs rag-frontend

# Local
tail -f logs/app.log
```

## License

MIT License - see LICENSE file for details.