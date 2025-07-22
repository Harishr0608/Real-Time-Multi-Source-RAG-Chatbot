from typing import Dict, Any
from backend.agents.langgraph_agents import DeletionAgent
from backend.agents.langgraph_agents import RAGState


class DeletionService:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client
        self.deletion_agent = DeletionAgent(self.chroma_client)
    
    def delete_by_hash(self, file_hash: str = None, url_hash: str = None) -> Dict[str, Any]:
        """Delete documents by hash"""
        try:
            state = RAGState()
            state.metadata = {}
            
            if file_hash:
                state.metadata['file_hash'] = file_hash
            elif url_hash:
                state.metadata['url_hash'] = url_hash
            else:
                return {'success': False, 'error': 'No hash provided'}
            
            state = self.deletion_agent.delete_documents(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            return {
                'success': True,
                'deleted_count': state.metadata.get('deleted_count', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}