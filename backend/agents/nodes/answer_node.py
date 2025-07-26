import logging
from typing import Dict, Any
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class AnswerNode:
    def __init__(self):
        self.rag_service = RAGService()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute answer generation node"""
        try:
            if "error" in state:
                logger.warning(f"Skipping answer generation due to previous error: {state.get('error')}")
                return state
            
            question = state.get("question")
            retrieved_chunks = state.get("retrieved_chunks", [])
            
            if not question:
                logger.error("No question found in state")
                state["error"] = "No question found in state"
                return state
            
            if not retrieved_chunks:
                logger.warning("No chunks retrieved, generating answer without context")
                state["answer"] = "I don't have enough information to answer your question. Please upload some relevant documents first."
                state["reasoning"] = "No relevant documents found in the knowledge base."
                return state
            
            logger.info(f"Generating answer for question: {question[:100]}...")
            
            result = await self.rag_service.generate_answer(
                question=question,
                chunks=retrieved_chunks
            )
            
            # Update state with results
            state["answer"] = result.get("answer", "Unable to generate answer")
            state["reasoning"] = result.get("reasoning", "")
            
            logger.info("Answer generation completed")
            
            return state
            
        except Exception as e:
            logger.error(f"Answer node failed: {str(e)}", exc_info=True)
            state["error"] = str(e)
            state["answer"] = "An error occurred while generating the answer."
            return state
