import logging
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio

from backend.utils.loader_factory import LoaderFactory
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        self.loader_factory = LoaderFactory()
        self.text_cleaner = TextCleaner()
    
    async def process_source(self, source_id: str, source_type: str, source_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process a source (file or link) and extract clean text"""
        try:
            logger.info(f"Processing {source_type}: {source_path}")
            
            # Load content based on type
            if source_type == "file":
                loader = self.loader_factory.get_loader(Path(source_path))
                raw_text = await loader.load()
            elif source_type == "link":
                loader = self.loader_factory.get_link_loader(source_path)
                raw_text = await loader.load()
            else:
                raise ValueError(f"Unknown source type: {source_type}")
            
            # Validate that we got content
            if not raw_text or raw_text.strip() == "":
                raise ValueError(f"No content extracted from {source_path}")
            
            # Clean the text
            cleaned_text = self.text_cleaner.clean(raw_text)
            
            # Validate cleaned text
            if not cleaned_text or cleaned_text.strip() == "":
                raise ValueError(f"No content after cleaning from {source_path}")
            
            logger.info(f"Successfully extracted {len(cleaned_text)} characters from {source_path}")
            
            # Update metadata
            metadata.update({
                "text_length": len(cleaned_text),
                "raw_text_length": len(raw_text),
                "status": "text_extracted"
            })
            
            # IMPORTANT: Return "content" not "text" to match what chunk_node expects
            return {
                "source_id": source_id,
                "content": cleaned_text,  # Changed from "text" to "content"
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Ingestion failed for {source_id}: {str(e)}", exc_info=True)
            metadata["status"] = "failed"
            metadata["error"] = str(e)
            
            # Still return the expected structure, but with error info
            return {
                "source_id": source_id,
                "content": "",  # Empty content on error
                "metadata": metadata,
                "error": str(e)
            }