"""
rag_agent.py — Retrieval-Augmented Generation agent for EnterpriseQ AI.

Flow:
  1. User asks a question about an uploaded PDF/document
  2. Retrieve the most relevant chunks from ChromaDB via similarity search
  3. Inject the retrieved context + question into the LLM prompt
  4. LLM generates an answer grounded in the document content
  5. Return { answer, sources }
"""

import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document

from utils.vector_store import get_retriever, get_retriever_by_collection
from utils.prompt_templates import RAG_ANSWER_PROMPT

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


def query_rag(session_id: str, question: str) -> dict:
    """
    Answer a question using RAG over the session's ingested documents.

    Args:
        session_id: User session identifier.
        question:   Natural-language question.

    Returns:
        dict with keys: answer, sources
    """
    retriever = get_retriever(session_id)
    if retriever is None:
        return {
            "answer": "No documents have been uploaded for this session. "
                      "Please upload a PDF file first.",
            "sources": [],
        }

    # Retrieve relevant document chunks
    docs: list[Document] = retriever.invoke(question)

    if not docs:
        return {
            "answer": "I couldn't find relevant information in the uploaded documents "
                      "to answer your question.",
            "sources": [],
        }

    # Build context from retrieved chunks
    context_parts = []
    sources = []
    for i, doc in enumerate(docs):
        context_parts.append(f"[Chunk {i + 1}]\n{doc.page_content}")
        source = doc.metadata.get("source", "unknown")
        if source not in sources:
            sources.append(source)

    context = "\n\n".join(context_parts)

    # Generate answer using the retrieved context
    prompt = RAG_ANSWER_PROMPT.format(
        context=context,
        question=question,
    )
    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "answer": response.content,
        "sources": sources,
    }


def query_rag_by_collection(collection_name: str, question: str) -> dict:
    """
    Answer a question using RAG over a permanent catalog document collection.

    Args:
        collection_name: ChromaDB collection name (e.g. "doc_3").
        question:        Natural-language question.

    Returns:
        dict with keys: answer, sources
    """
    retriever = get_retriever_by_collection(collection_name)
    if retriever is None:
        return {
            "answer": "Could not find the document's vector collection. "
                      "The document may need to be re-uploaded.",
            "sources": [],
        }

    docs: list[Document] = retriever.invoke(question)

    if not docs:
        return {
            "answer": "I couldn't find relevant information in this document "
                      "to answer your question.",
            "sources": [],
        }

    context_parts = []
    sources = []
    for i, doc in enumerate(docs):
        context_parts.append(f"[Chunk {i + 1}]\n{doc.page_content}")
        source = doc.metadata.get("source", "unknown")
        if source not in sources:
            sources.append(source)

    context = "\n\n".join(context_parts)

    prompt = RAG_ANSWER_PROMPT.format(
        context=context,
        question=question,
    )
    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "answer": response.content,
        "sources": sources,
    }
