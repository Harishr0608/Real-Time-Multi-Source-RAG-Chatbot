from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import asyncio
from typing import Dict, Any, TypedDict, List

from backend.agents.nodes.ingest_node import IngestNode
from backend.agents.nodes.chunk_node import ChunkNode
from backend.agents.nodes.embed_node import EmbedNode
from backend.agents.nodes.delete_node import DeleteNode
from backend.agents.nodes.retrieve_node import RetrieveNode
from backend.agents.nodes.answer_node import AnswerNode

# Define state schemas
class IngestionState(TypedDict):
    source_id: str
    source_type: str
    source_path: str
    metadata: Dict[str, Any]
    content: str
    chunks: list
    embeddings: list

class DeletionState(TypedDict):
    source_id: str
    metadata: Dict[str, Any]
    deleted_chunks: int

class RAGState(TypedDict):
    question: str  # Changed from 'query' to 'question' to match your nodes
    top_k: int
    include_sources: bool
    retrieved_chunks: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    answer: str
    reasoning: str
    error: str

def create_ingestion_graph():
    """Create the ingestion workflow graph"""
    
    # Initialize nodes
    ingest_node = IngestNode()
    chunk_node = ChunkNode()
    embed_node = EmbedNode()
    
    # Create workflow with state schema
    workflow = StateGraph(IngestionState)
    
    # Add nodes
    workflow.add_node("ingest", ingest_node.execute)
    workflow.add_node("chunk", chunk_node.execute)
    workflow.add_node("embed", embed_node.execute)
    
    # Add edges
    workflow.add_edge("ingest", "chunk")
    workflow.add_edge("chunk", "embed")
    workflow.add_edge("embed", END)
    
    # Set entry point
    workflow.set_entry_point("ingest")
    
    return workflow.compile()

def create_deletion_graph():
    """Create the deletion workflow graph"""
    
    delete_node = DeleteNode()
    
    # Create workflow with state schema
    workflow = StateGraph(DeletionState)
    workflow.add_node("delete", delete_node.execute)
    workflow.add_edge("delete", END)
    workflow.set_entry_point("delete")
    
    return workflow.compile()

def create_rag_graph():
    """Create the RAG query workflow graph"""
    
    retrieve_node = RetrieveNode()
    answer_node = AnswerNode()
    
    # Create workflow with state schema
    workflow = StateGraph(RAGState)
    
    workflow.add_node("retrieve", retrieve_node.execute)
    workflow.add_node("answer", answer_node.execute)
    
    workflow.add_edge("retrieve", "answer")
    workflow.add_edge("answer", END)
    
    workflow.set_entry_point("retrieve")
    
    return workflow.compile()