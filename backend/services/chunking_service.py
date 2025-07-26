import logging
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

logger = logging.getLogger(__name__)

class ChunkingService:
    def __init__(self):
        self.max_chunk_tokens = int(os.getenv("MAX_CHUNK_TOKENS", "500"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))
        
        # Approximate characters per token (rough estimate)
        self.chars_per_token = 4
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_tokens * self.chars_per_token,
            chunk_overlap=self.chunk_overlap * self.chars_per_token,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )
    
    async def chunk_text(self, source_id: str, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk text content into smaller pieces with metadata"""
        try:
            logger.info(f"Chunking text for {source_id}")
            
            if not content or content.strip() == "":
                logger.error(f"Empty content provided for chunking: {source_id}")
                return []
            
            # Split text into chunks
            text_chunks = self.text_splitter.split_text(content)
            
            if not text_chunks:
                logger.error(f"No chunks created for {source_id}")
                return []
            
            # Create chunk objects with metadata
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                if chunk_text.strip():  # Only add non-empty chunks
                    chunk = {
                        "chunk_id": f"{source_id}_{i}",
                        "source_id": source_id,
                        "text": chunk_text.strip(),
                        "chunk_index": i,
                        "metadata": metadata,  # IMPORTANT: Pass the original metadata
                        "filename": metadata.get("filename", "Unknown")  # Add filename directly
                    }
                    chunks.append(chunk)
            
            logger.info(f"Created {len(chunks)} chunks for {source_id}")
            
            # Update metadata with chunk count
            metadata["chunk_count"] = len(chunks)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Chunking failed for {source_id}: {str(e)}", exc_info=True)
            return []