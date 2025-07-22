from typing import Dict, Any
from backend.agents.langgraph_agents import RetrieverAgent, AnswerSynthesisAgent
from backend.agents.langgraph_agents import RAGState

class RAGResponseService:
    def __init__(self, chroma_client, embeddings_model, llm_model):
        self.chroma_client = chroma_client
        self.embeddings_model = embeddings_model
        self.llm_model = llm_model
        
        # Initialize agents
        self.retriever_agent = RetrieverAgent(self.chroma_client, self.embeddings_model)
        self.answer_agent = AnswerSynthesisAgent(self.llm_model)
    
    def get_response(self, query: str) -> Dict[str, Any]:
        """Get RAG response for query"""
        try:
            # Create state
            state = RAGState()
            state.query = query
            
            # Process through agents
            state = self.retriever_agent.retrieve_documents(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            state = self.answer_agent.generate_answer(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            return {
                'success': True,
                'answer': state.answer,
                'retrieved_docs_count': len(state.retrieved_docs),
                'sources': [doc.metadata.get('source', 'Unknown') for doc in state.retrieved_docs]
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}