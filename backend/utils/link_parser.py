import logging
import asyncio
import os
import yt_dlp
from pathlib import Path
from typing import Dict, Any
from backend.utils.loader_factory import BaseLoader
import concurrent.futures

logger = logging.getLogger(__name__)

class LinkParser(BaseLoader):
    def __init__(self, url: str):
        self.url = url
        self.is_youtube = "youtube.com" in url or "youtu.be" in url
    
    async def load(self) -> str:
        """Load content from web link"""
        try:
            if self.is_youtube:
                return await self._load_youtube_content()
            else:
                return await self._load_web_content()
        except Exception as e:
            logger.error(f"Failed to load content from {self.url}: {str(e)}")
            raise
    
    async def _load_youtube_content(self) -> str:
        """Enhanced YouTube content extraction with title, description, and transcript"""
        try:
            logger.info(f"Processing YouTube URL: {self.url}")
            
            # Extract video ID
            video_id = await asyncio.to_thread(self._extract_video_id, self.url)
            if not video_id:
                raise ValueError("Could not extract video ID from URL")
            
            # Setup directories (async)
            transcript_dir = Path("data/transcripts")
            await asyncio.to_thread(transcript_dir.mkdir, parents=True, exist_ok=True)
            
            # Run YouTube processing in background thread to avoid blocking
            logger.info("Starting YouTube metadata extraction (non-blocking)...")
            
            # Run the heavy yt-dlp operations in a thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._extract_youtube_data_sync, video_id, transcript_dir)
                
                # Wait for the YouTube processing with timeout
                try:
                    youtube_data = await asyncio.wait_for(
                        asyncio.wrap_future(future), 
                        timeout=60.0  # 60 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.error("YouTube processing timed out after 60 seconds")
                    raise ValueError("YouTube processing timed out")
            
            logger.info(f"YouTube content extraction completed. Total length: {len(youtube_data)} characters")
            return youtube_data
            
        except Exception as e:
            logger.error(f"YouTube content extraction failed: {str(e)}")
            raise
    
    def _extract_youtube_data_sync(self, video_id: str, transcript_dir: Path) -> str:
        """Synchronous YouTube data extraction (runs in thread pool)"""
        try:
            # Configure yt-dlp options for metadata and transcript
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'en-US', 'en-GB'],
                'subtitlesformat': 'vtt',
                'outtmpl': str(transcript_dir / '%(id)s.%(ext)s'),
                'skip_download': True,
                'quiet': True,  # Reduce output noise
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # Extract video information and download subtitles
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info
                info = ydl.extract_info(self.url, download=False)
                
                # Download subtitles
                ydl.download([self.url])
                
                # Extract metadata
                title = info.get('title', 'Unknown Title')
                description = info.get('description', '')
                uploader = info.get('uploader', 'Unknown')
                duration = info.get('duration', 0)
                view_count = info.get('view_count', 0)
                upload_date = info.get('upload_date', '')
                tags = info.get('tags', [])
                
                logger.info(f"YouTube metadata extracted - Title: {title[:50]}...")
            
            # Read transcript content
            transcript_content = ""
            transcript_files = list(transcript_dir.glob(f"{video_id}.*.vtt"))
            
            if transcript_files:
                # Use the first available transcript file
                transcript_file = transcript_files[0]
                logger.info(f"Reading transcript from: {transcript_file}")
                
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    vtt_content = f.read()
                    transcript_content = self._parse_vtt_content(vtt_content)
            else:
                logger.warning(f"No transcript found for video {video_id}")
                transcript_content = "No transcript available"
            
            # Combine all content
            combined_content = self._format_youtube_content(
                title=title,
                description=description,
                uploader=uploader,
                duration=duration,
                view_count=view_count,
                upload_date=upload_date,
                tags=tags,
                transcript=transcript_content
            )
            
            return combined_content
            
        except Exception as e:
            logger.error(f"Sync YouTube processing failed: {str(e)}")
            raise
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _parse_vtt_content(self, vtt_content: str) -> str:
        """Parse VTT subtitle content to extract text"""
        lines = vtt_content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip VTT headers, timestamps, and empty lines
            if (line and 
                not line.startswith('WEBVTT') and 
                not line.startswith('Kind:') and 
                not line.startswith('Language:') and 
                not '-->' in line and 
                not line.isdigit()):
                text_lines.append(line)
        
        return ' '.join(text_lines)
    
    def _format_youtube_content(self, title: str, description: str, uploader: str, 
                               duration: int, view_count: int, upload_date: str, 
                               tags: list, transcript: str) -> str:
        """Format YouTube content with metadata"""
        
        # Format duration
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
        
        # Format view count
        view_str = f"{view_count:,}" if view_count else "Unknown"
        
        # Format tags
        tags_str = ", ".join(tags[:10]) if tags else "No tags"  # Limit to first 10 tags
        
        # Format upload date
        if upload_date and len(upload_date) == 8:
            upload_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        else:
            upload_str = upload_date or "Unknown"
        
        formatted_content = f"""YOUTUBE VIDEO METADATA:

Title: {title}

Uploader: {uploader}
Duration: {duration_str}
Views: {view_str}
Upload Date: {upload_str}
Tags: {tags_str}

Description:
{description[:1000]}{'...' if len(description) > 1000 else ''}

TRANSCRIPT:
{transcript}
"""
        
        return formatted_content
    
    async def _load_web_content(self) -> str:
        """Load content from regular web pages"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Run BeautifulSoup parsing in thread pool (CPU intensive)
                        soup = await asyncio.to_thread(BeautifulSoup, html, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text content
                        text = soup.get_text()
                        
                        # Clean up text (also in thread pool)
                        cleaned_text = await asyncio.to_thread(self._clean_text, text)
                        
                        return cleaned_text
                    else:
                        raise ValueError(f"Failed to fetch content: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Web content extraction failed: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean up text content"""
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return ' '.join(chunk for chunk in chunks if chunk)