"""
vector_store.py — ChromaDB vector store manager for RAG document retrieval.

Each session gets its own Chroma collection so documents are isolated.
Uses Google Generative AI embeddings (free tier) to match the LLM provider.
"""

import os
from dotenv import load_dotenv

import chromadb
from chromadb.config import Settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

# Persistent ChromaDB client — stores vectors on disk so they survive restarts.
_CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_data")
_chroma_client = chromadb.PersistentClient(path=os.path.abspath(_CHROMA_DIR))

# Google embedding model (free tier, same API key as Gemini)
_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

# In-memory cache: session_id -> Chroma vectorstore wrapper
_vectorstores: dict[str, Chroma] = {}


def ingest_chunks(session_id: str, chunks: list[str], filename: str) -> int:
    """
    Embed text chunks and store them in a session-scoped Chroma collection.

    Args:
        session_id: Unique session identifier (used as collection name).
        chunks:     List of text chunks from the PDF splitter.
        filename:   Original filename — stored as metadata for source tracking.

    Returns:
        Number of chunks ingested.
    """
    collection_name = f"session_{session_id}"

    # Add filename metadata to each chunk for source attribution
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

    vectorstore = Chroma.from_texts(
        texts=chunks,
        embedding=_embeddings,
        collection_name=collection_name,
        client=_chroma_client,
        metadatas=metadatas,
    )

    _vectorstores[session_id] = vectorstore
    return len(chunks)


def get_retriever(session_id: str):
    """
    Return a LangChain retriever for the session's vector store.
    Returns None if no documents have been ingested for this session.
    """
    if session_id in _vectorstores:
        return _vectorstores[session_id].as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )

    # Try to load from persisted collection
    collection_name = f"session_{session_id}"
    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            client=_chroma_client,
            embedding_function=_embeddings,
        )
        # Check if collection actually has documents
        if vectorstore._collection.count() > 0:
            _vectorstores[session_id] = vectorstore
            return vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4},
            )
    except Exception:
        pass

    return None


def clear_vectorstore(session_id: str) -> None:
    """Delete the vector store collection for a session."""
    _vectorstores.pop(session_id, None)
    collection_name = f"session_{session_id}"
    try:
        _chroma_client.delete_collection(collection_name)
    except Exception:
        pass


# ── Permanent (catalog) document functions ────────────────────────────────

def ingest_chunks_permanent(doc_id: int, chunks: list[str], filename: str) -> tuple[int, str]:
    """
    Embed text chunks into a permanent ChromaDB collection for the catalog.

    Returns:
        (num_chunks, collection_name)
    """
    collection_name = f"doc_{doc_id}"
    metadatas = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]

    vectorstore = Chroma.from_texts(
        texts=chunks,
        embedding=_embeddings,
        collection_name=collection_name,
        client=_chroma_client,
        metadatas=metadatas,
    )

    _vectorstores[collection_name] = vectorstore
    return len(chunks), collection_name


def get_retriever_by_collection(collection_name: str):
    """
    Return a LangChain retriever for a named ChromaDB collection.
    Returns None if the collection doesn't exist or is empty.
    """
    if collection_name in _vectorstores:
        return _vectorstores[collection_name].as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )

    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            client=_chroma_client,
            embedding_function=_embeddings,
        )
        if vectorstore._collection.count() > 0:
            _vectorstores[collection_name] = vectorstore
            return vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4},
            )
    except Exception:
        pass

    return None


def delete_collection(collection_name: str) -> None:
    """Delete a named ChromaDB collection."""
    _vectorstores.pop(collection_name, None)
    try:
        _chroma_client.delete_collection(collection_name)
    except Exception:
        pass
