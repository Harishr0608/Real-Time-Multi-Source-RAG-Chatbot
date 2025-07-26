import streamlit as st
import requests
import json
import time
from typing import Dict, Any
import os
from datetime import datetime
from pathlib import Path


# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def main():
    st.set_page_config(
        page_title="RAG Chatbot",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 RAG Chatbot")
    st.subheader("Upload documents and ask questions")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "sources" not in st.session_state:
        st.session_state.sources = []
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Check backend health with improved tolerance
    if not check_backend_health():
        st.error("⚠️ Backend service is not responding. Please check if the server is running.")
        st.info("If you just submitted a YouTube video, please wait a moment as it may still be processing...")
    
    # Sidebar for file management
    with st.sidebar:
        # Clear Chat Button - Always visible at the top
        st.header("💬 Chat Controls")
        
        if st.button("🗑️ Clear Chat", type="secondary", help="Clear all chat messages", use_container_width=True):
            clear_chat()
            st.rerun()
        
        st.divider()
        
        st.header("📁 Document Management")
        
        # File upload
        st.subheader("Upload File")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'docx', 'xlsx', 'csv', 'txt', 'md'],
            help="Supported formats: PDF, DOCX, XLSX, CSV, TXT, MD"
        )
        
        if uploaded_file and st.button("Upload File"):
            if uploaded_file.size > 50 * 1024 * 1024:  # 50MB limit
                st.error("File size must be less than 50MB")
            else:
                with st.spinner("Uploading and processing file..."):
                    success = upload_file(uploaded_file)
                    if success:
                        st.success("File uploaded successfully! Processing in background...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Upload failed")
        
        # Link input
        st.subheader("Add Web Link")
        link_url = st.text_input(
            "Enter URL",
            placeholder="https://example.com or YouTube URL",
            help="Web pages and YouTube videos supported"
        )
        
        if link_url and st.button("Add Link"):
            if not (link_url.startswith("http://") or link_url.startswith("https://")):
                st.error("Please enter a valid URL starting with http:// or https://")
            else:
                with st.spinner("Processing link..."):
                    success = upload_link(link_url)
                    if success:
                        st.success("Link submitted successfully! Processing in background...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Link processing failed")
        
        # Source management
        st.subheader("📋 Uploaded Sources")
        
        # Auto-refresh controls
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 Refresh", help="Refresh source status"):
                st.session_state.last_refresh = time.time()
                st.rerun()
        
        with col2:
            auto_refresh = st.checkbox("Auto-refresh", value=True, help="Automatically refresh every 3 seconds")
        
        sources = get_sources()
        
        if sources:
            # Count sources by status
            processing_count = len([s for s in sources if s.get('status') == 'processing'])
            completed_count = len([s for s in sources if s.get('status') == 'completed'])
            failed_count = len([s for s in sources if s.get('status') == 'failed'])
            
            # Status summary
            st.info(f"📊 **Status:** {completed_count} completed, {processing_count} processing, {failed_count} failed")
            
            # Display sources
            for source in sources:
                status = source.get('status', 'unknown')
                source_type = source.get('type', 'unknown')
                
                # FIXED: Better display name logic for different source types
                display_name = get_display_name(source)
                
                # Status emoji
                status_emoji = {
                    'completed': '✅',
                    'processing': '🔄',
                    'failed': '❌',
                    'text_extracted': '📝',
                    'chunked': '📋',
                    'ingested': '📥'
                }.get(status, '❓')
                
                # Type emoji
                type_emoji = get_type_emoji(source)
                
                with st.expander(f"{status_emoji} {type_emoji} {display_name}", expanded=(status == 'failed')):
                    st.write(f"**Status:** {status}")
                    st.write(f"**Type:** {source_type}")
                    st.write(f"**ID:** {source.get('id', 'unknown')[:8]}...")
                    
                    # FIXED: Show URL for YouTube videos and web links
                    if source_type in ['youtube', 'YouTube Video', 'web', 'link']:
                        url = get_source_url(source)
                        if url:
                            st.write(f"**URL:** {url}")
                            if source_type in ['youtube', 'YouTube Video']:
                                st.markdown(f"🔗 [**Watch Video**]({url})")
                            else:
                                st.markdown(f"🔗 [**Open Link**]({url})")
                    
                    # Show upload time
                    if 'upload_time' in source:
                        try:
                            upload_time = datetime.fromisoformat(source['upload_time'].replace('Z', '+00:00'))
                            st.write(f"**Uploaded:** {upload_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        except:
                            st.write(f"**Uploaded:** {source['upload_time']}")
                    
                    # Show file size for files
                    if source.get('type') == 'file' and 'file_size' in source:
                        file_size_mb = source['file_size'] / (1024 * 1024)
                        st.write(f"**Size:** {file_size_mb:.2f} MB")
                    
                    # Show processing details for completed sources
                    if status == 'completed':
                        if 'chunk_count' in source:
                            st.write(f"**Chunks:** {source['chunk_count']}")
                        if 'embedded_count' in source:
                            st.write(f"**Embeddings:** {source['embedded_count']}")
                        if 'text_length' in source:
                            st.write(f"**Text Length:** {source['text_length']:,} characters")
                        
                        # Show completion time
                        if 'completed_time' in source:
                            try:
                                completed_time = datetime.fromisoformat(source['completed_time'].replace('Z', '+00:00'))
                                st.write(f"**Completed:** {completed_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            except:
                                st.write(f"**Completed:** {source['completed_time']}")
                        
                        # Add download button for files only
                        if source.get('type') == 'file' and 'path' in source:
                            create_download_button(source)
                    
                    # Show error details for failed sources
                    if status == 'failed' and 'error' in source:
                        st.error(f"**Error:** {source['error']}")
                        if 'failed_time' in source:
                            try:
                                failed_time = datetime.fromisoformat(source['failed_time'].replace('Z', '+00:00'))
                                st.write(f"**Failed at:** {failed_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            except:
                                st.write(f"**Failed at:** {source['failed_time']}")
                    
                    # Show progress for processing sources
                    if status == 'processing':
                        st.info("Processing in background...")
                        progress_bar = st.progress(0.5)
                        
                    # Delete button
                    if st.button(f"🗑️ Delete", key=f"delete_{source['id']}", type="secondary"):
                        with st.spinner("Deleting..."):
                            if delete_source(source['id']):
                                st.success("Deleted successfully!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Deletion failed")
        else:
            st.info("No sources uploaded yet")
            st.markdown("👆 Upload a file or add a link to get started!")
        
        # Auto-refresh logic
        if auto_refresh and sources:
            processing_sources = [s for s in sources if s.get('status') == 'processing']
            if processing_sources and (time.time() - st.session_state.last_refresh) > 3:
                st.session_state.last_refresh = time.time()
                st.rerun()
    
    # Check if there are any completed sources
    completed_sources = [s for s in get_sources() if s.get('status') == 'completed']
    
    if not completed_sources:
        st.info("📋 Upload and process some documents first to start chatting!")
    else:
        st.success(f"✅ Ready to chat! {len(completed_sources)} document(s) available.")
    
    # Display chat messages using both session states for compatibility
    messages_to_display = st.session_state.chat_history if st.session_state.chat_history else st.session_state.messages
    
    for message in messages_to_display:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Enhanced source display with citations
            if message["role"] == "assistant" and "sources" in message and message["sources"]:
                sources = message["sources"]
                
                # Group sources by source_id to avoid duplicates
                unique_sources = {}
                for source in sources:
                    source_id = source.get('source_id', f"source_{len(unique_sources)}")
                    if source_id not in unique_sources:
                        unique_sources[source_id] = source
                    else:
                        # Keep the source with higher relevance score
                        if source.get('relevance_score', 0) > unique_sources[source_id].get('relevance_score', 0):
                            unique_sources[source_id] = source
                
                retrieved_count = len(unique_sources)
                
                with st.expander(f"📚 Sources ({retrieved_count} unique documents from {len(sources)} chunks)"):
                    for i, (source_id, source) in enumerate(unique_sources.items(), 1):
                        display_source_info(source, i)
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents", disabled=not completed_sources):
        # Add user message to both session states for compatibility
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        st.session_state.chat_history.append(user_message)
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = query_documents(prompt)
                
                if result and result.get("success"):
                    response_data = result["data"]
                    response_text = response_data["answer"]
                    sources = response_data.get("sources", [])
                    retrieved_count = response_data.get("retrieved_docs_count", 0)
                    reasoning = response_data.get("reasoning", "")
                    
                    st.write(response_text)
                    
                    # Add assistant message to both session states
                    assistant_message = {
                        "role": "assistant", 
                        "content": response_text,
                        "sources": sources,
                        "reasoning": reasoning
                    }
                    st.session_state.messages.append(assistant_message)
                    st.session_state.chat_history.append(assistant_message)
                    
                    # Show sources immediately in the response
                    if sources:
                        # Group sources by source_id to avoid duplicates
                        unique_sources = {}
                        for source in sources:
                            source_id = source.get('source_id', f"source_{len(unique_sources)}")
                            if source_id not in unique_sources:
                                unique_sources[source_id] = source
                            else:
                                # Keep the source with higher relevance score
                                if source.get('relevance_score', 0) > unique_sources[source_id].get('relevance_score', 0):
                                    unique_sources[source_id] = source
                        
                        unique_count = len(unique_sources)
                        
                        with st.expander(f"📚 Sources ({unique_count} unique documents from {len(sources)} chunks)"):
                            for i, (source_id, source) in enumerate(unique_sources.items(), 1):
                                display_source_info(source, f"current_{i}")
                    
                    # Show reasoning if available
                    if reasoning:
                        with st.expander("🧠 Reasoning Process"):
                            st.markdown(reasoning)
                
                else:
                    error_msg = result.get("error", "Sorry, I couldn't process your question. Please try again.")
                    st.error(error_msg)
                    
                    error_message = {"role": "assistant", "content": error_msg}
                    st.session_state.messages.append(error_message)
                    st.session_state.chat_history.append(error_message)


def get_display_name(source: dict) -> str:
    """Get appropriate display name for different source types"""
    source_type = source.get('type', 'unknown')
    
    # For YouTube videos
    if source_type in ['youtube', 'YouTube Video']:
        # Try to get title first, then fallback to URL
        if source.get('title') and source.get('title') not in ['Unknown', '']:
            name = source['title']
        elif source.get('filename') and source.get('filename') not in ['Unknown', '']:
            name = source['filename']
        elif source.get('name') and source.get('name') not in ['Unknown', '']:
            name = source['name']
        else:
            url = get_source_url(source)
            name = url if url else "YouTube Video"
    
    # For files
    elif source_type == 'file':
        if source.get('filename') and source.get('filename') not in ['Unknown', '']:
            name = source['filename']
        elif source.get('name') and source.get('name') not in ['Unknown', '']:
            name = source['name']
        else:
            name = "Unknown File"
    
    # For web links
    elif source_type in ['web', 'link']:
        url = get_source_url(source)
        name = url if url else "Web Link"
    
    else:
        # Generic fallback
        name = source.get('filename') or source.get('name') or source.get('title') or "Unknown"
    
    # Truncate long names
    if len(name) > 40:
        name = name[:37] + "..."
    
    return name


def get_type_emoji(source: dict) -> str:
    """Get emoji for source type"""
    source_type = source.get('type', 'unknown')
    
    if source_type in ['youtube', 'YouTube Video']:
        return "🎥"
    elif source_type == 'file':
        return "📄"
    elif source_type in ['web', 'link']:
        return "🌐"
    else:
        return "📄"


def get_source_url(source: dict) -> str:
    """Extract URL from source with multiple fallbacks"""
    # Try different fields that might contain the URL
    url_fields = ['url', 'link', 'original_url', 'source_url', 'path', 'url_or_path']
    
    for field in url_fields:
        url = source.get(field)
        if url and isinstance(url, str) and url.startswith('http'):
            return url
    
    return ""


def display_source_info(source, unique_key):
    """Display source information in a consistent format"""
    if isinstance(source, dict):
        # Get source details
        source_name = get_display_name(source)
        citation_num = source.get('citation_number', unique_key)
        source_type = source.get('type', 'Document')
        relevance = source.get('relevance_score', 0)
        chunk_count = source.get('chunk_count', 1)
        preview = source.get('preview', '')
        url = get_source_url(source)
        
        # Source type emoji
        type_emoji = get_type_emoji(source)
        
        st.write(f"**{type_emoji} [{citation_num}] {source_name}**")
        st.write(f"*Type:* {source_type}")
        st.write(f"*Relevance Score:* {relevance:.2f}")
        if chunk_count > 1:
            st.write(f"*Chunks Used:* {chunk_count}")
        
        # Add download/link button for sources
        if source_type in ['youtube', 'YouTube Video']:
            if url:
                st.markdown(f"🔗 [**Watch Video**]({url})")
        elif source_type in ['web', 'link']:
            if url:
                st.markdown(f"🔗 [**Open Link**]({url})")
        else:
            # For documents, provide download if available
            source_id = source.get('source_id', source.get('id'))
            file_path = source.get('url_or_path', source.get('path'))
            if source_id and file_path and not file_path.startswith('http'):
                create_source_download_button(source_name, source_id, file_path, unique_key)
        
        if preview:
            with st.expander(f"📝 Preview - Citation [{citation_num}]"):
                st.text(preview)
    
    elif isinstance(source, str):
        # Simple string format (fallback)
        st.write(f"**{unique_key}. {source}**")
    
    else:
        # Unknown format
        st.write(f"**{unique_key}. {str(source)}**")


def clear_chat():
    """Clear all chat messages from session state"""
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.sources = []
    st.success("🗑️ Chat cleared successfully!")


def check_backend_health() -> bool:
    """Check if backend is responding with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return False
    
    return False


def create_download_button(source: dict) -> bool:
    """Create download button for uploaded files"""
    try:
        file_path = source.get('path', '')
        filename = source.get('filename', 'download')
        
        if file_path and Path(file_path).exists():
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            st.download_button(
                label=f"📥 Download {filename}",
                data=file_data,
                file_name=filename,
                mime=get_mime_type(filename),
                key=f"download_{source['id']}"
            )
            return True
    except Exception as e:
        st.error(f"Download error: {str(e)}")
    
    return False


def create_source_download_button(source_name: str, source_id: str, file_path: str, unique_key: str) -> bool:
    """Create download button for source files referenced in chat"""
    try:
        if file_path and Path(file_path).exists():
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            st.download_button(
                label=f"📥 Download Source",
                data=file_data,
                file_name=source_name,
                mime=get_mime_type(source_name),
                key=f"source_download_{source_id}_{unique_key}_{int(time.time())}"
            )
            return True
        elif file_path.startswith('http'):
            st.markdown(f"🔗 [Open Link]({file_path})")
            return True
    except Exception as e:
        st.error(f"Source download error: {str(e)}")
    
    return False


def get_mime_type(filename: str) -> str:
    """Get MIME type based on file extension"""
    extension = Path(filename).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.csv': 'text/csv',
        '.txt': 'text/plain',
        '.md': 'text/markdown'
    }
    return mime_types.get(extension, 'application/octet-stream')


def upload_file(file) -> bool:
    """Upload file to backend"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(f"{API_BASE_URL}/upload_file", files=files, timeout=60)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return False


def upload_link(url: str) -> bool:
    """Upload link to backend"""
    try:
        data = {"url": url}
        response = requests.post(f"{API_BASE_URL}/upload_link", data=data, timeout=60)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Link processing error: {str(e)}")
        return False


def get_sources() -> list:
    """Get list of uploaded sources"""
    try:
        response = requests.get(f"{API_BASE_URL}/list_sources", timeout=10)
        if response.status_code == 200:
            sources = response.json()["sources"]
            # Sort by status (processing first, then completed, then failed)
            status_order = {'processing': 0, 'completed': 1, 'failed': 2}
            sources.sort(key=lambda x: status_order.get(x.get('status', 'unknown'), 3))
            return sources
        return []
    except Exception as e:
        st.error(f"Error fetching sources: {str(e)}")
        return []


def delete_source(source_id: str) -> bool:
    """Delete a source"""
    try:
        response = requests.delete(f"{API_BASE_URL}/delete/{source_id}", timeout=30)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Deletion error: {str(e)}")
        return False


def query_documents(question: str) -> Dict[str, Any]:
    """Query documents and return structured response"""
    try:
        data = {
            "question": question,
            "top_k": 5,
            "include_sources": True
        }
        response = requests.post(f"{API_BASE_URL}/query", json=data, timeout=60)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Query failed: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        st.error(f"Query error: {str(e)}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()
