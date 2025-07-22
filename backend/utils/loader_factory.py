import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import logging

import PyPDF2
from docx import Document
import pandas as pd
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import requests

logger = logging.getLogger(__name__)

class DocumentLoader:
    @staticmethod
    def get_file_hash(content: bytes) -> str:
        """Generate hash for content tracking"""
        return hashlib.md5(content).hexdigest()
    
    @staticmethod
    def detect_file_type(filename: str) -> str:
        """Detect file type from extension"""
        extension = Path(filename).suffix.lower()
        type_mapping = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.html': 'html',
            '.htm': 'html'
        }
        return type_mapping.get(extension, 'unknown')
    
    @staticmethod
    def load_pdf(file_path: str) -> Dict[str, Any]:
        """Load PDF content"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                return {
                    'content': text,
                    'metadata': {
                        'source': file_path,
                        'type': 'pdf',
                        'pages': len(reader.pages)
                    }
                }
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {e}")
            raise
    
    @staticmethod
    def load_docx(file_path: str) -> Dict[str, Any]:
        """Load DOCX content"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            
            return {
                'content': text,
                'metadata': {
                    'source': file_path,
                    'type': 'docx',
                    'paragraphs': len(doc.paragraphs)
                }
            }
        except Exception as e:
            logger.error(f"Error loading DOCX {file_path}: {e}")
            raise
    
    @staticmethod
    def load_excel(file_path: str) -> Dict[str, Any]:
        """Load Excel content"""
        try:
            df = pd.read_excel(file_path)
            text = df.to_string()
            
            return {
                'content': text,
                'metadata': {
                    'source': file_path,
                    'type': 'excel',
                    'rows': len(df),
                    'columns': len(df.columns)
                }
            }
        except Exception as e:
            logger.error(f"Error loading Excel {file_path}: {e}")
            raise