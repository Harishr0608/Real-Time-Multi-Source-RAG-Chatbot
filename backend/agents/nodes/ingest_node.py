import logging
from typing import Dict, Any
from backend.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

class IngestNode:
    def __init__(self):
        self.ingestion_service = IngestionService()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ingestion node"""
        try:
            source_id = state.get("source_id")
            logger.info(f"Starting ingestion for {source_id}")
            
            # Add logging to see what we're sending to the service
            logger.info(f"Ingestion input - source_id: {state.get('source_id')}")
            logger.info(f"Ingestion input - source_type: {state.get('source_type')}")
            logger.info(f"Ingestion input - source_path: {state.get('source_path')}")
            
            result = await self.ingestion_service.process_source(
                source_id=state["source_id"],
                source_type=state["source_type"],
                source_path=state["source_path"],
                metadata=state["metadata"]
            )
            
            # IMPORTANT: Add logging to see what the service returns
            logger.info(f"Ingestion service returned keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            logger.info(f"Ingestion service result: {result}")
            
            # Check if result contains content
            if isinstance(result, dict):
                if "content" in result:
                    logger.info(f"Content found in result, length: {len(result['content'])}")
                elif "text" in result:
                    # If service returns 'text' instead of 'content', rename it
                    logger.info(f"Found 'text' key, renaming to 'content'. Length: {len(result['text'])}")
                    result["content"] = result["text"]
                    del result["text"]  # Remove the old key
                else:
                    logger.error(f"No 'content' or 'text' key found in result. Available keys: {list(result.keys())}")
                    state["error"] = "No content returned from ingestion service"
                    state["metadata"]["status"] = "failed"
                    return state
            else:
                logger.error(f"Ingestion service returned non-dict: {type(result)}")
                state["error"] = "Ingestion service returned invalid result"
                state["metadata"]["status"] = "failed"
                return state
            
            # Update state with the result
            state.update(result)
            
            # Verify content is in state
            if "content" not in state:
                logger.error("Content not found in state after update")
                state["error"] = "Content not found in state after ingestion"
                state["metadata"]["status"] = "failed"
                return state
            
            # Ensure metadata exists and update status
            if "metadata" not in state:
                state["metadata"] = {}
            state["metadata"]["status"] = "ingested"
            
            logger.info(f"Ingestion completed for {source_id}. Content length: {len(state['content'])}")
            logger.info(f"Final state keys: {list(state.keys())}")
            
            return state
            
        except Exception as e:
            logger.error(f"Ingestion node failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            
            # Ensure metadata exists before updating
            if "metadata" not in state:
                state["metadata"] = {}
            state["metadata"]["status"] = "failed"
            return state
