from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    session_id: str
    question: str
    mode: str = "auto"  # "sql" | "dataframe" | "rag" | "general" | "auto"
    doc_id: Optional[int] = None        # Single catalog document ID
    doc_ids: Optional[List[int]] = None  # Multiple catalog document IDs
    multi_doc_mode: str = "synthesize"   # "synthesize" | "compare" | "per_doc"


class ChatResponse(BaseModel):
    answer: str
    chart_json: Optional[str] = None   # Plotly figure serialised as JSON string
    sql_query: Optional[str] = None    # Generated SQL (when mode=sql)
    sources: Optional[List[str]] = None


class UploadResponse(BaseModel):
    filename: str
    rows: Optional[int] = None
    columns: Optional[List[str]] = None
    column_types: Optional[dict] = None  # {"col_name": "number" | "text" | ...}
    size_mb: Optional[float] = None      # Uploaded file size in MB
    table_name: Optional[str] = None     # SQL table name (data uploads)
    chunks: Optional[int] = None        # Number of text chunks (PDF uploads)
    file_type: str = "data"              # "data" or "document"
    doc_id: Optional[int] = None         # Catalog ID (PDF uploads)
    category: Optional[str] = None       # Auto-generated (PDF uploads)
    tags: Optional[List[str]] = None     # Auto-generated (PDF uploads)
    summary: Optional[str] = None        # Auto-generated (PDF uploads)
    message: str


# ── Catalog schemas ──────────────────────────────────────────────────────

class CatalogItem(BaseModel):
    id: int
    filename: str
    file_type: str
    category: str
    tags: List[str]
    summary: str
    upload_date: datetime
    last_accessed: datetime
    query_count: int
    is_pinned: bool
    vector_collection: str

    class Config:
        from_attributes = True


class CatalogListResponse(BaseModel):
    documents: List[CatalogItem]
    total: int


class PinRequest(BaseModel):
    doc_id: int
    pinned: bool


class AddTableRequest(BaseModel):
    session_id: str
    table_name: str
    filename: str


class CatalogStatsResponse(BaseModel):
    total_documents: int
    total_queries: int
    most_queried: Optional[CatalogItem] = None
    category_breakdown: dict
    pinned_count: int


# ── Multi-document query schemas ─────────────────────────────────────────

class MultiDocRequest(BaseModel):
    doc_ids: List[int]
    question: str
    mode: str = "synthesize"  # "synthesize" | "compare" | "per_doc"


class MultiDocResponse(BaseModel):
    answer: str
    sources: List[str]
    mode: str
