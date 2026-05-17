"""
main.py — FastAPI application entry point for EnterpriseQ AI.

Start the server:
  uvicorn backend.main:app --reload --port 8000

Interactive API docs:
  http://localhost:8000/docs   (Swagger UI)
  http://localhost:8000/redoc  (ReDoc)
"""
import uvicorn
from dotenv import load_dotenv
load_dotenv()   # Load .env before anything else imports os.getenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, upload
from routers import catalog as catalog_router
from routers import multi_doc as multi_doc_router
from models.database import init_db

app = FastAPI(
    title="EnterpriseQ AI",
    description="Your company's unified data assistant — ask questions in plain English.",
    version="1.0.0",
)

# CORS — allow the Streamlit frontend (runs on port 8501) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(catalog_router.router, prefix="/api", tags=["Catalog"])
app.include_router(multi_doc_router.router, prefix="/api", tags=["Multi-Doc"])


@app.on_event("startup")
def on_startup():
    """Initialise the catalog database on server start."""
    init_db()


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe — returns 200 when the server is up."""
    return {"status": "ok", "app": "EnterpriseQ AI", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",   # module path: change to "main:app" if run from the same directory
        host="0.0.0.0",
        port=8000,
        reload=True,          # remove or set to False in production
    )