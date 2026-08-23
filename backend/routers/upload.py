"""
upload.py — File upload endpoint.

POST /api/upload/{session_id}
  - Accepts CSV, Excel (.xlsx/.xls), JSON, or PDF files.
  - Parses the file into a pandas DataFrame (data) or chunks (PDF).
  - For PDFs: auto-generates summary/category/tags via Gemini,
    stores in catalog DB, and embeds in permanent ChromaDB collection.
"""

import json
import os
import shutil
import tempfile
import uuid

import pandas as pd
from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from auth import get_current_user
from fastapi import Depends
from models.schemas import UploadResponse
from models.database import SessionLocal, DocumentCatalog
from pipelines.csv_loader import load_csv, load_excel
from pipelines.json_loader import load_json
from pipelines.sql_loader import add_df_to_sqlite, filename_to_table
from pipelines.pdf_loader import load_pdf
from utils.vector_store import ingest_chunks, ingest_chunks_permanent, clear_vectorstore
from utils.prompt_templates import DOCUMENT_SUMMARIZE_PROMPT

load_dotenv()

_summarize_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

router = APIRouter()

# Maximum upload size in megabytes (override via MAX_UPLOAD_MB in .env)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

# Shared in-memory store: session_id -> DataFrame
# Imported by chat.py to look up the active DataFrame for a session.
_dataframes: dict[str, pd.DataFrame] = {}

# Shared in-memory store: session_id -> LangChain SQLDatabase
_databases: dict[str, object] = {}


# Directory where cataloged data files are snapshotted (as CSV) so they can
# be reloaded into future sessions.
_CATALOG_FILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "catalog_files")
)


def _file_type_from_name(filename: str) -> str:
    suffix = os.path.splitext(filename)[1].lower()
    return {".csv": "csv", ".xlsx": "excel", ".xls": "excel", ".json": "json"}.get(suffix, "data")


def catalog_data_document(df: pd.DataFrame, filename: str, user_id: str) -> dict:
    """
    Add a tabular file to the permanent catalog: auto-summarize its schema and
    sample rows with Gemini, store metadata + a CSV snapshot on disk so the
    data can be reloaded into any future session.

    Returns: {doc_id, category, tags, summary, rows, columns, column_types}
    """
    profile_lines = [
        f"Tabular data file: {filename}",
        f"Shape: {df.shape[0]} rows x {df.shape[1]} columns",
        f"Columns and types: { {str(c): str(t) for c, t in df.dtypes.items()} }",
        "",
        "Sample rows:",
        df.head(5).to_markdown(index=False),
    ]
    summary_text = ""
    category = "Uncategorized"
    tags: list = []
    try:
        prompt = DOCUMENT_SUMMARIZE_PROMPT.format(document_text="\n".join(profile_lines)[:3000])
        resp = _summarize_llm.invoke([HumanMessage(content=prompt)])
        parsed = json.loads(resp.content)
        summary_text = parsed.get("summary", "")
        category = parsed.get("category", "Uncategorized")
        tags = parsed.get("tags", [])
    except Exception:
        summary_text = f"Data file: {filename} ({df.shape[0]} rows, {df.shape[1]} columns)"

    db = SessionLocal()
    try:
        doc_row = DocumentCatalog(
            user_id=user_id,
            filename=filename,
            file_type=_file_type_from_name(filename),
            category=category,
            tags=tags,
            summary=summary_text,
            # Data files are not embedded — unique placeholder satisfies the constraint
            vector_collection=f"data_{uuid.uuid4().hex}",
        )
        db.add(doc_row)
        db.commit()
        db.refresh(doc_row)

        os.makedirs(_CATALOG_FILES_DIR, exist_ok=True)
        snapshot_path = os.path.join(_CATALOG_FILES_DIR, f"doc_{doc_row.id}.csv")
        df.to_csv(snapshot_path, index=False)
        doc_row.file_path = snapshot_path
        db.commit()
        doc_id = doc_row.id
    finally:
        db.close()

    return {
        "doc_id": doc_id,
        "category": category,
        "tags": tags,
        "summary": summary_text,
        "rows": len(df),
        "columns": list(df.columns),
        "column_types": {str(c): _friendly_dtype(t) for c, t in df.dtypes.items()},
    }


def catalog_pdf_document(chunks: list[str], filename: str, user_id: str) -> dict:
    """
    Add a parsed PDF to the permanent catalog: auto-summarize with Gemini,
    create the DocumentCatalog row, and embed into a permanent ChromaDB
    collection. Shared by session uploads and direct catalog uploads.

    Returns: {doc_id, num_chunks, category, tags, summary}
    """
    snippet = "\n".join(chunks)[:3000]
    summary_text = ""
    category = "Uncategorized"
    tags: list = []
    try:
        prompt = DOCUMENT_SUMMARIZE_PROMPT.format(document_text=snippet)
        resp = _summarize_llm.invoke([HumanMessage(content=prompt)])
        parsed = json.loads(resp.content)
        summary_text = parsed.get("summary", "")
        category = parsed.get("category", "Uncategorized")
        tags = parsed.get("tags", [])
    except Exception:
        summary_text = f"Document: {filename}"

    db = SessionLocal()
    try:
        doc_row = DocumentCatalog(
            user_id=user_id,
            filename=filename,
            file_type="pdf",
            category=category,
            tags=tags,
            summary=summary_text,
            vector_collection="",  # placeholder, updated below
        )
        db.add(doc_row)
        db.commit()
        db.refresh(doc_row)

        num_chunks, collection_name = ingest_chunks_permanent(
            doc_row.id, chunks, filename
        )
        doc_row.vector_collection = collection_name
        db.commit()
        doc_id = doc_row.id
    finally:
        db.close()

    return {
        "doc_id": doc_id,
        "num_chunks": num_chunks,
        "category": category,
        "tags": tags,
        "summary": summary_text,
    }


def _friendly_dtype(dtype) -> str:
    """Map a pandas dtype to a user-facing label for the frontend."""
    kind = getattr(dtype, "kind", "O")
    return {
        "i": "number", "u": "number", "f": "number",
        "b": "boolean",
        "M": "datetime", "m": "duration",
    }.get(kind, "text")


@router.post("/upload/{session_id}", response_model=UploadResponse)
def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a data file for a session.

    Supported formats: .csv, .xlsx, .xls, .json, .pdf

    Note: this is a plain `def` so FastAPI runs it in a worker thread —
    the LLM/embedding calls below are blocking and must stay off the event loop.
    """
    filename = file.filename or "unknown"
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in (".csv", ".xlsx", ".xls", ".json", ".pdf"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Use .csv, .xlsx, .xls, .json, or .pdf.",
        )

    # Enforce the upload size cap before doing any work
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

    # Write upload to a temp file so loaders can use file-path APIs
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            chunks = load_pdf(tmp_path)

            # Also ingest into session-scoped collection for immediate chat
            ingest_chunks(session_id, chunks, filename)

            # Add to the permanent catalog (summary, category, tags, embeddings)
            meta = catalog_pdf_document(chunks, filename, user["id"])

            os.unlink(tmp_path)
            return UploadResponse(
                filename=filename,
                chunks=meta["num_chunks"],
                size_mb=round(size / (1024 * 1024), 2),
                file_type="document",
                doc_id=meta["doc_id"],
                category=meta["category"],
                tags=meta["tags"],
                summary=meta["summary"],
                message=f"Successfully ingested {meta['num_chunks']} chunks from '{filename}' "
                        f"into catalog (category: {meta['category']}).",
            )

        if suffix == ".csv":
            df = load_csv(tmp_path)
        elif suffix in (".xlsx", ".xls"):
            df = load_excel(tmp_path)
        else:  # .json
            df = load_json(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Latest data file is the active DataFrame (DataFrame mode + charts);
    # every data file also becomes its own SQL table so queries can join files.
    table_name = filename_to_table(filename)
    _dataframes[session_id] = df
    _databases[session_id] = add_df_to_sqlite(_databases.get(session_id), df, table_name)

    return UploadResponse(
        filename=filename,
        rows=len(df),
        columns=list(df.columns),
        column_types={str(c): _friendly_dtype(t) for c, t in df.dtypes.items()},
        size_mb=round(size / (1024 * 1024), 2),
        file_type="data",
        table_name=table_name,
        message=f"Successfully loaded {len(df):,} rows and {len(df.columns)} columns "
                f"into table '{table_name}'.",
    )


@router.delete("/upload/{session_id}")
def clear_session(session_id: str):
    """Remove the loaded DataFrame and conversation memory for a session."""
    from utils.memory_manager import clear_memory
    _dataframes.pop(session_id, None)
    _databases.pop(session_id, None)
    clear_vectorstore(session_id)
    clear_memory(session_id)
    return {"message": f"Session '{session_id}' cleared."}
