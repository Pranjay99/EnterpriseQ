"""
multi_doc.py — Multi-document query endpoint.

POST /api/multi-doc/query
  Body: { doc_ids: [1, 3, 5], question: "...", mode: "synthesize" }
  - Retrieves chunks from each document's ChromaDB collection
  - Merges and deduplicates
  - Returns unified answer with per-document source attribution
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from agents.multi_doc_agent import query_multi_doc
from models.database import get_db, DocumentCatalog
from models.schemas import MultiDocRequest, MultiDocResponse

router = APIRouter()


@router.post("/multi-doc/query", response_model=MultiDocResponse)
def multi_doc_query(req: MultiDocRequest, db: Session = Depends(get_db)):
    """
    Query multiple catalog documents simultaneously.

    Modes:
      - synthesize: Combine all docs into one unified answer
      - compare: Highlight similarities and differences
      - per_doc: Answer separately for each document
    """
    if not req.doc_ids:
        raise HTTPException(status_code=400, detail="doc_ids must not be empty.")

    if len(req.doc_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 documents per query.")

    if req.mode not in ("synthesize", "compare", "per_doc"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{req.mode}'. Use: synthesize, compare, per_doc.",
        )

    # Look up all requested documents
    docs = db.query(DocumentCatalog).filter(DocumentCatalog.id.in_(req.doc_ids)).all()

    if not docs:
        raise HTTPException(status_code=404, detail="No documents found for the given IDs.")

    missing = set(req.doc_ids) - {d.id for d in docs}
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Documents not found: {sorted(missing)}",
        )

    # Build info list for the agent
    doc_infos = [
        {
            "id": d.id,
            "filename": d.filename,
            "vector_collection": d.vector_collection,
        }
        for d in docs
    ]

    # Run the multi-doc agent
    try:
        result = query_multi_doc(
            question=req.question,
            doc_infos=doc_infos,
            mode=req.mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")

    # Update stats for all queried documents
    now = datetime.now(timezone.utc)
    for d in docs:
        d.query_count += 1
        d.last_accessed = now
    db.commit()

    return MultiDocResponse(
        answer=result["answer"],
        sources=result["sources"],
        mode=result["mode"],
    )
