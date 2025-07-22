import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=os.getenv("CHROMADB_DIR", "./chroma_storage"))

# Initialize models
embeddings_model = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
llm_model = OpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Initialize services
from backend.api.services.ingestion_service import IngestionService
from backend.api.services.rag_response_service import RAGResponseService
from backend.api.services.deletion_service import DeletionService

ingestion_service = IngestionService(chroma_client, embeddings_model)
rag_service = RAGResponseService(chroma_client, embeddings_model, llm_model)
deletion_service = DeletionService(chroma_client)

@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process file"""
    try:
        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process file
        result = ingestion_service.process_file_upload(file_path, content)
        
        # Clean up temporary file
        os.remove(file_path)
        
        if result['success']:
            return {
                "message": "File uploaded and processed successfully",
                "file_hash": result['file_hash'],
                "chunks_stored": result['chunks_stored']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_link")
async def upload_link(url: str = Form(...)):
    """Upload and process link"""
    try:
        result = ingestion_service.process_link_upload(url)
        
        if result['success']:
            return {
                "message": "Link processed successfully",
                "url_hash": result['url_hash'],
                "chunks_stored": result['chunks_stored']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_documents(query: str = Form(...)):
    """Query documents and get RAG response"""
    try:
        result = rag_service.get_response(query)
        
        if result['success']:
            return {
                "answer": result['answer'],
                "retrieved_docs_count": result['retrieved_docs_count'],
                "sources": result['sources']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_file/{file_hash}")
async def delete_file(file_hash: str):
    """Delete file by hash"""
    try:
        result = deletion_service.delete_by_hash(file_hash=file_hash)
        
        if result['success']:
            return {
                "message": "File deleted successfully",
                "deleted_count": result['deleted_count']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_link/{url_hash}")
async def delete_link(url_hash: str):
    """Delete link by hash"""
    try:
        result = deletion_service.delete_by_hash(url_hash=url_hash)
        
        if result['success']:
            return {
                "message": "Link deleted successfully",
                "deleted_count": result['deleted_count']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RAG Chatbot API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)