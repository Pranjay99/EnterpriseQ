"""
catalog.py — Document Catalog API endpoints.

GET  /api/catalog/list    — list all documents
GET  /api/catalog/search  — search by name, category, or tag
POST /api/catalog/pin     — pin/unpin a document
GET  /api/catalog/stats   — usage analytics
DELETE /api/catalog/{doc_id} — delete a document from catalog and ChromaDB
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.database import get_db, DocumentCatalog
from models.schemas import (
    CatalogItem, CatalogListResponse, PinRequest, CatalogStatsResponse,
)
from utils.vector_store import delete_collection

router = APIRouter()


@router.get("/catalog/list", response_model=CatalogListResponse)
def catalog_list(
    pinned_only: bool = False,
    category: str = None,
    sort_by: str = "upload_date",
    db: Session = Depends(get_db),
):
    """List all cataloged documents with optional filters."""
    q = db.query(DocumentCatalog)

    if pinned_only:
        q = q.filter(DocumentCatalog.is_pinned == True)
    if category:
        q = q.filter(DocumentCatalog.category == category)

    if sort_by == "query_count":
        q = q.order_by(DocumentCatalog.query_count.desc())
    elif sort_by == "last_accessed":
        q = q.order_by(DocumentCatalog.last_accessed.desc())
    else:
        q = q.order_by(DocumentCatalog.upload_date.desc())

    docs = q.all()
    return CatalogListResponse(
        documents=[CatalogItem.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/catalog/search", response_model=CatalogListResponse)
def catalog_search(
    q: str = Query(default="", description="Search by filename"),
    category: str = Query(default=None),
    tag: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """Search documents by name, summary, category, or tag."""
    query = db.query(DocumentCatalog)

    if q:
        query = query.filter(
            DocumentCatalog.filename.ilike(f"%{q}%")
            | DocumentCatalog.summary.ilike(f"%{q}%")
        )
    if category:
        query = query.filter(DocumentCatalog.category == category)

    docs = query.order_by(DocumentCatalog.upload_date.desc()).all()

    # Filter by tag in Python (SQLite JSON support is limited)
    if tag:
        tag_lower = tag.lower()
        docs = [d for d in docs if tag_lower in [t.lower() for t in (d.tags or [])]]

    # Also match search query against tags if q is provided but no tag filter
    if q and not tag:
        q_lower = q.lower()
        # Include docs already matched by name/summary, plus any matching by tag
        tag_matches = [
            d for d in query.order_by(DocumentCatalog.upload_date.desc()).all()
            if any(q_lower in t.lower() for t in (d.tags or []))
        ]
        # Merge without duplicates
        seen_ids = {d.id for d in docs}
        for d in tag_matches:
            if d.id not in seen_ids:
                docs.append(d)
                seen_ids.add(d.id)

    return CatalogListResponse(
        documents=[CatalogItem.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.post("/catalog/pin")
def catalog_pin(req: PinRequest, db: Session = Depends(get_db)):
    """Pin or unpin a document."""
    doc = db.query(DocumentCatalog).filter(DocumentCatalog.id == req.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.is_pinned = req.pinned
    db.commit()
    return {"message": f"Document '{doc.filename}' {'pinned' if req.pinned else 'unpinned'}."}


@router.get("/catalog/stats", response_model=CatalogStatsResponse)
def catalog_stats(db: Session = Depends(get_db)):
    """Return usage analytics for the document catalog."""
    docs = db.query(DocumentCatalog).all()
    total = len(docs)
    total_queries = sum(d.query_count for d in docs)
    pinned_count = sum(1 for d in docs if d.is_pinned)

    # Category breakdown
    category_breakdown = {}
    for d in docs:
        cat = d.category or "Uncategorized"
        category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

    # Most queried
    most_queried = None
    if docs:
        top = max(docs, key=lambda d: d.query_count)
        if top.query_count > 0:
            most_queried = CatalogItem.model_validate(top)

    return CatalogStatsResponse(
        total_documents=total,
        total_queries=total_queries,
        most_queried=most_queried,
        category_breakdown=category_breakdown,
        pinned_count=pinned_count,
    )


@router.delete("/catalog/{doc_id}")
def catalog_delete(doc_id: int, db: Session = Depends(get_db)):
    """Delete a document from the catalog and its ChromaDB collection."""
    doc = db.query(DocumentCatalog).filter(DocumentCatalog.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    delete_collection(doc.vector_collection)
    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' deleted."}
