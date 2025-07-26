from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from backend.agents.graph import create_rag_graph

router = APIRouter()
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    include_sources: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    reasoning: str

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the document store using RAG with Chain-of-Thought"""
    try:
        logger.info(f"Processing query: {request.question[:100]}...")
        
        # Create and run RAG graph
        graph = create_rag_graph()
        result = await graph.ainvoke({
            "question": request.question,
            "top_k": request.top_k,
            "include_sources": request.include_sources,
            "retrieved_chunks": [],
            "answer": "",
            "sources": [],
            "reasoning": ""
        })
        
        logger.info(f"Query processed successfully")
        
        # FIXED: Debug the actual structure we receive from RAG
        sources = result.get("sources", [])
        logger.info(f"DEBUG: Received {len(sources)} sources from RAG service")
        
        if sources:
            logger.info(f"DEBUG: First source structure: {sources[0]}")
            logger.info(f"DEBUG: First source keys: {list(sources[0].keys()) if sources[0] else 'No keys'}")
        
        # FIXED: Enhanced source formatting with direct metadata lookup
        formatted_sources = []
        
        # Group sources by source_id to avoid duplicates and get metadata
        unique_sources = {}
        for source in sources:
            source_id = source.get('source_id', 'unknown')
            if source_id not in unique_sources:
                unique_sources[source_id] = source
            else:
                # Keep the one with higher relevance
                if source.get('relevance_score', 0) > unique_sources[source_id].get('relevance_score', 0):
                    unique_sources[source_id] = source
        
        # Now load metadata for each unique source and format properly
        for source_id, source in unique_sources.items():
            # Try to load metadata directly from file for this source_id
            filename = "Unknown"
            
            try:
                import json
                from pathlib import Path
                
                metadata_path = Path(f"data/metadata/{source_id}.json")
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    filename = metadata.get('filename', 'Unknown')
                    logger.info(f"DEBUG: Loaded filename from metadata file: '{filename}'")
                else:
                    logger.warning(f"DEBUG: Metadata file not found: {metadata_path}")
            except Exception as e:
                logger.error(f"DEBUG: Error loading metadata for {source_id}: {e}")
            
            # If metadata loading failed, try other extraction methods
            if filename == "Unknown":
                # Try from source object itself
                if source.get('filename') and source.get('filename') not in ['Unknown', '']:
                    filename = source['filename']
                elif source.get('name') and source.get('name') not in ['Unknown', '']:
                    filename = source['name']
                elif source.get('url_or_path'):
                    url_or_path = source.get('url_or_path', '')
                    if not url_or_path.startswith('http'):
                        from pathlib import Path
                        filename = Path(url_or_path).name
                    else:
                        filename = url_or_path
            
            formatted_source = {
                "citation_number": source.get("citation_number", 1),
                "source_id": source_id,
                "name": filename,  # This is what frontend uses
                "filename": filename,  # Backup field
                "type": source.get("type", "Document"),
                "url_or_path": source.get("url_or_path", ""),
                "relevance_score": source.get("relevance_score", 0.0),
                "chunk_count": source.get("chunk_count", 1),
                "text": source.get("text", source.get("preview", ""))[:200] + "..." if len(source.get("text", source.get("preview", ""))) > 200 else source.get("text", source.get("preview", "")),
                "chunk_id": source.get("chunk_id", ""),
                "preview": source.get("preview", "")
            }
            
            # Debug logging to see what we're sending to frontend
            logger.info(f"Formatted source for frontend: name='{formatted_source['name']}', filename='{formatted_source['filename']}', type='{formatted_source['type']}', source_id='{source_id}'")
            
            formatted_sources.append(formatted_source)
        
        response_data = {
            "success": True,
            "data": {
                "answer": result.get("answer", "No answer generated"),
                "sources": formatted_sources,
                "reasoning": result.get("reasoning", "Analysis completed based on context."),
                "retrieved_docs_count": len(formatted_sources)
            }
        }
        
        # Debug logging to see the complete response
        logger.info(f"Sending response with {len(formatted_sources)} unique sources")
        for i, source in enumerate(formatted_sources):
            logger.info(f"  Source {i}: {source.get('name', 'NO_NAME')} (ID: {source.get('source_id', 'NO_ID')})")
        
        return JSONResponse(response_data)
        
    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Query failed: {str(e)}"
        })

@router.post("/chat")
async def chat_with_documents(request: QueryRequest):
    """Chat interface with conversation history"""
    try:
        logger.info(f"Processing chat: {request.question[:100]}...")
        # For now, same as query - can be extended for conversation memory
        return await query_documents(request)
        
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Chat failed: {str(e)}"
        })