import streamlit as st
import requests
import json
from typing import Dict, Any
import hashlib

# Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'uploaded_links' not in st.session_state:
    st.session_state.uploaded_links = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def call_api(endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
    """Make API calls to backend"""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        elif method == "DELETE":
            response = requests.delete(url, **kwargs)
        
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}

def upload_file_to_api(file):
    """Upload file to API"""
    files = {"file": (file.name, file.getvalue(), file.type)}
    return call_api("upload_file", method="POST", files=files)

def upload_link_to_api(url: str):
    """Upload link to API"""
    data = {"url": url}
    return call_api("upload_link", method="POST", data=data)

def query_api(query: str):
    """Send query to API"""
    data = {"query": query}
    return call_api("query", method="POST", data=data)

def delete_file_api(file_hash: str):
    """Delete file via API"""
    return call_api(f"delete_file/{file_hash}", method="DELETE")

def delete_link_api(url_hash: str):
    """Delete link via API"""
    return call_api(f"delete_link/{url_hash}", method="DELETE")

# Streamlit UI
st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 Real-Time Multi-Source RAG Chatbot")
st.markdown("Upload documents, add links, and chat with your knowledge base!")

# Sidebar for document management
with st.sidebar:
    st.header("📚 Knowledge Base Management")
    
    # File Upload Section
    st.subheader("📄 Upload Documents")
    uploaded_file = st.file_uploader(
        "Choose files",
        type=['pdf', 'docx', 'xlsx', 'xls'],
        accept_multiple_files=False
    )
    
    if uploaded_file and st.button("Upload File"):
        with st.spinner("Processing file..."):
            result = upload_file_to_api(uploaded_file)
            
            if result["success"]:
                file_hash = result["data"]["file_hash"]
                st.session_state.uploaded_files[uploaded_file.name] = {
                    "hash": file_hash,
                    "chunks": result["data"]["chunks_stored"]
                }
                st.success(f"✅ File uploaded! {result['data']['chunks_stored']} chunks stored.")
            else:
                st.error(f"❌ Error: {result['error']}")
    
    # Link Upload Section
    st.subheader("🔗 Add Links")
    url_input = st.text_input("Enter URL (YouTube, Web pages)")
    
    if url_input and st.button("Add Link"):
        with st.spinner("Processing link..."):
            result = upload_link_to_api(url_input)
            
            if result["success"]:
                url_hash = result["data"]["url_hash"]
                st.session_state.uploaded_links[url_input] = {
                    "hash": url_hash,
                    "chunks": result["data"]["chunks_stored"]
                }
                st.success(f"✅ Link added! {result['data']['chunks_stored']} chunks stored.")
            else:
                st.error(f"❌ Error: {result['error']}")
    
    # Display uploaded files
    if st.session_state.uploaded_files:
        st.subheader("📁 Uploaded Files")
        for filename, info in st.session_state.uploaded_files.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"📄 {filename}")
                st.caption(f"Chunks: {info['chunks']}")
            with col2:
                if st.button("🗑️", key=f"delete_file_{info['hash']}"):
                    result = delete_file_api(info['hash'])
                    if result["success"]:
                        del st.session_state.uploaded_files[filename]
                        st.success("File deleted!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result['error']}")
    
    # Display uploaded links
    if st.session_state.uploaded_links:
        st.subheader("🔗 Added Links")
        for url, info in st.session_state.uploaded_links.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"🔗 {url[:30]}...")
                st.caption(f"Chunks: {info['chunks']}")
            with col2:
                if st.button("🗑️", key=f"delete_link_{info['hash']}"):
                    result = delete_link_api(info['hash'])
                    if result["success"]:
                        del st.session_state.uploaded_links[url]
                        st.success("Link deleted!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result['error']}")

# Main chat interface
col1, col2 = st.columns([3, 1])

with col1:
    st.header("💬 Chat Interface")
    
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
            if "sources" in message:
                with st.expander("📚 Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        st.write(f"{i}. {source}")
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your documents..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        # Get response from API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = query_api(prompt)
                
                if result["success"]:
                    response_data = result["data"]
                    response_text = response_data["answer"]
                    sources = response_data.get("sources", [])
                    retrieved_count = response_data.get("retrieved_docs_count", 0)
                    
                    st.write(response_text)
                    
                    # Add assistant message to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": response_text,
                        "sources": sources
                    })
                    
                    # Show sources
                    if sources:
                        with st.expander(f"📚 Sources ({retrieved_count} documents retrieved)"):
                            for i, source in enumerate(sources, 1):
                                st.write(f"{i}. {source}")
                else:
                    error_msg = f"❌ Error: {result['error']}"
                    st.write(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

with col2:
    st.header("📊 Statistics")
    
    # Knowledge base stats
    total_files = len(st.session_state.uploaded_files)
    total_links = len(st.session_state.uploaded_links)
    total_chunks = (
        sum(info['chunks'] for info in st.session_state.uploaded_files.values()) +
        sum(info['chunks'] for info in st.session_state.uploaded_links.values())
    )
    
    st.metric("📄 Files", total_files)
    st.metric("🔗 Links", total_links)
    st.metric("📊 Total Chunks", total_chunks)
    st.metric("💬 Messages", len(st.session_state.chat_history))
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun() 