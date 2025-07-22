import os
import hashlib
from typing import Dict, Any
from backend.agents.langgraph_agents import *
from backend.utils.loader_factory import DocumentLoader
from backend.utils.link_parser import LinkParser
from backend.utils.cleaner import TextCleaner

class IngestionService:
    def __init__(self, chroma_client, embeddings_model):
        self.chroma_client = chroma_client
        self.embeddings_model = embeddings_model
        self.loader_factory = DocumentLoader()
        self.link_parser = LinkParser()
        self.text_cleaner = TextCleaner()
        
        # Initialize agents
        self.file_agent = FileIngestionAgent(self.loader_factory, self.text_cleaner)
        self.link_agent = LinkIngestionAgent(self.link_parser, self.text_cleaner)
        self.embedding_agent = EmbeddingAgent(self.chroma_client, self.embeddings_model)
    
    def process_file_upload(self, file_path: str, file_content: bytes) -> Dict[str, Any]:
        """Process uploaded file"""
        try:
            # Create state
            state = RAGState()
            file_hash = hashlib.md5(file_content).hexdigest()
            state.metadata = {
                'file_path': file_path,
                'file_hash': file_hash
            }
            
            # Process through agents
            state = self.file_agent.process_file(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            state = self.embedding_agent.embed_and_store(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            return {
                'success': True,
                'file_hash': file_hash,
                'chunks_stored': state.metadata.get('stored_count', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def process_link_upload(self, url: str) -> Dict[str, Any]:
        """Process link upload"""
        try:
            # Create state
            state = RAGState()
            url_hash = hashlib.md5(url.encode()).hexdigest()
            state.metadata = {
                'url': url,
                'url_hash': url_hash
            }
            
            # Process through agents
            state = self.link_agent.process_link(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            state = self.embedding_agent.embed_and_store(state)
            if state.error:
                return {'success': False, 'error': state.error}
            
            return {
                'success': True,
                'url_hash': url_hash,
                'chunks_stored': state.metadata.get('stored_count', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}