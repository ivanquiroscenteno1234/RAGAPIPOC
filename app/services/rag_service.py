"""RAG (Retrieval-Augmented Generation) service with Bedrock KB and Gemini using LangChain."""
import logging
from typing import List, Tuple, Optional, Dict, Any
from uuid import UUID
import boto3
from botocore.exceptions import ClientError

from langchain_aws import AmazonKnowledgeBasesRetriever
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document as LangChainDocument
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings
from app.models import Message, MessageRole
from app.services.bedrock_client import create_metadata_filter

logger = logging.getLogger(__name__)

# System prompt for Gemini
SYSTEM_PROMPT_CONCISE = """You are a notebook assistant working exclusively with the documents provided in this notebook.

CRITICAL RULES:
1. Answer ONLY using information from the provided context (document chunks)
2. If the answer is not in the context, clearly state: "I don't have enough information in these documents to answer that question."
3. Cite your sources naturally by mentioning the document name when relevant (e.g., "According to the Project Plan...").
4. Do NOT use bracketed citations like [Doc: filename, Chunk: id].
5. Never invent or infer information not explicitly stated in the context
6. Never leak or reference information from other notebooks or users
7. Provide clear, concise, and natural answers.

Be professional and helpful, but maintain strict adherence to the provided context."""

SYSTEM_PROMPT_DETAILED = """You are an expert Senior Software Architect and Technical Lead.
Your role is to assist developers by analyzing code documentation and providing high-quality, detailed, and actionable technical responses.

CRITICAL RULES:
1. **Context-Driven**: Answer ONLY using information from the provided context (document chunks).
2. **Honesty**: If the answer is not in the context, clearly state: "I don't have enough information in these documents to answer that question."
3. **Citation**: Cite your sources naturally by mentioning the document name (e.g., "According to the Project Plan...").
4. **No Hallucination**: Never invent or infer information not explicitly stated in the context.
5. **Privacy**: Never leak or reference information from other notebooks or users.
6. **Detail & Structure**: 
   - Provide comprehensive, detailed answers.
   - Use markdown headers, bullet points, and code blocks to structure your response.
   - When asked for a plan, break it down into clear, actionable steps.
   - Reference specific file names, class names, and method names from the context.
7. **Tone**: Be professional, technical, and authoritative.

Your goal is to provide the most helpful and complete technical answer possible based on the available data."""


def build_notebook_retriever(
    user_id: UUID,
    notebook_id: UUID,
    selected_document_ids: Optional[List[UUID]] = None,
    k: int = 6
) -> AmazonKnowledgeBasesRetriever:
    """Build LangChain retriever for a notebook.
    
    Args:
        user_id: User UUID
        notebook_id: Notebook UUID
        selected_document_ids: Optional list of specific document IDs
        k: Number of chunks to retrieve
        
    Returns:
        AmazonKnowledgeBasesRetriever instance
    """
    # Create metadata filter
    metadata_filter = create_metadata_filter(
        user_id=user_id,
        notebook_id=notebook_id,
        document_ids=selected_document_ids
    )
    
    # Create bedrock-agent-runtime client with explicit credentials
    client = boto3.client(
        'bedrock-agent-runtime',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        region_name=settings.AWS_REGION
    )

    retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=settings.BEDROCK_KB_ID,
        retrieval_config={
            "vectorSearchConfiguration": {
                "numberOfResults": k,
                "filter": metadata_filter
            }
        },
        client=client
    )
    
    return retriever


def format_langchain_docs(docs: List[LangChainDocument]) -> str:
    """Format LangChain documents into context string.
    
    Args:
        docs: List of LangChain Documents
        
    Returns:
        Formatted context string
    """
    if not docs:
        return "No relevant documents found."
    
    context_parts = []
    for i, doc in enumerate(docs, 1):
        metadata = doc.metadata
        # Bedrock KB returns metadata in a specific structure, LangChain might flatten it or keep it
        # We need to inspect how AmazonKnowledgeBasesRetriever returns it.
        # Usually it's in doc.metadata
        
        chunk_id = metadata.get('chunk_id', f'chunk_{i}')
        # Fallback for chunk_id if not directly in metadata (depends on Bedrock response mapping)
        if 'chunk_id' not in metadata and 'sourceMetadata' in metadata:
             chunk_id = metadata['sourceMetadata'].get('chunkId', f'chunk_{i}')
             
        content = doc.page_content
        
        # Extract document info
        doc_id = metadata.get('document_id', 'unknown')
        filename = metadata.get('filename', 'unknown_document')
        # Fallback for filename
        if 'filename' not in metadata and 'x-amz-bedrock-kb-source-uri' in metadata:
            filename = metadata['x-amz-bedrock-kb-source-uri'].split('/')[-1]
        
        context_parts.append(
            f"[Document {i}: {filename}, Chunk: {chunk_id}, Doc ID: {doc_id}]\n{content}"
        )
    
    return "\n\n---\n\n".join(context_parts)


def format_chat_history(messages: List[Message], max_messages: int = 10) -> List[Any]:
    """Format chat history for LangChain.
    
    Args:
        messages: List of Message objects
        max_messages: Maximum number of messages to include
        
    Returns:
        List of BaseMessage objects
    """
    # Get most recent messages
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    formatted = []
    for msg in recent_messages:
        if msg.role == MessageRole.USER:
            formatted.append(HumanMessage(content=msg.content))
        elif msg.role == MessageRole.ASSISTANT:
            formatted.append(AIMessage(content=msg.content))
        elif msg.role == MessageRole.SYSTEM:
            formatted.append(SystemMessage(content=msg.content))
            
    return formatted


def answer_question(
    user_id: UUID,
    notebook_id: UUID,
    question: str,
    history: List[Message],
    selected_document_ids: Optional[List[UUID]] = None,
    mode: str = "ask"
) -> Tuple[str, List[Dict[str, Any]]]:
    """Answer a question using RAG with LangChain.
    
    Args:
        user_id: User UUID
        notebook_id: Notebook UUID
        question: User's question
        history: Chat history
        selected_document_ids: Optional list of document IDs to search
        mode: "ask" (concise) or "plan" (detailed)
        
    Returns:
        Tuple of (answer, retrieved_chunks)
    """
    # Configure mode-specific settings
    if mode == "plan":
        system_prompt = SYSTEM_PROMPT_DETAILED
        retrieval_count = 25
        temperature = 0.3
        logger.info("Using PLAN mode: Detailed prompt, 25 chunks, temp 0.3")
    else:
        system_prompt = SYSTEM_PROMPT_CONCISE
        retrieval_count = 6
        temperature = 0.7
        logger.info("Using ASK mode: Concise prompt, 6 chunks, temp 0.7")

    try:
        # Check if AWS credentials are configured for RAG
        if not settings.AWS_ACCESS_KEY_ID or not settings.BEDROCK_KB_ID:
            logger.warning("AWS credentials not configured. Running in chat-only mode (no document retrieval)")
            
            # Format chat history
            chat_history = format_chat_history(history)
            
            # Add system message and user question
            messages = [SystemMessage(content="You are a helpful AI assistant.")] + chat_history + [HumanMessage(content=question)]
            
            # Call Gemini directly via LangChain
            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                convert_system_message_to_human=True # Gemini sometimes prefers this
            )
            
            response = llm.invoke(messages)
            answer = response.content
            
            logger.info(f"Generated answer in chat-only mode for question: {question[:50]}...")
            return (answer, [])
        
        # 1. Build retriever (REMOVED: Using direct boto3 call instead)
        # retriever = build_notebook_retriever(...)
        
        # 2. Retrieve relevant chunks using direct boto3 call
        # This bypasses potential issues with AmazonKnowledgeBasesRetriever filter handling
        
        # Create metadata filter
        metadata_filter = create_metadata_filter(
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=selected_document_ids
        )
        
        # Create client
        client = boto3.client(
            'bedrock-agent-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN,
            region_name=settings.AWS_REGION
        )
        
        logger.info(f"Querying Bedrock KB with filter: {metadata_filter}")
        
        try:
            response = client.retrieve(
                knowledgeBaseId=settings.BEDROCK_KB_ID,
                retrievalQuery={
                    'text': question
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': retrieval_count,
                        'filter': metadata_filter
                    }
                }
            )
            
            retrieval_results = response.get('retrievalResults', [])
            
            # Map to LangChain Documents
            docs = []
            for result in retrieval_results:
                content = result.get('content', {}).get('text', '')
                metadata = result.get('metadata', {})
                metadata['score'] = result.get('score')
                metadata['location'] = result.get('location')
                
                docs.append(LangChainDocument(
                    page_content=content,
                    metadata=metadata
                ))
                
        except Exception as e:
            logger.error(f"Bedrock retrieval failed: {e}")
            docs = []

        logger.info(f"Retrieved {len(docs)} documents for question: {question}")
        for i, doc in enumerate(docs):
            logger.info(f"Doc {i} content preview: {doc.page_content[:200]}...")
        
        if not docs:
            return (
                "I couldn't find any relevant information in your documents to answer this question.",
                []
            )
        
        # 3. Format context
        context = format_langchain_docs(docs)
        
        # 4. Format chat history
        chat_history = format_chat_history(history)
        
        # 5. Build the prompt
        # We construct the messages list manually to have full control
        system_message = SystemMessage(content=system_prompt)
        
        human_message_content = f"""CONTEXT FROM YOUR DOCUMENTS:
{context}

QUESTION:
{question}

Please answer the question using only the information from the context above. Answer naturally and professionally."""
        
        messages = [system_message] + chat_history + [HumanMessage(content=human_message_content)]
        
        # 6. Call Gemini via LangChain
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True
        )
        
        response = llm.invoke(messages)
        answer = response.content
        
        # Handle case where Gemini returns a list of content blocks
        if isinstance(answer, list):
            text_parts = []
            for part in answer:
                if isinstance(part, dict) and part.get('type') == 'text':
                    text_parts.append(part.get('text', ''))
                elif isinstance(part, str):
                    text_parts.append(part)
            answer = "".join(text_parts)
        
        logger.info(f"Generated answer for question: {question[:50]}...")
        
        # 7. Convert LangChain docs back to dictionary format for the API response
        chunks = []
        for doc in docs:
            # Map LangChain Document back to our chunk dict format
            metadata = doc.metadata
            
            # Try to extract chunk_id
            chunk_id = metadata.get('chunk_id')
            if not chunk_id and 'sourceMetadata' in metadata:
                chunk_id = metadata['sourceMetadata'].get('chunkId', 'unknown')
            if not chunk_id:
                chunk_id = 'unknown'

            chunk = {
                'content': doc.page_content,
                'score': metadata.get('score', 0.0), # AmazonKnowledgeBasesRetriever might put score in metadata
                'metadata': metadata,
                'location': metadata.get('location', {}),
                'chunk_id': chunk_id
            }
            chunks.append(chunk)
        
        return (answer, chunks)
        
    except Exception as e:
        logger.error(f"Error in answer_question: {e}")
        return (
            f"I encountered an error while processing your question: {str(e)}",
            []
        )
