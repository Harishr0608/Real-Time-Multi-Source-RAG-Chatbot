from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.schema import Document
import chromadb
import logging

logger = logging.getLogger(__name__)

class RAGState:
    def __init__(self):
        self.documents: List[Document] = []
        self.query: str = ""
        self.retrieved_docs: List[Document] = []
        self.answer: str = ""
        self.metadata: Dict[str, Any] = {}
        self.error: Optional[str] = None

class FileIngestionAgent:
    def __init__(self, loader_factory, text_cleaner):
        self.loader_factory = loader_factory
        self.text_cleaner = text_cleaner
    
    def process_file(self, state: RAGState) -> RAGState:
        """Process uploaded file"""
        try:
            file_path = state.metadata.get('file_path')
            file_type = self.loader_factory.detect_file_type(file_path)
            
            # Load content based on file type
            if file_type == 'pdf':
                content_data = self.loader_factory.load_pdf(file_path)
            elif file_type == 'docx':
                content_data = self.loader_factory.load_docx(file_path)
            elif file_type == 'excel':
                content_data = self.loader_factory.load_excel(file_path)
            else:
                state.error = f"Unsupported file type: {file_type}"
                return state
            
            # Clean and chunk text
            cleaned_text = self.text_cleaner.clean_text(content_data['content'])
            chunks = self.text_cleaner.chunk_text(cleaned_text)
            
            # Create Document objects
            documents = []
            for chunk in chunks:
                doc = Document(
                    page_content=chunk['text'],
                    metadata={
                        **content_data['metadata'],
                        'chunk_index': chunk['chunk_index'],
                        'file_hash': state.metadata.get('file_hash')
                    }
                )
                documents.append(doc)
            
            state.documents = documents
            logger.info(f"Processed {len(documents)} chunks from {file_path}")
            
        except Exception as e:
            state.error = f"File processing error: {str(e)}"
            logger.error(state.error)
        
        return state

class LinkIngestionAgent:
    def __init__(self, link_parser, text_cleaner):
        self.link_parser = link_parser
        self.text_cleaner = text_cleaner
    
    def process_link(self, state: RAGState) -> RAGState:
        """Process web link or YouTube URL"""
        try:
            url = state.metadata.get('url')
            
            # Determine link type and load content
            if self.link_parser.is_youtube_url(url):
                content_data = self.link_parser.load_youtube_content(url)
            else:
                content_data = self.link_parser.load_web_content(url)
            
            # Clean and chunk text
            cleaned_text = self.text_cleaner.clean_text(content_data['content'])
            chunks = self.text_cleaner.chunk_text(cleaned_text)
            
            # Create Document objects
            documents = []
            for chunk in chunks:
                doc = Document(
                    page_content=chunk['text'],
                    metadata={
                        **content_data['metadata'],
                        'chunk_index': chunk['chunk_index'],
                        'url_hash': state.metadata.get('url_hash')
                    }
                )
                documents.append(doc)
            
            state.documents = documents
            logger.info(f"Processed {len(documents)} chunks from {url}")
            
        except Exception as e:
            state.error = f"Link processing error: {str(e)}"
            logger.error(state.error)
        
        return state

class EmbeddingAgent:
    def __init__(self, chroma_client, embeddings_model):
        self.chroma_client = chroma_client
        self.embeddings_model = embeddings_model
    
    def embed_and_store(self, state: RAGState) -> RAGState:
        """Generate embeddings and store in ChromaDB"""
        try:
            if not state.documents:
                state.error = "No documents to embed"
                return state
            
            collection = self.chroma_client.get_or_create_collection(
                name="rag_documents",
                metadata={"description": "RAG document embeddings"}
            )
            
            # Generate embeddings
            texts = [doc.page_content for doc in state.documents]
            embeddings = self.embeddings_model.embed_documents(texts)
            
            # Prepare data for ChromaDB
            ids = [f"{doc.metadata.get('source', 'unknown')}_{doc.metadata.get('chunk_index', 0)}" 
                   for doc in state.documents]
            metadatas = [doc.metadata for doc in state.documents]
            
            # Store in ChromaDB
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            state.metadata['stored_count'] = len(texts)
            logger.info(f"Stored {len(texts)} embeddings in ChromaDB")
            
        except Exception as e:
            state.error = f"Embedding storage error: {str(e)}"
            logger.error(state.error)
        
        return state

class RetrieverAgent:
    def __init__(self, chroma_client, embeddings_model, top_k: int = 5):
        self.chroma_client = chroma_client
        self.embeddings_model = embeddings_model
        self.top_k = top_k
    
    def retrieve_documents(self, state: RAGState) -> RAGState:
        """Retrieve relevant documents"""
        try:
            collection = self.chroma_client.get_collection("rag_documents")
            
            # Generate query embedding
            query_embedding = self.embeddings_model.embed_query(state.query)
            
            # Retrieve similar documents
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=self.top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Convert to Document objects
            retrieved_docs = []
            for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
                retrieved_doc = Document(
                    page_content=doc,
                    metadata={
                        **metadata,
                        'similarity_score': 1 - results['distances'][0][i]  # Convert distance to similarity
                    }
                )
                retrieved_docs.append(retrieved_doc)
            
            state.retrieved_docs = retrieved_docs
            logger.info(f"Retrieved {len(retrieved_docs)} documents for query")
            
        except Exception as e:
            state.error = f"Document retrieval error: {str(e)}"
            logger.error(state.error)
        
        return state

class AnswerSynthesisAgent:
    def __init__(self, llm_model):
        self.llm_model = llm_model
    
    def generate_answer(self, state: RAGState) -> RAGState:
        """Generate answer using retrieved documents"""
        try:
            if not state.retrieved_docs:
                state.answer = "No relevant documents found for your query."
                return state
            
            # Prepare context from retrieved documents
            context = "\n\n".join([
                f"Document {i+1}: {doc.page_content}"
                for i, doc in enumerate(state.retrieved_docs)
            ])
            
            # Create prompt
            prompt = f"""
            Based on the following context documents, please provide a comprehensive answer to the user's question.
            
            Context:
            {context}
            
            Question: {state.query}
            
            Please provide a detailed answer based on the context provided. If the context doesn't contain enough information to answer the question completely, please mention what information is available and what might be missing.
            
            Answer:
            """
            
            # Generate response
            response = self.llm_model.generate([prompt])
            state.answer = response.generations[0][0].text.strip()
            
            logger.info("Generated answer for query")
            
        except Exception as e:
            state.error = f"Answer generation error: {str(e)}"
            state.answer = "I apologize, but I encountered an error while generating the answer."
            logger.error(state.error)
        
        return state

class DeletionAgent:
    def __init__(self, chroma_client):
        self.chroma_client = chroma_client
    
    def delete_documents(self, state: RAGState) -> RAGState:
        """Delete documents from ChromaDB"""
        try:
            collection = self.chroma_client.get_collection("rag_documents")
            
            # Delete by file hash or URL hash
            delete_filter = {}
            if state.metadata.get('file_hash'):
                delete_filter['file_hash'] = state.metadata['file_hash']
            elif state.metadata.get('url_hash'):
                delete_filter['url_hash'] = state.metadata['url_hash']
            
            if delete_filter:
                # Get documents to delete
                results = collection.get(where=delete_filter)
                if results['ids']:
                    collection.delete(ids=results['ids'])
                    state.metadata['deleted_count'] = len(results['ids'])
                    logger.info(f"Deleted {len(results['ids'])} documents")
                else:
                    state.metadata['deleted_count'] = 0
                    logger.info("No documents found to delete")
            
        except Exception as e:
            state.error = f"Document deletion error: {str(e)}"
            logger.error(state.error)
        
        return state