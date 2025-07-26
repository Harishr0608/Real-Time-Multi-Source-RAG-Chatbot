from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
import hashlib
import json
from pathlib import Path
import asyncio
import logging
from datetime import datetime
import os

from backend.agents.graph import create_ingestion_graph
from backend.utils.loader_factory import LoaderFactory

router = APIRouter()
logger = logging.getLogger(__name__)

async def process_file_async(graph, data):
    """Separate async function with error handling and metadata update"""
    try:
        source_id = data["source_id"]
        logger.info(f"Starting async processing for {source_id}")
        
        result = await graph.ainvoke(data)
        logger.info(f"Processing completed for {source_id}")
        
        # Update metadata file with completion status
        metadata_path = Path(f"data/metadata/{source_id}.json")
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            # Update status based on result
            if "error" in result:
                metadata["status"] = "failed"
                metadata["error"] = result["error"]
                logger.error(f"Processing failed for {source_id}: {result['error']}")
            else:
                metadata["status"] = "completed"
                metadata["completed_time"] = datetime.now().isoformat()
                
                # Add processing statistics
                if "metadata" in result and isinstance(result["metadata"], dict):
                    result_metadata = result["metadata"]
                    if "chunk_count" in result_metadata:
                        metadata["chunk_count"] = result_metadata["chunk_count"]
                    if "embedded_count" in result_metadata:
                        metadata["embedded_count"] = result_metadata["embedded_count"]
                    if "text_length" in result_metadata:
                        metadata["text_length"] = result_metadata["text_length"]
                
                logger.info(f"Processing completed successfully for {source_id}")
            
            # Save updated metadata
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Metadata updated for {source_id} - status: {metadata['status']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Async processing failed for {data['source_id']}: {str(e)}", exc_info=True)
        
        # Update metadata to reflect error
        try:
            metadata_path = Path(f"data/metadata/{data['source_id']}.json")
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                metadata["status"] = "failed"
                metadata["error"] = str(e)
                metadata["failed_time"] = datetime.now().isoformat()
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                logger.info(f"Metadata updated with error for {data['source_id']}")
        except Exception as meta_error:
            logger.error(f"Failed to update metadata with error: {meta_error}")

@router.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file"""
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Calculate file hash for deduplication
        content = await file.read()
        file_hash = hashlib.md5(content).hexdigest()
        
        # Ensure directories exist
        Path("data/uploads").mkdir(parents=True, exist_ok=True)
        Path("data/metadata").mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = Path(f"data/uploads/{file_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create metadata with proper timestamp
        current_time = datetime.now().isoformat()
        metadata = {
            "id": file_id,
            "filename": file.filename,
            "hash": file_hash,
            "type": "file",
            "status": "processing",
            "path": str(file_path),
            "upload_time": current_time,
            "file_size": len(content)
        }
        
        metadata_path = Path(f"data/metadata/{file_id}.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"File uploaded: {file.filename} with ID: {file_id}")
        
        # Start async processing with LangGraph
        try:
            graph = create_ingestion_graph()
            asyncio.create_task(
                process_file_async(graph, {
                    "source_id": file_id,
                    "source_type": "file",
                    "source_path": str(file_path),
                    "metadata": metadata
                })
            )
            logger.info(f"Async processing started for {file_id}")
        except Exception as graph_error:
            logger.error(f"Failed to start processing for {file_id}: {graph_error}")
            # Update metadata with error
            metadata["status"] = "failed"
            metadata["error"] = str(graph_error)
            metadata["failed_time"] = current_time
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        return JSONResponse({
            "message": "File uploaded successfully",
            "file_id": file_id,
            "status": "processing",
            "filename": file.filename,
            "file_size": len(content)
        })
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload_link")
async def upload_link(url: str = Form(...)):
    """Upload and process a web link or YouTube URL"""
    try:
        link_id = str(uuid.uuid4())
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Ensure directories exist
        Path("data/metadata").mkdir(parents=True, exist_ok=True)
        
        # Create metadata with proper timestamp
        current_time = datetime.now().isoformat()
        metadata = {
            "id": link_id,
            "url": url,
            "hash": url_hash,
            "type": "link",
            "status": "processing",
            "upload_time": current_time
        }
        
        metadata_path = Path(f"data/metadata/{link_id}.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Link submitted: {url} with ID: {link_id}")
        
        # Start async processing
        try:
            graph = create_ingestion_graph()
            asyncio.create_task(
                process_file_async(graph, {
                    "source_id": link_id,
                    "source_type": "link",
                    "source_path": url,
                    "metadata": metadata
                })
            )
            logger.info(f"Async processing started for {link_id}")
        except Exception as graph_error:
            logger.error(f"Failed to start processing for {link_id}: {graph_error}")
            # Update metadata with error
            metadata["status"] = "failed"
            metadata["error"] = str(graph_error)
            metadata["failed_time"] = current_time
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        
        return JSONResponse({
            "message": "Link submitted successfully",
            "link_id": link_id,
            "status": "processing",
            "url": url
        })
        
    except Exception as e:
        logger.error(f"Link processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Link processing failed: {str(e)}")

@router.get("/status/{source_id}")
async def get_status(source_id: str):
    """Get processing status of a file or link"""
    try:
        metadata_path = Path(f"data/metadata/{source_id}.json")
        if not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Source not found")
        
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        return JSONResponse(metadata)
        
    except Exception as e:
        logger.error(f"Status check failed for {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if directories exist
        uploads_dir = Path("data/uploads")
        metadata_dir = Path("data/metadata")
        
        return JSONResponse({
            "status": "healthy",
            "uploads_dir_exists": uploads_dir.exists(),
            "metadata_dir_exists": metadata_dir.exists(),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
