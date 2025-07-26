from pathlib import Path
from typing import Union
import mimetypes
from abc import ABC, abstractmethod
import PyPDF2
from docx import Document
import pandas as pd

from backend.utils.base_loaders import BaseLoader
from backend.utils.link_parser import LinkParser

class PDFLoader(BaseLoader):
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    async def load(self) -> str:
        try:
            with open(self.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            raise ImportError("PyPDF2 is required for PDF processing")

class DocxLoader(BaseLoader):
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    async def load(self) -> str:
        try:
            doc = Document(self.file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            raise ImportError("python-docx is required for DOCX processing")

class ExcelLoader(BaseLoader):
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    async def load(self) -> str:
        try:
            df = pd.read_excel(self.file_path)
            return df.to_string()
        except ImportError:
            raise ImportError("pandas and openpyxl are required for Excel processing")

class CSVLoader(BaseLoader):
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    async def load(self) -> str:
        try:
            df = pd.read_csv(self.file_path)
            return df.to_string()
        except ImportError:
            raise ImportError("pandas is required for CSV processing")

class TextLoader(BaseLoader):
    def __init__(self, file_path: Path):
        self.file_path = file_path
    
    async def load(self) -> str:
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return file.read()

class LoaderFactory:
    def __init__(self):
        self.loaders = {
            '.pdf': PDFLoader,
            '.docx': DocxLoader,
            '.xlsx': ExcelLoader,
            '.csv': CSVLoader,
            '.txt': TextLoader,
            '.md': TextLoader,
            '.html': TextLoader
        }
    
    def get_loader(self, file_path: Path) -> BaseLoader:
        """Get appropriate loader for file type"""
        suffix = file_path.suffix.lower()
        
        if suffix in self.loaders:
            return self.loaders[suffix](file_path)
        
        # Try to detect by MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            if mime_type.startswith('text/'):
                return TextLoader(file_path)
        
        raise ValueError(f"Unsupported file type: {suffix}")
    
    def get_link_loader(self, url: str) -> BaseLoader:
        """Get appropriate loader for web links"""
        return LinkParser(url)