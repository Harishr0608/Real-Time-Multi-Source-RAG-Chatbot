import logging
from typing import Dict, Any
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class RetrieveNode:
    def __init__(self):
        self.rag_service = RAGService()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retrieval node"""
        try:
            question = state.get("question")
            if not question:
                logger.error("No question found in state")
                state["error"] = "No question found in state"
                return state
            
            logger.info(f"Retrieving chunks for question: {question[:100]}...")
            
            chunks = await self.rag_service.retrieve_relevant_chunks(
                question=question,
                top_k=state.get("top_k", 5)
            )
            
            state["retrieved_chunks"] = chunks
            
            # Also format sources for response
            sources = []
            for chunk in chunks:
                sources.append({
                    "filename": chunk.get("filename", "Unknown"),
                    "text": chunk.get("text", "")[:200] + "...",  # Preview
                    "relevance_score": chunk.get("score", 0.0),
                    "chunk_id": chunk.get("chunk_id", "")
                })
            
            state["sources"] = sources
            logger.info(f"Retrieved {len(chunks)} chunks")
            
            return state
            
        except Exception as e:
            logger.error(f"Retrieval node failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
