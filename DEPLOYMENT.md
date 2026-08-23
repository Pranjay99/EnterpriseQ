# Deploying Enterprise Q

Architecture: **frontend on Vercel** (free Hobby tier) + **backend on Google Cloud Run**
(free tier), with Supabase (auth) and Gemini (LLM) already cloud-hosted.

```
Browser ──▶ Vercel (Next.js)  ──▶ Cloud Run (FastAPI + local embeddings)
                │                        │
                └──▶ Supabase Auth       ├──▶ Gemini API
                                         └──▶ SQLite + ChromaDB (in-container)
```

---

## Part 1 — Backend on Cloud Run

### One-time setup

1. Create/log into a Google Cloud account at https://console.cloud.google.com
   (requires a card; the free tier itself doesn't charge).
2. Create a project, e.g. `enterprise-q`.
3. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install — then:
   ```bash
   gcloud auth login
   gcloud config set project <YOUR_PROJECT_ID>
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```

### Deploy

From the repo root (the `Dockerfile` here is what gets built):

```bash
gcloud run deploy enterprise-q-api ^
  --source . ^
  --region us-central1 ^
  --memory 2Gi --cpu 2 --cpu-boost ^
  --timeout 300 ^
  --min-instances 0 --max-instances 2 ^
  --allow-unauthenticated ^
  --set-env-vars "SUPABASE_URL=https://<your-ref>.supabase.co,ALLOWED_ORIGINS=https://<your-app>.vercel.app,MAX_UPLOAD_MB=20"
```

Set the Gemini key separately so it never lands in shell history / build logs —
best practice is Secret Manager:

```bash
echo -n "<YOUR_GEMINI_KEY>" | gcloud secrets create google-api-key --data-file=-
gcloud run services update enterprise-q-api --region us-central1 ^
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest"
```

(Quick-and-dirty alternative: add `GOOGLE_API_KEY=...` to `--set-env-vars`.)

The first deploy takes ~10 min (Cloud Build builds the image, which includes
CPU PyTorch and the baked-in embedding model). The command prints your service
URL, e.g. `https://enterprise-q-api-xxxxx-uc.a.run.app` — verify:

```bash
curl https://<service-url>/health
```

### Sizing notes

- `--memory 2Gi` — PyTorch + MiniLM need ~1.5 GB; 1Gi will OOM.
- `--cpu-boost` — halves the model-load time on cold starts.
- `--min-instances 0` — free (scales to zero); first request after idle takes
  ~30–60 s. Set `--min-instances 1` to eliminate cold starts (~$10+/mo — not free).

---

## Part 2 — Frontend on Vercel

1. Commit and push the repo to GitHub (make sure `.env` is NOT committed — it's
   git-ignored; only `.env.example` should be in the repo).
2. Go to https://vercel.com → Add New → Project → import the GitHub repo.
3. **Root Directory:** set to `frontend` (critical — the repo root is not the Next.js app).
4. Environment Variables (Production):
   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | your Cloud Run service URL (no trailing slash) |
   | `NEXT_PUBLIC_SUPABASE_URL` | same as local `.env.local` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | same as local `.env.local` |
5. Deploy. Vercel gives you `https://<your-app>.vercel.app`.

---

## Part 3 — Wire the three services together

1. **CORS**: make sure the Cloud Run env var `ALLOWED_ORIGINS` exactly matches
   your Vercel URL (comma-separate to also keep `http://localhost:3000` for dev).
2. **Supabase** → Authentication → URL Configuration:
   - Site URL: `https://<your-app>.vercel.app`
   - Redirect URLs: add `https://<your-app>.vercel.app/**`
3. **Google OAuth** (console.cloud.google.com → Credentials → your OAuth client):
   the Supabase callback URL is already there from local setup; nothing new needed
   unless you add a custom domain.

Then open the Vercel URL, sign in with Google, upload a CSV, ask a question.

---

## Known limitations of this (free) setup

| Limitation | Why | Fix when it matters |
|---|---|---|
| **Catalog data resets** on redeploy/restart | `catalog.db`, `chroma_data/`, `catalog_files/` live on the container's ephemeral disk | Migrate catalog to Supabase Postgres + a hosted vector DB (pgvector) |
| Sessions don't survive restarts | in-memory DataFrames/SQLite | Redis/Valkey or re-upload |
| Cold start ~30–60 s after idle | scale-to-zero + model load | `--min-instances 1` (paid) |
| One shared Gemini quota | free tier | provider fallbacks (Groq/Cerebras) or paid tier |

## Redeploying after changes

Backend: rerun the same `gcloud run deploy` command.
Frontend: `git push` — Vercel auto-deploys every push to the main branch.
