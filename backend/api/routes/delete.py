from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import json
from pathlib import Path
import asyncio
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter()

@router.delete("/delete/{source_id}")
async def delete_source(source_id: str):
    """Delete a file or link and its embeddings"""
    try:
        logger.info(f"Starting deletion for source_id: {source_id}")
        
        metadata_path = Path(f"data/metadata/{source_id}.json")
        logger.info(f"Checking metadata path: {metadata_path}")
        
        if not metadata_path.exists():
            logger.warning(f"Metadata file not found: {metadata_path}")
            raise HTTPException(status_code=404, detail="Source not found")
        
        logger.info("Reading metadata file")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        logger.info(f"Metadata loaded: {metadata}")
        
        # Test graph creation separately
        logger.info("Attempting to create deletion graph")
        try:
            from backend.agents.graph import create_deletion_graph
            graph = create_deletion_graph()
            logger.info("Deletion graph created successfully")
        except Exception as graph_error:
            logger.error(f"Graph creation failed: {graph_error}")
            logger.error(f"Graph creation traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Graph creation failed: {str(graph_error)}")
        
        # Test graph invocation (delete embeddings from vector store)
        logger.info("Attempting to invoke deletion graph")
        try:
            result = await graph.ainvoke({
                "source_id": source_id,
                "metadata": metadata
            })
            logger.info(f"Graph invocation successful: {result}")
        except Exception as invoke_error:
            logger.error(f"Graph invocation failed: {invoke_error}")
            logger.error(f"Graph invocation traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Graph invocation failed: {str(invoke_error)}")
        
        # Delete the actual uploaded file (if it exists)
        logger.info("Deleting uploaded file")
        if metadata.get("type") == "file" and "path" in metadata:
            file_path = Path(metadata["path"])
            if file_path.exists():
                try:
                    file_path.unlink()  # Delete the file
                    logger.info(f"Deleted uploaded file: {file_path}")
                except Exception as file_error:
                    logger.warning(f"Failed to delete uploaded file {file_path}: {file_error}")
            else:
                logger.warning(f"Uploaded file not found: {file_path}")
        
        # Delete any associated chunk/transcript files
        logger.info("Deleting associated files")
        try:
            # Delete chunks file if it exists
            chunks_path = Path(f"data/chunks/{source_id}.json")
            if chunks_path.exists():
                chunks_path.unlink()
                logger.info(f"Deleted chunks file: {chunks_path}")
            
            # Delete transcript file if it exists
            transcript_path = Path(f"data/transcripts/{source_id}.txt")
            if transcript_path.exists():
                transcript_path.unlink()
                logger.info(f"Deleted transcript file: {transcript_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete associated files: {cleanup_error}")
        
        # IMPORTANT: Delete the metadata file (instead of updating it)
        logger.info("Deleting metadata file")
        try:
            metadata_path.unlink()  # This actually removes the file
            logger.info(f"Deleted metadata file: {metadata_path}")
        except Exception as metadata_error:
            logger.error(f"Failed to delete metadata file: {metadata_error}")
            raise HTTPException(status_code=500, detail=f"Failed to delete metadata: {str(metadata_error)}")
        
        return JSONResponse({
            "message": f"Source {source_id} deleted successfully",
            "deleted_chunks": result.get("deleted_chunks", 0),
            "deleted_files": ["metadata", "source_file", "chunks", "transcript"]
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Deletion failed with error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

@router.get("/list_sources")
async def list_sources():
    """List all uploaded sources"""
    try:
        logger.info("Listing sources")
        metadata_dir = Path("data/metadata")
        sources = []
        
        if not metadata_dir.exists():
            logger.info("Metadata directory doesn't exist, returning empty list")
            return JSONResponse({"sources": []})
        
        for metadata_file in metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                
                # Optional: Filter out sources marked as deleted (if you want to keep metadata but hide them)
                # if metadata.get("status") != "deleted":
                #     sources.append(metadata)
                
                # Since we're actually deleting files now, we don't need this filter
                sources.append(metadata)
                logger.debug(f"Added source: {metadata.get('id', 'unknown')}")
            except Exception as file_error:
                logger.warning(f"Failed to read metadata file {metadata_file}: {file_error}")
                continue
        
        logger.info(f"Found {len(sources)} sources")
        return JSONResponse({"sources": sources})
        
    except Exception as e:
        logger.error(f"Listing failed: {str(e)}")
        logger.error(f"Listing traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Listing failed: {str(e)}")