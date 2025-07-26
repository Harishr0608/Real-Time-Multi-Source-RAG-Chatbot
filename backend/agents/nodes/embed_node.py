import logging
from typing import Dict, Any
from backend.services.embedding_service import EmbeddingService
import asyncio

logger = logging.getLogger(__name__)

class EmbedNode:
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute embedding node with robust error handling"""
        try:
            if "error" in state:
                logger.warning(f"Skipping embedding due to previous error: {state.get('error')}")
                return state
            
            source_id = state.get("source_id")
            chunks = state.get("chunks", [])
            
            if not chunks:
                logger.error(f"No chunks found for {source_id}")
                state["error"] = "No chunks found for embedding"
                state["metadata"]["status"] = "failed"
                await self.save_metadata_to_file(source_id, state["metadata"])
                return state
            
            logger.info(f"Starting embedding for {source_id} with {len(chunks)} chunks")
            
            # Attempt embedding with timeout
            try:
                result = await asyncio.wait_for(
                    self.embedding_service.embed_chunks(chunks),
                    timeout=300  # 5 minute timeout
                )
                
                # Check if embedding was actually successful
                if result.get("success", False) and result.get("embedded_count", 0) > 0:
                    state["embedding_result"] = result
                    state["metadata"]["status"] = "completed"
                    state["metadata"]["embedded_count"] = result["embedded_count"]
                    logger.info(f"Successfully embedded {result['embedded_count']} chunks for {source_id}")
                else:
                    # Embedding failed or no chunks were embedded
                    error_msg = result.get("error", "Embedding failed - no chunks embedded")
                    state["error"] = error_msg
                    state["metadata"]["status"] = "failed"
                    state["metadata"]["error"] = error_msg
                    logger.error(f"Embedding failed for {source_id}: {error_msg}")
                
            except asyncio.TimeoutError:
                error_msg = "Embedding process timed out after 5 minutes"
                logger.error(f"{error_msg} for {source_id}")
                state["error"] = error_msg
                state["metadata"]["status"] = "failed"
                state["metadata"]["error"] = error_msg
            
            # Save metadata regardless of success/failure
            await self.save_metadata_to_file(source_id, state["metadata"])
            
            return state
            
        except Exception as e:
            logger.error(f"Embedding node failed for {source_id}: {str(e)}", exc_info=True)
            
            if "metadata" not in state:
                state["metadata"] = {}
            
            state["error"] = str(e)
            state["metadata"]["status"] = "failed"
            state["metadata"]["error"] = str(e)
            
            try:
                await self.save_metadata_to_file(source_id, state["metadata"])
            except:
                pass
            
            return state
    
    async def save_metadata_to_file(self, source_id: str, metadata: Dict[str, Any]):
        """Save metadata to file"""
        try:
            import json
            from pathlib import Path
            
            metadata_path = Path(f"data/metadata/{source_id}.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Metadata saved for {source_id} with status: {metadata.get('status')}")
            
        except Exception as e:
            logger.error(f"Failed to save metadata for {source_id}: {e}")