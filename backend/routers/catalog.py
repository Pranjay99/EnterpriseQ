"""
catalog.py — Document Catalog API endpoints.

GET  /api/catalog/list    — list all documents
GET  /api/catalog/search  — search by name, category, or tag
POST /api/catalog/pin     — pin/unpin a document
GET  /api/catalog/stats   — usage analytics
DELETE /api/catalog/{doc_id} — delete a document from catalog and ChromaDB
"""

import os
import shutil
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

import pandas as pd

from auth import get_current_user
from models.database import get_db, DocumentCatalog
from models.schemas import (
    AddTableRequest, CatalogItem, CatalogListResponse, PinRequest,
    CatalogStatsResponse, UploadResponse,
)
from pipelines.csv_loader import load_csv, load_excel
from pipelines.json_loader import load_json
from pipelines.pdf_loader import load_pdf
from pipelines.sql_loader import add_df_to_sqlite, filename_to_table
from routers.upload import (
    MAX_UPLOAD_MB, _databases, _dataframes, _friendly_dtype,
    catalog_data_document, catalog_pdf_document,
)
from utils.vector_store import delete_collection

router = APIRouter()

_ALLOWED_SUFFIXES = (".csv", ".xlsx", ".xls", ".json", ".pdf")


@router.post("/catalog/upload", response_model=UploadResponse)
def catalog_upload(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Add a file directly to the permanent catalog (no chat session involved).
    PDFs are embedded for Q&A; data files (CSV/Excel/JSON) are profiled and
    snapshotted so they can be reloaded into any session. All entries get an
    auto-generated summary, category, and tags.
    """
    filename = file.filename or "unknown"
    suffix = os.path.splitext(filename)[1].lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Use .csv, .xlsx, .xls, .json, or .pdf.",
        )

    size = file.size
    if size is None:
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File is {size / (1024 * 1024):.1f} MB — the maximum allowed "
                   f"upload size is {MAX_UPLOAD_MB} MB.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            chunks = load_pdf(tmp_path)
            meta = catalog_pdf_document(chunks, filename, user["id"])
            return UploadResponse(
                filename=filename,
                chunks=meta["num_chunks"],
                size_mb=round(size / (1024 * 1024), 2),
                file_type="document",
                doc_id=meta["doc_id"],
                category=meta["category"],
                tags=meta["tags"],
                summary=meta["summary"],
                message=f"Added '{filename}' to catalog (category: {meta['category']}).",
            )

        if suffix == ".csv":
            df = load_csv(tmp_path)
        elif suffix in (".xlsx", ".xls"):
            df = load_excel(tmp_path)
        else:
            df = load_json(tmp_path)
        meta = catalog_data_document(df, filename, user["id"])
        return UploadResponse(
            filename=filename,
            rows=meta["rows"],
            columns=meta["columns"],
            column_types=meta["column_types"],
            size_mb=round(size / (1024 * 1024), 2),
            file_type="data",
            doc_id=meta["doc_id"],
            category=meta["category"],
            tags=meta["tags"],
            summary=meta["summary"],
            message=f"Added '{filename}' to catalog (category: {meta['category']}).",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to process file: {exc}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/catalog/add-table", response_model=UploadResponse)
def catalog_add_table(
    req: AddTableRequest,
    user: dict = Depends(get_current_user),
):
    """
    Add a data file already uploaded in the current chat session to the
    permanent catalog (reads the table back from the session's SQLite).
    """
    db_sql = _databases.get(req.session_id)
    if db_sql is None:
        raise HTTPException(status_code=404, detail="No data loaded for this session.")

    try:
        df = pd.read_sql_table(req.table_name, db_sql._engine)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Table '{req.table_name}' not found in this session.",
        )

    meta = catalog_data_document(df, req.filename, user["id"])
    return UploadResponse(
        filename=req.filename,
        rows=meta["rows"],
        columns=meta["columns"],
        column_types=meta["column_types"],
        file_type="data",
        doc_id=meta["doc_id"],
        table_name=req.table_name,
        category=meta["category"],
        tags=meta["tags"],
        summary=meta["summary"],
        message=f"Added '{req.filename}' to catalog (category: {meta['category']}).",
    )


@router.post("/catalog/{doc_id}/load/{session_id}", response_model=UploadResponse)
def catalog_load_into_session(
    doc_id: int,
    session_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Load a cataloged data file back into a chat session so the SQL and
    DataFrame agents can query it.
    """
    doc = db.query(DocumentCatalog).filter(
        DocumentCatalog.id == doc_id,
        DocumentCatalog.user_id == user["id"],
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(
            status_code=400,
            detail="This catalog entry has no stored data file. "
                   "PDFs are queried directly via document chat.",
        )

    df = load_csv(doc.file_path)
    table_name = filename_to_table(doc.filename)
    _dataframes[session_id] = df
    _databases[session_id] = add_df_to_sqlite(_databases.get(session_id), df, table_name)

    doc.query_count += 1
    doc.last_accessed = datetime.now(timezone.utc)
    db.commit()

    return UploadResponse(
        filename=doc.filename,
        rows=len(df),
        columns=list(df.columns),
        column_types={str(c): _friendly_dtype(t) for c, t in df.dtypes.items()},
        file_type="data",
        doc_id=doc.id,
        table_name=table_name,
        category=doc.category,
        tags=doc.tags,
        summary=doc.summary,
        message=f"Loaded '{doc.filename}' into session as table '{table_name}'.",
    )


@router.get("/catalog/list", response_model=CatalogListResponse)
def catalog_list(
    pinned_only: bool = False,
    category: str = None,
    sort_by: str = "upload_date",
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List the current user's cataloged documents with optional filters."""
    q = db.query(DocumentCatalog).filter(DocumentCatalog.user_id == user["id"])

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
    user: dict = Depends(get_current_user),
):
    """Search the current user's documents by name, summary, category, or tag."""
    query = db.query(DocumentCatalog).filter(DocumentCatalog.user_id == user["id"])

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
def catalog_pin(
    req: PinRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Pin or unpin a document."""
    doc = db.query(DocumentCatalog).filter(
        DocumentCatalog.id == req.doc_id,
        DocumentCatalog.user_id == user["id"],
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.is_pinned = req.pinned
    db.commit()
    return {"message": f"Document '{doc.filename}' {'pinned' if req.pinned else 'unpinned'}."}


@router.get("/catalog/stats", response_model=CatalogStatsResponse)
def catalog_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return usage analytics for the current user's document catalog."""
    docs = db.query(DocumentCatalog).filter(DocumentCatalog.user_id == user["id"]).all()
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
def catalog_delete(
    doc_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a document from the catalog and its ChromaDB collection."""
    doc = db.query(DocumentCatalog).filter(
        DocumentCatalog.id == doc_id,
        DocumentCatalog.user_id == user["id"],
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    delete_collection(doc.vector_collection)
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.unlink(doc.file_path)
        except OSError:
            pass
    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' deleted."}
