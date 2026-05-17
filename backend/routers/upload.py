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
import tempfile

import pandas as pd
from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from models.schemas import UploadResponse
from models.database import SessionLocal, DocumentCatalog
from pipelines.csv_loader import load_csv, load_excel
from pipelines.json_loader import load_json
from pipelines.sql_loader import df_to_sqlite
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

# Shared in-memory store: session_id -> DataFrame
# Imported by chat.py to look up the active DataFrame for a session.
_dataframes: dict[str, pd.DataFrame] = {}

# Shared in-memory store: session_id -> LangChain SQLDatabase
_databases: dict[str, object] = {}


@router.post("/upload/{session_id}", response_model=UploadResponse)
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """
    Upload a data file for a session.

    Supported formats: .csv, .xlsx, .xls, .json
    """
    filename = file.filename or "unknown"
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in (".csv", ".xlsx", ".xls", ".json", ".pdf"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Use .csv, .xlsx, .xls, .json, or .pdf.",
        )

    # Write upload to a temp file so loaders can use file-path APIs
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if suffix == ".pdf":
            chunks = load_pdf(tmp_path)

            # Also ingest into session-scoped collection for immediate chat
            ingest_chunks(session_id, chunks, filename)

            # ── Catalog: auto-summarize with Gemini ──────────────────
            full_text = "\n".join(chunks)
            snippet = full_text[:3000]
            summary_text = ""
            category = "Uncategorized"
            tags = []
            try:
                prompt = DOCUMENT_SUMMARIZE_PROMPT.format(document_text=snippet)
                resp = _summarize_llm.invoke([HumanMessage(content=prompt)])
                parsed = json.loads(resp.content)
                summary_text = parsed.get("summary", "")
                category = parsed.get("category", "Uncategorized")
                tags = parsed.get("tags", [])
            except Exception:
                summary_text = f"Document: {filename}"

            # ── Catalog: create DB row first to get the id ───────────
            db = SessionLocal()
            try:
                doc_row = DocumentCatalog(
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

                # ── Catalog: ingest into permanent collection ────────
                num_chunks, collection_name = ingest_chunks_permanent(
                    doc_row.id, chunks, filename
                )
                doc_row.vector_collection = collection_name
                db.commit()

                # Capture values before closing session
                saved_doc_id = doc_row.id
            finally:
                db.close()

            os.unlink(tmp_path)
            return UploadResponse(
                filename=filename,
                chunks=num_chunks,
                file_type="document",
                doc_id=saved_doc_id,
                message=f"Successfully ingested {num_chunks} chunks from '{filename}' "
                        f"into catalog (category: {category}).",
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

    _dataframes[session_id] = df
    _databases[session_id] = df_to_sqlite(df, table_name="uploaded_data")

    return UploadResponse(
        filename=filename,
        rows=len(df),
        columns=list(df.columns),
        file_type="data",
        message=f"Successfully loaded {len(df):,} rows and {len(df.columns)} columns.",
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
