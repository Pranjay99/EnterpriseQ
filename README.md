# Enterprise Q

An AI-powered enterprise data assistant that lets you query structured data, analyze documents, and get intelligent answers through a natural language interface.

<img width="1901" height="946" alt="Screenshot 2026-05-18 154951" src="https://github.com/user-attachments/assets/f240d68c-2dff-49bd-84d4-75eb9bb4df93" />


## Features

- **Text-to-SQL** — Ask questions about CSV, Excel, or JSON files and get SQL-powered answers
- **DataFrame Analysis** — Pandas-based analysis with automatic chart generation
- **Document Q&A (RAG)** — Upload PDFs and ask questions grounded in the document content
- **Math & Reasoning** — Calculator, unit converter, and chain-of-thought reasoning
- **Document Catalog** — Permanently store PDFs with auto-generated summaries, categories, and tags
- **Multi-Document Analysis** — Synthesize, compare, or query across up to 10 documents at once
- **Interactive Charts** — Plotly visualizations generated automatically from your data

  <img width="1906" height="948" alt="Screenshot 2026-05-18 155027" src="https://github.com/user-attachments/assets/303887d9-9e74-40ab-9ef5-0b3c4154eaa8" />


## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Uvicorn |
| LLM | Google Gemini 2.5 Flash (free tier) |
| Embeddings | Google Gemini Embedding 001 |
| Vector DB | ChromaDB |
| Data | Pandas, SQLAlchemy, SQLite |
| Visualization | Plotly |

## Project Structure

```
EnterpriseQ/
├── backend/
│   ├── agents/          # LLM orchestration (SQL, RAG, DataFrame, General, Multi-doc)
│   ├── models/          # Pydantic schemas + SQLAlchemy ORM
│   ├── pipelines/       # Data loaders (CSV, JSON, PDF, SQL)
│   ├── routers/         # FastAPI route handlers
│   ├── utils/           # Vector store, chart generator, memory, prompts
│   └── main.py          # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── app/         # Next.js pages (chat, catalog, multi-doc)
│       ├── components/  # UI components (chat, nav, charts)
│       ├── lib/         # API client, utilities
│       └── types/       # TypeScript interfaces
├── tests/
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Google AI Studio](https://aistudio.google.com/) API key (free)

### 1. Clone the repository

```bash
git clone https://github.com/Pranjay99/EnterpriseQ.git
cd EnterpriseQ
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```
GOOGLE_API_KEY=your_api_key_here
```

### 3. Start the backend

```bash
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

1. **Chat page** — Upload a CSV, Excel, JSON, or PDF file. Select a query mode and start asking questions in natural language.
2. **Catalog page** — Browse all uploaded PDFs. Pin important documents, filter by category, and chat with any document directly.
3. **Multi-Doc page** — Select multiple documents and synthesize insights, compare content, or get per-document answers in one query.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload/{session_id}` | Upload a data file or PDF |
| DELETE | `/api/upload/{session_id}` | Clear session data |
| POST | `/api/chat` | Send a chat message |
| GET | `/api/catalog/list` | List all catalog documents |
| GET | `/api/catalog/search` | Search documents |
| POST | `/api/catalog/pin` | Pin or unpin a document |
| GET | `/api/catalog/stats` | Get catalog analytics |
| DELETE | `/api/catalog/{doc_id}` | Delete a document |
| POST | `/api/multi-doc/query` | Query multiple documents |

## License

MIT
