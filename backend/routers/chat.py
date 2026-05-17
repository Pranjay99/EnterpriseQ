"""
chat.py — Natural language query endpoint.

POST /api/chat
  Body: { session_id, question, mode, doc_id }
  - For data queries: looks up DataFrame, calls data_agent or sql_agent.
  - For RAG queries: uses session vectorstore or catalog doc_id.
  - Returns { answer, chart_json, sql_query, sources }
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from agents.data_agent import query_data
from agents.sql_agent import query_sql
from agents.rag_agent import query_rag, query_rag_by_collection
from agents.multi_doc_agent import query_multi_doc
from agents.general_agent import query_general
from agents.orchestrator_agent import should_use_general_agent
from routers.upload import _dataframes, _databases
from utils.vector_store import get_retriever
from models.schemas import ChatRequest, ChatResponse
from models.database import SessionLocal, DocumentCatalog

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Ask a natural-language question about the data loaded for a session,
    or about a cataloged document (via doc_id).
    """
    # ── If doc_ids is provided, use multi-document query ─────────────
    if req.doc_ids and len(req.doc_ids) > 0:
        db = SessionLocal()
        try:
            docs = db.query(DocumentCatalog).filter(
                DocumentCatalog.id.in_(req.doc_ids)
            ).all()
            if not docs:
                raise HTTPException(status_code=404, detail="No catalog documents found for given IDs.")

            doc_infos = [
                {"id": d.id, "filename": d.filename, "vector_collection": d.vector_collection}
                for d in docs
            ]

            result = query_multi_doc(
                question=req.question,
                doc_infos=doc_infos,
                mode=req.multi_doc_mode,
            )

            # Update catalog stats
            now = datetime.now(timezone.utc)
            for d in docs:
                d.query_count += 1
                d.last_accessed = now
            db.commit()
        finally:
            db.close()

        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources"),
        )

    # ── If doc_id is provided, use the catalog document ───────────────
    if req.doc_id is not None:
        db = SessionLocal()
        try:
            doc = db.query(DocumentCatalog).filter(DocumentCatalog.id == req.doc_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="Catalog document not found.")

            result = query_rag_by_collection(doc.vector_collection, req.question)

            # Update catalog stats
            doc.query_count += 1
            doc.last_accessed = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources"),
        )

    # ── General-purpose agent (explicit mode or no data context) ────────
    if req.mode == "general":
        result = query_general(req.question)
        return ChatResponse(answer=result["answer"])

    # ── Session-based queries (existing flow) ─────────────────────────
    df = _dataframes.get(req.session_id)
    has_documents = get_retriever(req.session_id) is not None

    if df is None and not has_documents:
        # Auto-route MATH / REASON questions even without uploaded data
        if req.mode == "auto" and should_use_general_agent(req.question):
            result = query_general(req.question)
            return ChatResponse(answer=result["answer"])

        raise HTTPException(
            status_code=400,
            detail=f"No data loaded for session '{req.session_id}'. "
                   "Please upload a file first via POST /api/upload/{session_id}.",
        )

    # Determine which agent to use
    if req.mode == "rag" or (req.mode == "auto" and has_documents and df is None):
        use_mode = "rag"
    elif req.mode == "sql" or (req.mode == "auto" and req.session_id in _databases):
        use_mode = "sql"
    else:
        use_mode = "dataframe"

    try:
        if use_mode == "rag":
            result = query_rag(req.session_id, req.question)
        elif use_mode == "sql" and req.session_id in _databases:
            db_sql = _databases[req.session_id]
            result = query_sql(req.session_id, req.question, db_sql, df)
        else:
            if df is None:
                raise HTTPException(
                    status_code=400,
                    detail="No tabular data loaded for this mode. Upload a CSV/Excel/JSON file, "
                           "or switch to RAG mode for document queries.",
                )
            result = query_data(req.session_id, req.question, df)
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Error processing request: {err_msg}")

    return ChatResponse(
        answer=result["answer"],
        chart_json=result.get("chart_json"),
        sql_query=result.get("sql_query"),
        sources=result.get("sources"),
    )
