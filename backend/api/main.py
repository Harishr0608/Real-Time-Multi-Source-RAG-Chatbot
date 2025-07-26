from dotenv import load_dotenv
import os
import gc

# Load environment variables FIRST
load_dotenv()

# Disable ChromaDB telemetry before any other imports
os.environ["ANONYMIZED_TELEMETRY"] = "false"

# Configure memory management
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"  # For macOS
gc.set_threshold(700, 10, 10)  # Reduce garbage collection pressure

# Now continue with your existing imports
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import uvicorn
import traceback
import sys
from pathlib import Path

from backend.api.routes import upload, delete, query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create data directories
directories = ["data/uploads", "data/transcripts", "data/chunks", "data/metadata"]
for directory in directories:
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Directory created/verified: {directory}")
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")

app = FastAPI(
    title="RAG Chatbot API",
    description="Real-time document ingestion and retrieval system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler (only one, after app creation)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Force garbage collection to prevent memory leaks
    gc.collect()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "error_type": type(exc).__name__
        }
    )

# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )

# Include routers with error handling
try:
    app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
    logger.info("Upload router included successfully")
except Exception as e:
    logger.error(f"Failed to include upload router: {e}")

try:
    app.include_router(delete.router, prefix="/api/v1", tags=["delete"])
    logger.info("Delete router included successfully")
except Exception as e:
    logger.error(f"Failed to include delete router: {e}")

try:
    app.include_router(query.router, prefix="/api/v1", tags=["query"])
    logger.info("Query router included successfully")
except Exception as e:
    logger.error(f"Failed to include query router: {e}")

@app.get("/")
async def root():
    return {"message": "RAG Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "directories": directories}

# Test endpoint to check if graph creation works
@app.get("/test/graph")
async def test_graph():
    """Test endpoint to check if graph creation works"""
    try:
        from backend.agents.graph import create_ingestion_graph
        graph = create_ingestion_graph()
        return {"status": "Graph creation successful", "graph_type": str(type(graph))}
    except Exception as e:
        logger.error(f"Graph creation test failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "Graph creation failed", "error": str(e)}
        )

# Additional debug endpoint for collection stats
@app.get("/test/collection")
async def test_collection():
    """Test endpoint to check ChromaDB collection status"""
    try:
        from backend.services.rag_service import RAGService
        rag_service = RAGService()
        stats = rag_service.get_collection_stats()
        return {"status": "Collection check successful", "stats": stats}
    except Exception as e:
        logger.error(f"Collection test failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "Collection check failed", "error": str(e)}
        )

if __name__ == "__main__":
    logger.info("Starting RAG Chatbot API server...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        reload=False  # Set to True for development
    )