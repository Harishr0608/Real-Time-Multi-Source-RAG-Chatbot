import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None
import logging as logger


class LinkParser:
    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Check if URL is YouTube"""
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in youtube_domains)
    
    @staticmethod
    def extract_youtube_id(url: str) -> Optional[str]:
        """Extract YouTube video ID - SAME AS YOUR WORKING CODE"""
        try:
            # Handle different YouTube URL formats
            if "watch?v=" in url:
                video_id = url.split("=")[1]
                # Handle URLs with additional parameters
                if "&" in video_id:
                    video_id = video_id.split("&")[0]
                return video_id
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1]
                if "?" in video_id:
                    video_id = video_id.split("?")[0]
                return video_id
            else:
                # Fallback to regex patterns
                patterns = [
                    r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
                    r'youtu\.be\/([0-9A-Za-z_-]{11})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, url)
                    if match:
                        return match.group(1)
        except Exception as e:
            logger.error(f"Error extracting video ID from {url}: {e}")
        return None
    
    @staticmethod
    def get_youtube_metadata(video_id: str) -> Dict[str, str]:
        """Extract YouTube video metadata from webpage"""
        try:
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(youtube_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('meta', property='og:title')
            title = title_tag.get('content', '') if title_tag else ''
            
            # Extract description
            desc_tag = soup.find('meta', property='og:description')
            description = desc_tag.get('content', '') if desc_tag else ''
            
            return {
                'title': title,
                'description': description
            }
        except Exception as e:
            logger.warning(f"Failed to extract YouTube metadata: {e}")
            return {}
    
    @staticmethod
    def load_youtube_content(url: str) -> Dict[str, Any]:
        """Load YouTube transcript - USING EXACT SAME METHOD AS YOUR WORKING CODE"""
        try:
            # Check if YouTube Transcript API is available
            if YouTubeTranscriptApi is None:
                logger.error("youtube_transcript_api not installed")
                video_id = LinkParser.extract_youtube_id(url) or 'unknown'
                return LinkParser._create_metadata_fallback(url, video_id)
            
            video_id = LinkParser.extract_youtube_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            # Method 1: Use the EXACT same approach as your working Streamlit code
            try:
                # This is identical to your working extract_transcript_details function
                transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
                
                transcript = ""
                for i in transcript_text:
                    transcript += " " + i["text"]
                
                return {
                    'content': transcript.strip(),
                    'metadata': {
                        'source': url,
                        'type': 'youtube',
                        'video_id': video_id,
                        'content_type': 'transcript'
                    }
                }
                
            except Exception as e:
                logger.warning(f"Transcript extraction failed: {e}")
                
                # Method 2: Try with language specification as fallback
                try:
                    transcript_text = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                    
                    transcript = ""
                    for i in transcript_text:
                        transcript += " " + i["text"]
                    
                    return {
                        'content': transcript.strip(),
                        'metadata': {
                            'source': url,
                            'type': 'youtube',
                            'video_id': video_id,
                            'content_type': 'transcript'
                        }
                    }
                    
                except Exception as e2:
                    logger.warning(f"Transcript with language failed: {e2}")
                    # Fallback to metadata
                    return LinkParser._create_metadata_fallback(url, video_id)
            
        except Exception as e:
            logger.error(f"Error loading YouTube content {url}: {e}")
            video_id = LinkParser.extract_youtube_id(url) or 'unknown'
            return LinkParser._create_metadata_fallback(url, video_id)
    
    @staticmethod
    def _create_metadata_fallback(url: str, video_id: str) -> Dict[str, Any]:
        """Create fallback content using metadata"""
        logger.info(f"Using metadata fallback for YouTube video: {video_id}")
        metadata = LinkParser.get_youtube_metadata(video_id)
        
        content_parts = []
        if metadata.get('title'):
            content_parts.append(f"YouTube Video: {metadata['title']}")
        if metadata.get('description'):
            desc = metadata['description'][:300] + "..." if len(metadata['description']) > 300 else metadata['description']
            content_parts.append(f"Description: {desc}")
        
        content_parts.append(f"Video URL: {url}")
        content_parts.append(f"Video ID: {video_id}")
        
        content = " | ".join(content_parts) if content_parts else f"YouTube video: {url}"
        
        return {
            'content': content,
            'metadata': {
                'source': url,
                'type': 'youtube',
                'video_id': video_id,
                'content_type': 'metadata_fallback',
                'title': metadata.get('title', ''),
                'description': metadata.get('description', '')
            }
        }
    
    @staticmethod
    def load_web_content(url: str) -> Dict[str, Any]:
        """Load web page content"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return {
                'content': text,
                'metadata': {
                    'source': url,
                    'type': 'web',
                    'title': soup.title.string if soup.title else url
                }
            }
        except Exception as e:
            logger.error(f"Error loading web content {url}: {e}")
            raise