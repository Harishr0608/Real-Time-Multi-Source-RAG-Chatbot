import logging
from typing import Dict, Any
from backend.services.rag_service import RAGService
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class DeleteNode:
    def __init__(self):
        self.rag_service = RAGService()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deletion node"""
        try:
            source_id = state.get("source_id")
            if not source_id:
                logger.error("No source_id found in state")
                state["error"] = "No source_id found"
                return state
            
            logger.info(f"Deleting embeddings for {source_id}")
            
            # Delete embeddings from vector store
            result = await self.rag_service.delete_embeddings(source_id)
            
            # Clean up files
            self._cleanup_files(source_id, state.get("metadata", {}))
            
            state["deleted_chunks"] = result.get("deleted_count", 0)
            logger.info(f"Deletion completed for {source_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"Delete node failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            state["deleted_chunks"] = 0
            return state
    
    def _cleanup_files(self, source_id: str, metadata: Dict[str, Any]):
        """Clean up associated files"""
        try:
            # Remove uploaded file if it exists
            if metadata.get("type") == "file" and "path" in metadata:
                file_path = Path(metadata["path"])
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")
            
            # Remove chunks file
            chunks_file = Path(f"data/chunks/{source_id}.json")
            if chunks_file.exists():
                chunks_file.unlink()
                logger.info(f"Deleted chunks file: {chunks_file}")
            
            # Remove transcript file if it exists
            transcript_file = Path(f"data/transcripts/{source_id}.txt")
            if transcript_file.exists():
                transcript_file.unlink()
                logger.info(f"Deleted transcript file: {transcript_file}")
                
        except Exception as e:
            logger.warning(f"File cleanup failed: {str(e)}")