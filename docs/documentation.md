# Enterprise Q — Project Documentation

> Markdown companion to [`documentation.html`](./documentation.html). Keep both in sync when the architecture changes.

An AI-powered enterprise data assistant — ask questions in plain English over spreadsheets, databases, and documents, and get grounded answers with interactive charts.

---

## 1. The Idea — What Enterprise Q Solves

In most organizations, valuable knowledge is scattered across **CSV exports, Excel workbooks, JSON dumps, and PDF reports**. Getting answers out of them requires either technical skills (SQL, pandas, BI tools) or waiting on an analyst. Enterprise Q removes that barrier: it is a **unified natural-language interface over structured and unstructured enterprise data**.

A user uploads a file and asks a question — *"What is the average attrition rate per department?"* or *"Summarize the risks section of this contract"*. A set of specialized LLM agents figures out **how** to answer: generating and safely executing SQL, analyzing a DataFrame, retrieving relevant document passages (RAG), performing math, or synthesizing insight across up to 10 documents at once.

### Problems it addresses

| Problem | How Enterprise Q solves it |
|---|---|
| **Data access bottleneck** | Text-to-SQL and DataFrame agents translate plain English into executable analysis — no SQL/pandas knowledge needed. |
| **Buried document knowledge** | PDFs are chunked, embedded, and stored in ChromaDB; answers are *grounded* in document content with cited sources (RAG). |
| **No document memory** | A permanent **Document Catalog** auto-generates summaries, categories, and tags for every PDF, tracks usage stats, supports pinning. |
| **Cross-document analysis** | The Multi-Doc agent can **synthesize**, **compare**, or answer **per-document** across many files in one query. |
| **Insight, not just answers** | Agents emit chart hints that become interactive Plotly visualizations automatically. |
| **Cost** | Runs entirely on the Google Gemini free tier, with a zero-LLM-cost heuristic router and local tool execution to conserve quota. |

---

## 2. Architecture

Three-tier application with an **agentic middle layer**: Next.js frontend → FastAPI backend that routes every request through the right agent → storage layer (in-memory session store, SQLite, persistent ChromaDB). Answer generation comes from **Google Gemini 2.5 Flash** via LangChain; embeddings are computed locally with sentence-transformers.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND — Next.js 14 · TypeScript · Tailwind · shadcn/ui  (:3000)     │
│   ┌──────────────┐   ┌────────────────┐   ┌───────────────────┐         │
│   │ 💬 Chat Page │   │ 🗂️ Catalog Page │   │ 🔀 Multi-Doc Page │         │
│   └──────────────┘   └────────────────┘   └───────────────────┘         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  REST / JSON (CORS-guarded)
┌───────────────────────────────▼─────────────────────────────────────────┐
│  BACKEND API — FastAPI · Uvicorn  (:8000)                                │
│   ┌────────────┐ ┌────────────┐ ┌───────────────┐ ┌─────────────────┐   │
│   │ upload     │ │ chat       │ │ catalog       │ │ multi-doc       │   │
│   │ router     │ │ router     │ │ router        │ │ router          │   │
│   └────────────┘ └────────────┘ └───────────────┘ └─────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  route by mode / data context
┌───────────────────────────────▼─────────────────────────────────────────┐
│  AGENT LAYER — LangChain orchestration                                   │
│   ┌──────────────────┐ ┌─────────────────┐ ┌──────────────────┐          │
│   │ 🧭 Orchestrator  │ │ 🧮 General      │ │ 🗃️ SQL Agent      │          │
│   │ keyword/regex    │ │ calculator ·    │ │ Text-to-SQL →    │          │
│   │ MATH|REASON|OTHER│ │ percentage ·    │ │ SELECT-only →    │          │
│   │ (zero LLM cost)  │ │ unit convert ·  │ │ execute →        │          │
│   │                  │ │ logic reasoner  │ │ summarize        │          │
│   ├──────────────────┤ ├─────────────────┤ ├──────────────────┤          │
│   │ 📊 Data Agent    │ │ 📚 RAG Agent    │ │ 🔀 Multi-Doc     │          │
│   │ pandas summary + │ │ ChromaDB        │ │ retrieve from N  │          │
│   │ stats → Gemini · │ │ similarity →    │ │ collections →    │          │
│   │ session memory · │ │ grounded answer │ │ synthesize |     │          │
│   │ chart hints      │ │ + sources       │ │ compare | per-doc│          │
│   └──────────────────┘ └─────────────────┘ └──────────────────┘          │
└──────────────┬──────────────────────────────────────┬───────────────────┘
               │                                      │
┌──────────────▼──────────────────┐   ┌───────────────▼─────────────────┐
│  STORAGE & DATA                 │   │  AI MODELS (Gemini + local)     │
│  · ChromaDB (chroma_data/)      │   │  · gemini-2.5-flash             │
│  · SQLite catalog.db (SQLAlchemy)│   │    (reasoning · SQL · answers)  │
│  · In-memory DataFrames/session │   │  · all-MiniLM-L6-v2 (local)     │
│  · In-memory SQLite (sandboxed  │   │    (CPU embeddings, no quota)   │
│    per-session Text-to-SQL DB)  │   │  · Plotly chart generator       │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

### Layer responsibilities

| Layer | Components | Responsibility |
|---|---|---|
| **Frontend** | Next.js pages: Chat, Catalog, Multi-Doc | File upload, mode selection (auto / SQL / DataFrame / RAG / general), rendering answers, sources, Plotly charts. |
| **API** | `backend/routers/` — upload, chat, catalog, multi_doc | Request validation, upload size + file-type limits, agent routing, catalog stat updates. |
| **Agents** | `backend/agents/` — orchestrator, data, sql, rag, multi_doc, general | All LLM orchestration: prompts, tool use, SQL safety validation, retrieval, answer synthesis, chart hints. |
| **Pipelines** | `backend/pipelines/` — csv, json, pdf, sql loaders | Parse uploads into DataFrames or text chunks; mirror DataFrames into sandboxed in-memory SQLite. |
| **Storage** | ChromaDB, SQLite (`catalog.db`), in-memory session stores | Persistent embeddings, catalog metadata, per-session tabular data. |

---

## 3. Data Flow

### Flow 1 — File Upload & Ingestion (`POST /api/upload/{session_id}`)

1. Upload router validates the file type (`.csv .xlsx .xls .json .pdf`) and enforces the size cap (default 20 MB via `MAX_UPLOAD_MB`), then writes to a temp file.
2. **Tabular files** (CSV / Excel / JSON) → parsed into a pandas **DataFrame** (in-memory session store) and mirrored into a **sandboxed in-memory SQLite DB** for the SQL Agent.
3. **PDFs** → split into text chunks, embedded locally with `all-MiniLM-L6-v2` (sentence-transformers, server CPU — no API quota), ingested into a **session-scoped ChromaDB collection** for immediate chat.
4. PDFs are *also* ingested into a **permanent ChromaDB collection**; Gemini auto-generates a **summary, category, and tags**, saved to `catalog.db` — making the document searchable and reusable forever.

### Flow 2 — Chat Query Routing (`POST /api/chat`, see `backend/routers/chat.py`)

Priority order:

1. **Multiple `doc_ids`** → **Multi-Doc Agent**: retrieves chunks from every selected catalog collection, answers in the requested mode (synthesize / compare / per_doc).
2. **Single `doc_id`** → **RAG Agent** against that document's permanent collection; updates query-count / last-accessed stats.
3. **Mode = `general`**, or no data uploaded and the **Orchestrator** classifies the question as MATH or REASON → **General Agent** with local tools.
4. **Session documents present (rag/auto mode)** → **RAG Agent**: similarity search on the session ChromaDB collection → grounded answer + cited sources.
5. **Tabular data (sql/auto mode)** → **SQL Agent**: Gemini sees the schema → generates SQL → backend validates *single read-only SELECT/WITH only* (blocks INSERT/UPDATE/DROP/PRAGMA/chaining) → executes on in-memory SQLite → Gemini summarizes results.
6. **Otherwise** → **Data Agent**: compact DataFrame summary (shape, columns, sample rows, stats) + conversation memory → Gemini analyzes directly.
7. **Chart generation** — if the answer contains a hint like `Chart: bar on Department vs AttritionRate`, the chart generator builds an interactive **Plotly JSON figure**.
8. Response shape: `{ answer, chart_json, sql_query, sources }`.

### Routing decision summary

| Condition on the request | Agent selected | Data source |
|---|---|---|
| `doc_ids` (2–10 documents) | Multi-Doc Agent | Multiple permanent ChromaDB collections |
| `doc_id` (one catalog document) | RAG Agent | Permanent ChromaDB collection |
| Mode `general`, or no data + MATH/REASON detected | General Agent | Local tools + Gemini reasoning |
| Session PDF uploaded, mode `rag`/`auto` | RAG Agent | Session ChromaDB collection |
| Tabular data, mode `sql`/`auto` | SQL Agent | In-memory SQLite (SELECT-only) |
| Tabular data, mode `dataframe` | Data Agent | pandas DataFrame summary + memory |

---

## 4. The Agents (`backend/agents/`)

| Agent | File | What it does |
|---|---|---|
| 🧭 **Orchestrator** | `orchestrator_agent.py` | Classifies questions as MATH / REASON / OTHER with keyword + regex heuristics (detects `12 * 34`, "prove that", "syllogism"). **No LLM call** — zero API quota. |
| 📊 **Data Agent** | `data_agent.py` | Token-efficient DataFrame summary (shape, columns, sample rows, stats) → Gemini via LangChain ConversationChain. Per-session **conversation memory**; parses chart hints. |
| 🗃️ **SQL Agent** | `sql_agent.py` | Text-to-SQL: schema + question → Gemini generates SQL → **validated single read-only SELECT/WITH** → executed on sandboxed in-memory SQLite → Gemini summarizes. Returns the SQL for transparency. |
| 📚 **RAG Agent** | `rag_agent.py` | Similarity search over ChromaDB (session or permanent catalog collection) → top chunks injected as context → Gemini answers *only from that context* → cited source filenames. |
| 🔀 **Multi-Doc Agent** | `multi_doc_agent.py` | Retrieves chunks from each selected document's collection (up to 10), annotated by source. Modes: **synthesize**, **compare**, **per_doc**. |
| 🧮 **General Agent** | `general_agent.py` | LangChain tool-calling agent with 4 tools: `calculator` (AST-whitelisted safe eval — no `eval()`), `percentage`, `unit_converter` (km↔miles, kg↔lb, °C↔°F), `logical_reasoner` (chain-of-thought via Gemini). |

---

## 5. Tools & Technology Stack

| Category | Technology | Role |
|---|---|---|
| Frontend | Next.js 14 + TypeScript | App-router pages: Chat, Catalog, Multi-Doc. |
| Frontend | Tailwind CSS + shadcn/ui | Styling and UI components. |
| Backend | FastAPI + Uvicorn | REST API, CORS, Swagger at `/docs`; blocking LLM calls run in worker threads (plain `def` endpoints). |
| Backend | Pydantic | Request/response schemas (`ChatRequest`, `ChatResponse`, …). |
| AI / LLM | Google Gemini 2.5 Flash | All generation: SQL synthesis, analysis, RAG answers, reasoning, summarization. Free tier. |
| AI / LLM | sentence-transformers (`all-MiniLM-L6-v2`, local) | Text embeddings on the server's CPU — no API quota; ~80 MB model cached after first download. |
| AI / LLM | LangChain (core, community, google-genai, classic) | LLM wiring, conversation chains, tool-calling agent, retrievers, SQLDatabase utility. |
| Storage | ChromaDB (persistent client) | Vector store — session + permanent collections under `chroma_data/`. |
| Storage | SQLite + SQLAlchemy | `catalog.db` for the document catalog; in-memory SQLite per session for sandboxed Text-to-SQL. |
| Data | pandas + openpyxl + pypdf | CSV/Excel/JSON parsing; PDF text extraction. |
| Visualization | Plotly | Interactive charts from agent chart hints, delivered as JSON. |
| Ops | Docker Compose, python-dotenv, pytest | Containerized run, env config (`GOOGLE_API_KEY`, `ALLOWED_ORIGINS`, `MAX_UPLOAD_MB`), tests. |

### Safety & cost design choices

- **SQL sandboxing** — LLM-generated SQL runs only on a per-session in-memory DB; only single read-only SELECT/WITH statements pass validation.
- **Safe math** — calculator uses an AST operator whitelist, never `eval()`.
- **Upload guards** — file-type allowlist and configurable size cap before any processing; CORS restricted to configured origins.
- **Quota-aware routing** — regex/keyword orchestrator instead of an LLM call; compact DataFrame summaries keep token usage low.

---

## 6. API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload/{session_id}` | Upload a CSV, Excel, JSON, or PDF file. |
| DELETE | `/api/upload/{session_id}` | Clear all session data. |
| POST | `/api/chat` | Ask a question — body `{ session_id, question, mode, doc_id, doc_ids, multi_doc_mode }` → `{ answer, chart_json, sql_query, sources }`. |
| GET | `/api/catalog/list` | List catalog documents with summaries, categories, tags. |
| GET | `/api/catalog/search` | Search catalog documents. |
| POST | `/api/catalog/pin` | Pin or unpin a document. |
| GET | `/api/catalog/stats` | Catalog analytics. |
| DELETE | `/api/catalog/{doc_id}` | Delete a document and its vector collection. |
| POST | `/api/multi-doc/query` | Query multiple documents (synthesize / compare / per_doc). |
| GET | `/health` | Liveness probe. |

### Quick start

```bash
# 1. Configure environment
cp .env.example .env        # add your GOOGLE_API_KEY

# 2. Backend
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload    # → http://localhost:8000 (Swagger at /docs)

# 3. Frontend
cd frontend
npm install
npm run dev                  # → http://localhost:3000
```
