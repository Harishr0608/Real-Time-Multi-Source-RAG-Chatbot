import os
import openai
import logging
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any
import asyncio
from pathlib import Path
import json

load_dotenv()
logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)
        self.client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=3)
    
    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Embed chunks with EXTENSIVE debugging"""
        try:
            source_id = chunks[0].get("source_id") if chunks else "unknown"
            logger.info(f"🔍 DEBUG: Starting embedding for source_id: {source_id}")
            logger.info(f"🔍 DEBUG: Number of chunks to embed: {len(chunks)}")
            
            # DEBUG: Log the first chunk to see what data we have
            if chunks:
                first_chunk = chunks[0]
                logger.info(f"🔍 DEBUG: First chunk keys: {list(first_chunk.keys())}")
                logger.info(f"🔍 DEBUG: First chunk source_id: {first_chunk.get('source_id', 'MISSING')}")
                logger.info(f"🔍 DEBUG: First chunk filename: {first_chunk.get('filename', 'MISSING')}")
                logger.info(f"🔍 DEBUG: First chunk metadata: {first_chunk.get('metadata', 'MISSING')}")
            
            texts = [chunk.get("text", "") for chunk in chunks]
            if not texts or all(not text.strip() for text in texts):
                logger.warning(f"No valid text found in chunks for {source_id}")
                return {"embedded_count": 0, "success": False, "error": "No valid text"}
            
            # Try embedding
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔍 DEBUG: Embedding attempt {attempt + 1}/{max_retries} for {source_id}")
                    
                    response = await self.client.embeddings.create(
                        model=os.getenv("EMBED_MODEL", "text-embedding-3-large"),
                        input=texts
                    )
                    
                    # Store embeddings with debugging
                    embedded_count = await self._store_embeddings_debug(chunks, response.data, source_id)
                    
                    logger.info(f"✅ Successfully embedded {embedded_count} chunks for {source_id}")
                    return {"embedded_count": embedded_count, "success": True}
                    
                except Exception as e:
                    logger.error(f"❌ Embedding attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        return {"embedded_count": 0, "success": False, "error": str(e)}
                    await asyncio.sleep(2 ** attempt)
                        
        except Exception as e:
            logger.error(f"❌ Embedding failed for {source_id}: {str(e)}", exc_info=True)
            return {"embedded_count": 0, "success": False, "error": str(e)}
    
    async def _store_embeddings_debug(self, chunks: List[Dict], embeddings_data: List, source_id: str) -> int:
        """Store embeddings with EXTENSIVE debugging"""
        try:
            logger.info(f"🔍 DEBUG: Starting to store embeddings for {source_id}")
            
            # Load metadata with debugging
            source_metadata = await self._load_source_metadata_debug(source_id)
            
            documents = []
            metadatas = []
            ids = []
            embeddings = []
            
            for i, (chunk, embedding_obj) in enumerate(zip(chunks, embeddings_data)):
                # DEBUG: Log what we're processing
                logger.info(f"🔍 DEBUG: Processing chunk {i} for {source_id}")
                logger.info(f"🔍 DEBUG: Chunk keys: {list(chunk.keys())}")
                
                documents.append(chunk.get("text", ""))
                
                # Get filename with extensive debugging
                filename = "UNKNOWN_DEBUG"
                
                # Try from source metadata first
                if source_metadata.get("filename"):
                    filename = source_metadata["filename"]
                    logger.info(f"🔍 DEBUG: Got filename from source_metadata: '{filename}'")
                
                # Try from chunk metadata
                elif chunk.get("filename"):
                    filename = chunk["filename"]
                    logger.info(f"🔍 DEBUG: Got filename from chunk: '{filename}'")
                
                # Try from chunk metadata dict
                elif chunk.get("metadata", {}).get("filename"):
                    filename = chunk["metadata"]["filename"]
                    logger.info(f"🔍 DEBUG: Got filename from chunk.metadata: '{filename}'")
                
                # Try from source metadata URL for links
                elif source_metadata.get("url"):
                    chunk_text = chunk.get("text", "")
                    if 'YOUTUBE VIDEO METADATA' in chunk_text and 'Title:' in chunk_text:
                        title_lines = [line for line in chunk_text.split('\n') if line.startswith('Title:')]
                        if title_lines:
                            filename = title_lines[0].replace('Title:', '').strip()
                            logger.info(f"🔍 DEBUG: Extracted YouTube title: '{filename}'")
                    else:
                        filename = source_metadata["url"]
                        logger.info(f"🔍 DEBUG: Using URL as filename: '{filename}'")
                
                else:
                    logger.error(f"❌ DEBUG: Could not determine filename for {source_id} chunk {i}")
                    logger.error(f"❌ DEBUG: source_metadata: {source_metadata}")
                    logger.error(f"❌ DEBUG: chunk keys: {list(chunk.keys())}")
                    if 'metadata' in chunk:
                        logger.error(f"❌ DEBUG: chunk.metadata keys: {list(chunk['metadata'].keys()) if isinstance(chunk['metadata'], dict) else 'Not a dict'}")
                
                # Create metadata for ChromaDB
                chunk_metadata = {
                    "source_id": source_id,
                    "chunk_id": f"{source_id}_{i}",
                    "filename": filename,  # This is what RAG retrieval will use
                    "chunk_index": i,
                    "source_type": source_metadata.get("type", "unknown")
                }
                
                # Add URL or path
                if source_metadata.get("type") == "link":
                    chunk_metadata["url"] = source_metadata.get("url", "")
                elif source_metadata.get("type") == "file":
                    chunk_metadata["path"] = source_metadata.get("path", "")
                
                metadatas.append(chunk_metadata)
                ids.append(f"{source_id}_{i}")
                embeddings.append(embedding_obj.embedding)
                
                logger.info(f"✅ DEBUG: Prepared chunk {i} metadata: filename='{filename}', source_type='{chunk_metadata['source_type']}'")
            
            # Store in vector database
            from backend.services.rag_service import RAGService
            rag_service = RAGService()
            
            logger.info(f"🔍 DEBUG: About to store {len(documents)} embeddings with metadata")
            await rag_service.add_embeddings(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
            
            logger.info(f"✅ DEBUG: Successfully stored {len(documents)} embeddings for {source_id}")
            return len(documents)
            
        except Exception as e:
            logger.error(f"❌ DEBUG: Failed to store embeddings for {source_id}: {e}", exc_info=True)
            raise
    
    async def _load_source_metadata_debug(self, source_id: str) -> Dict[str, Any]:
        """Load source metadata with EXTENSIVE debugging"""
        try:
            metadata_path = Path(f"data/metadata/{source_id}.json")
            logger.info(f"🔍 DEBUG: Looking for metadata file: {metadata_path}")
            logger.info(f"🔍 DEBUG: File exists: {metadata_path.exists()}")
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                logger.info(f"✅ DEBUG: Successfully loaded metadata for {source_id}:")
                logger.info(f"🔍 DEBUG: Metadata keys: {list(metadata.keys())}")
                logger.info(f"🔍 DEBUG: filename: '{metadata.get('filename', 'MISSING')}'")
                logger.info(f"🔍 DEBUG: type: '{metadata.get('type', 'MISSING')}'")
                logger.info(f"🔍 DEBUG: url: '{metadata.get('url', 'MISSING')}'")
                logger.info(f"🔍 DEBUG: Full metadata: {metadata}")
                
                return metadata
            else:
                logger.error(f"❌ DEBUG: Metadata file not found: {metadata_path}")
                
                # Check if directory exists
                metadata_dir = Path("data/metadata")
                if metadata_dir.exists():
                    available_files = list(metadata_dir.glob("*.json"))
                    logger.error(f"❌ DEBUG: Available metadata files: {[f.name for f in available_files]}")
                else:
                    logger.error(f"❌ DEBUG: Metadata directory doesn't exist: {metadata_dir}")
                
        except Exception as e:
            logger.error(f"❌ DEBUG: Error loading metadata for {source_id}: {e}", exc_info=True)
        
        return {"filename": "METADATA_LOAD_FAILED", "type": "unknown"}
