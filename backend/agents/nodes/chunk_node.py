import logging
from typing import Dict, Any
from backend.services.chunking_service import ChunkingService

logger = logging.getLogger(__name__)

class ChunkNode:
    def __init__(self):
        self.chunking_service = ChunkingService()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chunking node"""
        try:
            source_id = state.get("source_id")
            logger.info(f"Starting chunking for {source_id}")
            
            # Validate input
            if "content" not in state:
                logger.error(f"No content found in state for {source_id}")
                state["error"] = "No content available for chunking"
                if "metadata" not in state:
                    state["metadata"] = {}
                state["metadata"]["status"] = "failed"
                return state
            
            content = state["content"]
            if not content or content.strip() == "":
                logger.error(f"Empty content for {source_id}")
                state["error"] = "Empty content provided for chunking"
                state["metadata"]["status"] = "failed" 
                return state
            
            # Get metadata from state
            metadata = state.get("metadata", {})
            
            # Chunk the content
            chunks = await self.chunking_service.chunk_text(
                source_id=source_id,
                content=content,
                metadata=metadata  # Pass the full metadata including filename
            )
            
            if not chunks:
                logger.error(f"No chunks created for {source_id}")
                state["error"] = "Failed to create chunks"
                state["metadata"]["status"] = "failed"
                return state
            
            # Add chunks to state
            state["chunks"] = chunks
            state["metadata"]["status"] = "chunked"
            state["metadata"]["chunk_count"] = len(chunks)
            
            logger.info(f"Created {len(chunks)} chunks for {source_id}")
            logger.info(f"Chunking completed for {source_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"Chunking node failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            
            if "metadata" not in state:
                state["metadata"] = {}
            state["metadata"]["status"] = "failed"
            return state