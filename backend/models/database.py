"""
database.py — SQLAlchemy ORM models and engine for the Document Catalog.

Uses a local SQLite file (catalog.db) stored alongside the backend.
This is separate from the in-memory SQLite used for Text-to-SQL queries.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, DateTime, JSON,
)
from sqlalchemy.orm import declarative_base, sessionmaker

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "catalog.db")
_DB_URL = f"sqlite:///{os.path.abspath(_DB_PATH)}"

engine = create_engine(_DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class DocumentCatalog(Base):
    __tablename__ = "document_catalog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, default="dev-user", index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)          # "pdf"
    category = Column(String(100), default="Uncategorized")
    tags = Column(JSON, default=list)                        # ["finance", "quarterly"]
    summary = Column(Text, default="")
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    query_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    vector_collection = Column(String(100), nullable=False, unique=True)
    # For tabular files (csv/excel/json): path to the stored CSV snapshot,
    # so the data can be reloaded into any future session. NULL for PDFs.
    file_path = Column(String(500), nullable=True)


def init_db():
    """Create all tables if they don't exist, and apply lightweight migrations."""
    Base.metadata.create_all(bind=engine)

    # Migration: add user_id to rows created before authentication existed.
    from sqlalchemy import text
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(document_catalog)"))]
        if "user_id" not in cols:
            conn.execute(text(
                "ALTER TABLE document_catalog "
                "ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT 'dev-user'"
            ))
            conn.commit()
        if "file_path" not in cols:
            conn.execute(text(
                "ALTER TABLE document_catalog ADD COLUMN file_path VARCHAR(500)"
            ))
            conn.commit()


def get_db():
    """Yield a SQLAlchemy session, auto-closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
