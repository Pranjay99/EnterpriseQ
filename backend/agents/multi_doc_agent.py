"""
multi_doc_agent.py — Multi-document RAG agent for EnterpriseQ AI.

Supports three query modes across multiple catalog documents:
  - synthesize: Combine context from all docs into one unified answer
  - compare:    Highlight similarities and differences between documents
  - per_doc:    Answer the question separately for each document
"""

import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document

from utils.vector_store import get_retriever_by_collection
from utils.prompt_templates import (
    MULTI_DOC_SYNTHESIZE_PROMPT,
    MULTI_DOC_COMPARE_PROMPT,
    MULTI_DOC_PER_DOC_PROMPT,
)

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


def _retrieve_from_collection(collection_name: str, question: str, filename: str) -> list[dict]:
    """Retrieve chunks from a single collection, annotated with source."""
    retriever = get_retriever_by_collection(collection_name)
    if retriever is None:
        return []

    docs: list[Document] = retriever.invoke(question)
    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content,
            "source": filename,
            "collection": collection_name,
        })
    return results


def query_multi_doc(
    question: str,
    doc_infos: list[dict],
    mode: str = "synthesize",
) -> dict:
    """
    Query multiple documents simultaneously.

    Args:
        question:   Natural-language question.
        doc_infos:  List of dicts with keys: id, filename, vector_collection
        mode:       "synthesize" | "compare" | "per_doc"

    Returns:
        dict with keys: answer, sources, mode
    """
    # Retrieve chunks from all documents
    all_chunks: dict[str, list[dict]] = {}  # filename -> chunks
    for info in doc_infos:
        chunks = _retrieve_from_collection(
            info["vector_collection"], question, info["filename"]
        )
        if chunks:
            all_chunks[info["filename"]] = chunks

    if not all_chunks:
        return {
            "answer": "Could not find relevant information in the selected documents.",
            "sources": [],
            "mode": mode,
        }

    sources = list(all_chunks.keys())

    # ── Mode: per_doc ─────────────────────────────────────────────────
    if mode == "per_doc":
        per_doc_answers = []
        for filename, chunks in all_chunks.items():
            context = "\n\n".join(
                [f"[Chunk {i+1}]\n{c['content']}" for i, c in enumerate(chunks)]
            )
            prompt = MULTI_DOC_PER_DOC_PROMPT.format(
                filename=filename,
                context=context,
                question=question,
            )
            resp = llm.invoke([HumanMessage(content=prompt)])
            per_doc_answers.append(f"### {filename}\n\n{resp.content}")

        combined_answer = "\n\n---\n\n".join(per_doc_answers)
        return {
            "answer": combined_answer,
            "sources": sources,
            "mode": mode,
        }

    # ── Build merged context for synthesize / compare ─────────────────
    context_parts = []
    for filename, chunks in all_chunks.items():
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[{filename} — Chunk {i+1}]\n{chunk['content']}")

    # Deduplicate chunks with identical content
    seen = set()
    deduped = []
    for part in context_parts:
        content_key = part.split("\n", 1)[1].strip()[:200]
        if content_key not in seen:
            seen.add(content_key)
            deduped.append(part)
    context = "\n\n".join(deduped)

    # ── Mode: compare ─────────────────────────────────────────────────
    if mode == "compare":
        prompt = MULTI_DOC_COMPARE_PROMPT.format(
            documents=", ".join(sources),
            context=context,
            question=question,
        )
    # ── Mode: synthesize (default) ────────────────────────────────────
    else:
        prompt = MULTI_DOC_SYNTHESIZE_PROMPT.format(
            documents=", ".join(sources),
            context=context,
            question=question,
        )

    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "answer": response.content,
        "sources": sources,
        "mode": mode,
    }
