import logging
import os
import openai
import chromadb
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any
import asyncio
import json
from pathlib import Path

load_dotenv()
logger = logging.getLogger(__name__)

class RAGService:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Disable ChromaDB telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "false"
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found")
        
        # Configure timeout settings
        timeout = httpx.Timeout(
            connect=30.0,
            read=120.0,
            write=30.0,
            pool=30.0
        )
        
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=3
        )
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=os.getenv("CHROMADB_DIR", "./data/vectorstore")
        )
        
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o")
        self.embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-large")
        
        # Initialize collection only once
        self._initialize_collection()
        self._initialized = True
    
    def _initialize_collection(self):
        """Initialize collection with proper dimension handling"""
        try:
            # Check if collection exists and test dimensions
            try:
                self.collection = self.chroma_client.get_collection("documents")
                logger.info("Found existing ChromaDB collection")
                
                # Test if we can use it with current embedding dimensions
                count = self.collection.count()
                if count > 0:
                    # Try a test query to check dimensions
                    try:
                        test_embedding = [0.0] * self._get_embedding_dimensions()
                        self.collection.query(
                            query_embeddings=[test_embedding],
                            n_results=1
                        )
                        logger.info(f"Collection is compatible with {self.embed_model} model")
                        return
                    except chromadb.errors.InvalidArgumentError as e:
                        if "embedding with dimension" in str(e):
                            logger.warning(f"Dimension mismatch: {e}")
                            logger.info("Recreating collection with correct dimensions...")
                            self.chroma_client.delete_collection("documents")
                        else:
                            raise
                else:
                    logger.info("Collection exists but is empty, keeping it")
                    return
                    
            except ValueError:
                # Collection doesn't exist
                logger.info("Collection doesn't exist, creating new one")
            
            # Create new collection
            self.collection = self.chroma_client.create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new ChromaDB collection for {self.embed_model} model")
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def _get_embedding_dimensions(self) -> int:
        """Get expected embedding dimensions for current model"""
        model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
        return model_dimensions.get(self.embed_model, 1536)
    
    async def retrieve_relevant_chunks(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks for a question"""
        try:
            logger.info(f"Retrieving chunks for question: {question[:100]}...")
            
            # Ensure collection exists
            if not hasattr(self, 'collection') or self.collection is None:
                logger.warning("Collection not initialized, reinitializing...")
                self._initialize_collection()
            
            # Check if collection has any documents
            try:
                count = self.collection.count()
            except chromadb.errors.NotFoundError:
                logger.warning("Collection was deleted, recreating...")
                self._initialize_collection()
                count = self.collection.count()
            
            if count == 0:
                logger.warning("Collection is empty, no documents to retrieve")
                return []
            
            # Generate query embedding
            response = await self.client.embeddings.create(
                model=self.embed_model,
                input=question
            )
            query_embedding = response.data[0].embedding
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count),
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results with enhanced metadata extraction
            chunks = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    metadata = results["metadatas"][0][i] if results["metadatas"][0] else {}
                    text = results["documents"][0][i]
                    
                    # Enhanced filename extraction for both files and YouTube videos
                    filename = metadata.get("filename", "Unknown")
                    source_type = metadata.get("source_type", "unknown")
                    
                    # Special handling for YouTube videos
                    if (filename == "Unknown" or filename == "") and "YOUTUBE VIDEO METADATA" in text:
                        # Extract title from YouTube video content
                        title_lines = [line for line in text.split('\n') if line.startswith('Title:')]
                        if title_lines:
                            filename = title_lines[0].replace('Title:', '').strip()
                            source_type = "link"
                            logger.info(f"Extracted YouTube title from content: '{filename}'")
                    
                    # Additional fallback for links
                    elif source_type == "link" and (filename == "Unknown" or filename == ""):
                        # Try to extract from URL metadata
                        url = metadata.get("url", "")
                        if url:
                            filename = url
                            logger.info(f"Using URL as filename for link: '{filename}'")
                    
                    logger.debug(f"Retrieved chunk {i}: filename='{filename}', source_type='{source_type}', source_id='{metadata.get('source_id', '')}'")
                    
                    chunks.append({
                        "id": results["ids"][0][i],
                        "text": text,
                        "metadata": metadata,
                        "distance": results["distances"][0][i],
                        "filename": filename,
                        "source_id": metadata.get("source_id", ""),
                        "chunk_index": metadata.get("chunk_index", i),
                        "score": 1 - results["distances"][0][i],
                        "source_type": source_type
                    })
            
            logger.info(f"Retrieved {len(chunks)} chunks with filenames: {[c['filename'] for c in chunks]}")
            return chunks
            
        except Exception as e:
            logger.error(f"Retrieval failed: {str(e)}", exc_info=True)
            return []
    
    def _extract_youtube_title_from_text(self, text: str) -> str:
        """Extract YouTube video title from text content"""
        try:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Title:'):
                    title = line.replace('Title:', '').strip()
                    if title:
                        logger.info(f"Extracted YouTube title: '{title}'")
                        return title
                # Alternative patterns
                elif line.startswith('VIDEO TITLE:'):
                    title = line.replace('VIDEO TITLE:', '').strip()
                    if title:
                        return title
                elif 'title:' in line.lower() and len(line) < 200:  # Reasonable title length
                    parts = line.lower().split('title:')
                    if len(parts) > 1:
                        title = parts[1].strip()
                        if title:
                            return title
            
            # If no title found, try to extract from first meaningful line
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line and not line.startswith('http') and len(line) > 10 and len(line) < 100:
                    return line
                    
        except Exception as e:
            logger.error(f"Error extracting YouTube title: {e}")
        
        return "Unknown"
    
    async def generate_answer(self, question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer using Chain-of-Thought reasoning with proper source attribution"""
        try:
            logger.info(f"Generating answer for question: {question[:100]}...")
            
            if not chunks:
                return {
                    "answer": "I don't have enough information to answer your question. Please make sure documents are properly uploaded and processed.",
                    "reasoning": "No relevant documents found in the knowledge base.",
                    "sources": []
                }
            
            # Log retrieved chunks for debugging
            logger.info(f"Processing {len(chunks)} chunks:")
            for i, chunk in enumerate(chunks):
                logger.info(f"  Chunk {i}: filename='{chunk.get('filename', 'Unknown')}', source_id='{chunk.get('source_id', '')}', score={chunk.get('score', 0):.3f}")
            
            # Get additional metadata for better source attribution
            source_details = await self._get_source_details(chunks)
            
            # Aggregate chunks by source for better citation - ENHANCED VERSION
            source_groups = {}
            for chunk in chunks:
                source_id = chunk.get('source_id', 'unknown')
                if source_id not in source_groups:
                    # Get enhanced source information
                    source_info = source_details.get(source_id, {})
                    
                    # Enhanced filename extraction with YouTube support
                    filename = "Unknown"
                    
                    # 1. Try from loaded metadata first
                    if source_info.get('filename') and source_info.get('filename') not in ['Unknown', '']:
                        filename = source_info['filename']
                        logger.info(f"Got filename from metadata: '{filename}'")
                    
                    # 2. Try from chunk filename
                    elif chunk.get('filename') and chunk.get('filename') not in ['Unknown', '']:
                        filename = chunk['filename']
                        logger.info(f"Got filename from chunk: '{filename}'")
                    
                    # 3. Special handling for YouTube videos
                    elif source_info.get('type') == 'link' or chunk.get('source_type') == 'link':
                        # Try to extract title from chunk text
                        if chunk.get('text'):
                            extracted_title = self._extract_youtube_title_from_text(chunk['text'])
                            if extracted_title != "Unknown":
                                filename = extracted_title
                                logger.info(f"Extracted YouTube title: '{filename}'")
                            elif source_info.get('url'):
                                filename = source_info['url']
                                logger.info(f"Using URL as filename: '{filename}'")
                    
                    # 4. Final fallback
                    if filename == "Unknown" or not filename:
                        if source_info.get('url'):
                            filename = source_info['url']
                        else:
                            filename = "Unknown Document"
                    
                    source_groups[source_id] = {
                        'chunks': [],
                        'max_score': 0,
                        'filename': filename,
                        'metadata': chunk.get('metadata', {}),
                        'source_info': source_info,
                        'source_type': chunk.get('source_type', source_info.get('type', 'unknown'))
                    }
                    
                    logger.info(f"Created source group for {source_id}: filename='{filename}', type='{source_groups[source_id]['source_type']}'")
                
                source_groups[source_id]['chunks'].append(chunk)
                source_groups[source_id]['max_score'] = max(
                    source_groups[source_id]['max_score'], 
                    chunk.get('score', 0)
                )
            
            # Prepare context from chunks with enhanced source info
            context_parts = []
            source_citations = {}
            citation_counter = 1
            
            for source_id, group in source_groups.items():
                source_info = group['source_info']
                source_type = group['source_type']
                filename = group['filename']
                
                # Determine source type and create proper citation
                chunks_text = group['chunks']
                combined_text = '\n'.join([chunk.get('text', '') for chunk in chunks_text])
                
                if source_type == 'link' or 'YOUTUBE VIDEO METADATA' in combined_text:
                    source_type = "YouTube Video"
                    
                    # Final attempt to extract YouTube title if still unknown
                    if filename == "Unknown" or filename == source_info.get('url', ''):
                        extracted_title = self._extract_youtube_title_from_text(combined_text)
                        if extracted_title != "Unknown":
                            filename = extracted_title
                    
                    source_citation = f"[{citation_counter}] YouTube Video: {filename}"
                    source_url = source_info.get('url', '')
                else:
                    source_type = "Document"
                    source_citation = f"[{citation_counter}] Document: {filename}"
                    source_url = source_info.get('path', 'Local File')
                
                source_citations[source_id] = {
                    'number': citation_counter,
                    'type': source_type,
                    'name': filename,
                    'citation': source_citation,
                    'score': group['max_score'],
                    'url_or_path': source_url
                }
                
                context_parts.append(f"{source_citation}:\n{combined_text}")
                citation_counter += 1
                
                logger.info(f"Created citation [{citation_counter-1}] for {source_type}: '{filename}' (score: {group['max_score']:.3f})")
            
            context = "\n\n".join(context_parts)
            
            # Enhanced Chain-of-Thought prompt with citation instructions
            system_prompt = """You are a helpful AI assistant that answers questions based on provided context.

Rules:
1. Answer based ONLY on the provided context
2. ALWAYS cite sources using the [number] format provided (e.g., "According to [1]..." or "As mentioned in [2]...")
3. Be concise but comprehensive
4. Use explicit Chain-of-Thought reasoning
5. If information comes from multiple sources, cite all relevant sources

You MUST provide your reasoning in this exact format:
1. Step 1: [Describe what you're analyzing]
2. Step 2: [Describe your analysis process]  
3. Step 3: [Describe your conclusion]

Then provide your final answer with proper citations."""

            user_prompt = f"""Context:
{context}

Question: {question}

Please provide your step-by-step reasoning followed by your final answer:

Step 1: Identify the key information from the context relevant to the question
Step 2: Analyze how this information relates to the question  
Step 3: Draw conclusions and provide the answer

Reasoning:"""
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1200
            )
            
            full_response = response.choices[0].message.content
            logger.info(f"LLM Response length: {len(full_response)} characters")
            
            # Better reasoning extraction
            reasoning_text = ""
            answer_text = full_response
            
            # Look for step-by-step reasoning
            if "Step 1:" in full_response and "Step 2:" in full_response:
                # Extract reasoning section
                reasoning_start = full_response.find("Step 1:")
                
                # Look for final answer markers
                answer_markers = [
                    "Final answer:",
                    "Answer:",
                    "In conclusion:",
                    "Therefore:",
                    "Based on this analysis:",
                    "The answer is:"
                ]
                
                answer_start = -1
                for marker in answer_markers:
                    marker_pos = full_response.find(marker)
                    if marker_pos > reasoning_start:
                        answer_start = marker_pos
                        break
                
                if answer_start > reasoning_start:
                    reasoning_text = full_response[reasoning_start:answer_start].strip()
                    answer_text = full_response[answer_start:].strip()
                    # Remove the marker from answer
                    for marker in answer_markers:
                        if answer_text.startswith(marker):
                            answer_text = answer_text[len(marker):].strip()
                            break
                else:
                    reasoning_text = full_response[reasoning_start:].strip()
                    answer_text = reasoning_text  # Use reasoning as answer if no clear separation
            
            # If no clear reasoning found, use fallback
            if not reasoning_text:
                reasoning_text = "Applied systematic analysis to the provided context to extract relevant information and draw conclusions."
            
            logger.info(f"Extracted reasoning length: {len(reasoning_text)} characters")
            logger.info(f"Extracted answer length: {len(answer_text)} characters")
            
            # Prepare properly formatted sources with all required fields
            sources = []
            for source_id, citation_info in source_citations.items():
                group = source_groups[source_id]
                chunks_text = ' '.join([chunk.get('text', '') for chunk in group['chunks']])
                source_info = group['source_info']
                
                # Use the citation_info name which should now be correct
                actual_filename = citation_info['name']
                
                if citation_info['type'] == "YouTube Video":
                    # Extract YouTube metadata for display
                    uploader = "Unknown"
                    for line in chunks_text.split('\n'):
                        if line.startswith('Uploader:') or line.startswith('Channel:'):
                            uploader = line.split(':', 1)[1].strip()
                            break
                    
                    # If we have a meaningful title, show it with uploader
                    if actual_filename and actual_filename not in ["Unknown", source_info.get('url', '')]:
                        source_display_name = f"{actual_filename} (by {uploader})"
                    else:
                        source_display_name = f"YouTube Video (by {uploader})"
                    source_url = citation_info['url_or_path']
                else:
                    source_display_name = actual_filename
                    source_url = citation_info['url_or_path']
                
                sources.append({
                    "citation_number": citation_info['number'],
                    "source_id": source_id,
                    "name": source_display_name,
                    "filename": actual_filename,
                    "type": citation_info['type'],
                    "url_or_path": source_url,
                    "relevance_score": citation_info['score'],
                    "chunk_count": len(group['chunks']),
                    "text": chunks_text[:200] + "..." if len(chunks_text) > 200 else chunks_text,
                    "chunk_id": group['chunks'][0].get('id', ''),
                    "preview": chunks_text[:400] + "..." if len(chunks_text) > 400 else chunks_text
                })
            
            # Sort sources by citation number
            sources.sort(key=lambda x: x['citation_number'])
            
            logger.info(f"Generated answer with {len(sources)} properly attributed sources:")
            for source in sources:
                logger.info(f"  [{source['citation_number']}] {source['filename']} (source_id: {source['source_id']}, relevance: {source['relevance_score']:.3f})")
            
            return {
                "answer": answer_text,
                "reasoning": reasoning_text,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Answer generation failed: {str(e)}", exc_info=True)
            return {
                "answer": "I encountered an error while generating the answer. Please try again.",
                "reasoning": f"Error occurred during answer generation: {str(e)}",
                "sources": []
            }
    
    async def _get_source_details(self, chunks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Get additional source details from metadata files"""
        source_details = {}
        
        try:
            unique_source_ids = set(chunk.get('source_id') for chunk in chunks if chunk.get('source_id'))
            logger.info(f"Loading metadata for source IDs: {list(unique_source_ids)}")
            
            for source_id in unique_source_ids:
                if source_id and source_id != 'unknown':
                    try:
                        # Try to load metadata from file
                        metadata_path = Path(f"data/metadata/{source_id}.json")
                        if metadata_path.exists():
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                                source_details[source_id] = metadata
                                logger.info(f"Loaded metadata for {source_id}: filename='{metadata.get('filename', 'Unknown')}', type='{metadata.get('type', 'unknown')}', url='{metadata.get('url', 'N/A')}'")
                        else:
                            logger.warning(f"Metadata file not found: {metadata_path}")
                            source_details[source_id] = {"filename": "Unknown", "type": "unknown"}
                    except Exception as e:
                        logger.error(f"Could not load metadata for source {source_id}: {e}")
                        source_details[source_id] = {"filename": "Unknown", "type": "unknown"}
                        
        except Exception as e:
            logger.error(f"Error getting source details: {e}")
        
        return source_details
    
    async def add_embeddings(self, documents: List[str], metadatas: List[Dict], 
                           ids: List[str], embeddings: List[List[float]]):
        """Add embeddings to the vector database with enhanced metadata"""
        try:
            # Ensure collection exists
            if not hasattr(self, 'collection') or self.collection is None:
                logger.warning("Collection not initialized, reinitializing...")
                self._initialize_collection()
            
            # Verify embedding dimensions
            if embeddings:
                expected_dim = self._get_embedding_dimensions()
                actual_dim = len(embeddings[0])
                logger.info(f"Adding embeddings: expected dimension {expected_dim}, got {actual_dim}")
                
                if actual_dim != expected_dim:
                    logger.error(f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}")
                    raise ValueError(f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}")
            
            # Enhanced metadata logging
            for i, metadata in enumerate(metadatas):
                logger.info(f"Adding embedding {i} with metadata: filename='{metadata.get('filename', 'Unknown')}', source_id='{metadata.get('source_id', '')}', source_type='{metadata.get('source_type', 'unknown')}'")
            
            # Add embeddings
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            logger.info(f"Successfully added {len(documents)} embeddings to vector database")
            
        except chromadb.errors.InvalidArgumentError as e:
            if "embedding with dimension" in str(e):
                logger.error(f"ChromaDB dimension error: {e}")
                logger.info("Recreating collection to fix dimension mismatch...")
                
                # Delete and recreate collection
                try:
                    self.chroma_client.delete_collection("documents")
                except:
                    pass
                
                self.collection = self.chroma_client.create_collection(
                    name="documents",
                    metadata={"hnsw:space": "cosine"}
                )
                
                # Retry adding embeddings
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings
                )
                logger.info(f"Successfully added {len(documents)} embeddings after recreation")
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise
    
    async def delete_embeddings(self, source_id: str) -> Dict[str, Any]:
        """Delete all embeddings for a source"""
        try:
            # Ensure collection exists
            if not hasattr(self, 'collection') or self.collection is None:
                logger.warning("Collection not initialized, no embeddings to delete")
                return {"deleted_count": 0}
            
            results = self.collection.get(where={"source_id": source_id})
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                deleted_count = len(results['ids'])
                logger.info(f"Deleted {deleted_count} embeddings for source {source_id}")
                return {"deleted_count": deleted_count}
            
            return {"deleted_count": 0}
        except Exception as e:
            logger.error(f"Failed to delete embeddings for {source_id}: {e}")
            return {"deleted_count": 0}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics for debugging"""
        try:
            if not hasattr(self, 'collection') or self.collection is None:
                return {"status": "not_initialized"}
            
            count = self.collection.count()
            return {
                "status": "active",
                "document_count": count,
                "embedding_model": self.embed_model,
                "expected_dimensions": self._get_embedding_dimensions()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}