import re
import logging

logger = logging.getLogger(__name__)

class TextCleaner:
    def __init__(self):
        # Common patterns to clean
        self.patterns = [
            # Multiple whitespaces
            (r'\s+', ' '),
            # Multiple newlines
            (r'\n\s*\n', '\n\n'),
            # Remove page numbers (standalone numbers)
            (r'^\d+$', ''),  # Fixed: Added second argument and corrected pattern
            # Remove common headers/footers
            (r'(Page \d+ of \d+|©.*?\d{4})', ''),
            # Remove excessive punctuation
            (r'[.]{3,}', '...'),
            # Remove HTML entities
            (r'&[a-zA-Z]+;', ' '),
        ]
    
    def clean(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        try:
            # Apply cleaning patterns
            cleaned_text = text
            for pattern, replacement in self.patterns:
                cleaned_text = re.sub(pattern, replacement, cleaned_text, flags=re.MULTILINE)
            
            # Strip leading/trailing whitespace
            cleaned_text = cleaned_text.strip()
            
            # Remove empty lines
            lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            logger.info(f"Text cleaned: {len(text)} -> {len(cleaned_text)} characters")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Text cleaning failed: {str(e)}")
            return text  # Return original text on failure