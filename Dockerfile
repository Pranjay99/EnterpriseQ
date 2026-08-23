# Enterprise Q backend — Cloud Run image
# Build:  docker build -t enterprise-q-backend .
# Run:    docker run -p 8080:8080 --env-file .env enterprise-q-backend

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/hf_cache \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

WORKDIR /app

# CPU-only torch first (the default wheel bundles CUDA and adds ~5 GB)
COPY requirements.txt .
RUN pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

# Bake the embedding model into the image so cold starts don't download it
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY backend/ ./backend/

WORKDIR /app/backend

# Cloud Run injects $PORT (default 8080). Model load takes ~20-40s on boot,
# so deploy with --cpu-boost and a generous startup window.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
