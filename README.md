# Nexus Resolve

Production-grade **Multi-Database Entity Resolution & Unified Data Repository**.

Ingest CSV files and SQL dumps from many source systems, auto-map columns to a canonical schema, normalize identifiers, match records with a rule hierarchy, and progressively enrich a single master entity with full source traceability.

Public evaluation UI is login-free.

## Architecture

- **Frontend**: Next.js 14 + Tailwind CSS dashboard (datasets, mapping review, progressive search, live metrics)
- **Backend**: FastAPI + SQLAlchemy
- **Store**: SQLite by default (swap `DATABASE_URL` for PostgreSQL)
- **Indexes**: B-tree indexes on normalized email, phone, username, member_id
- **Batching**: 5,000-row chunks, background worker thread (swap-in Celery/RQ via the same job model)
- **Field mapping**: rule-based synonym matcher with optional LLM refinement (`USER_LLM_*`)

Pipeline stages: `Uploaded -> Inspecting -> Field mapping -> Cleaning -> Indexing -> Matching -> Enriching -> Completed`.

Matching hierarchy:

1. Exact normalized email
2. Exact normalized phone
3. Username
4. Member / customer ID

Unmatched records become new master entities marked `unmatched` for later imports.

## Repository layout

```
backend/                 FastAPI application
frontend/                Next.js dashboard
tests/                   Pytest suite
scripts/                 helpers
.github/workflows/       CI + deploy
docker-compose.yml       local containers
```

## Local development

```bash
python3 -m pip install --break-system-packages -r backend/requirements.txt pytest
cd frontend && npm install && cd ..
chmod +x start.sh
./start.sh
```

- UI: `http://localhost:3000`
- API: `http://localhost:8000/api/health`
- OpenAPI: `http://localhost:8000/docs`

Seed four overlapping sample databases from the Overview page (**Load sample datasets**) or:

```bash
PYTHONPATH=backend python -c "from app.main import bootstrap; print(bootstrap())"
```

Samples:

- Database A CRM: `email` / `full_name` / `mobile_number`
- Database B billing: `email_id` / `address`
- Database C directory: `username` / `contact_no` / `company`
- Database D members: SQL dump `member_id` / `email_address` / `user_name`

Search `john.carter@example.com` after seeding to see BFS enrichment across sources.

## Tests

```bash
PYTHONPATH=backend pytest -q
cd frontend && npx tsc --noEmit
```

## Docker

```bash
docker compose up --build
```

UI on port 3000, API on port 8000.

## Environment

Copy `.env.example`. LLM mapping is optional; the rule-based matcher runs without keys.

```
USER_LLM_API_KEY=your-api-key-here
USER_LLM_BASE_URL=https://api.deepseek.com/v1
USER_LLM_MODEL=deepseek-chat
```

## Push to GitHub

Replace `YOUR_USER/YOUR_REPO` with the existing repository.

```bash
git init
git checkout -b main
git add .
git commit -m "feat: multi-database entity resolution platform"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

If the repo already exists with a remote:

```bash
git add .
git commit -m "feat: multi-database entity resolution platform"
git branch -M main
git push -u origin main
```

## Free-tier hosting (zero-downtime)

### Render (recommended, single public URL)

One-click Blueprint (login-free web service from this repo):

https://render.com/deploy?repo=https://github.com/Tejk20/Entity-Resolution-Unified-Data-Repository2

Manual setup:

1. New Blueprint / Web Service from `Tejk20/Entity-Resolution-Unified-Data-Repository2`
2. Runtime: Python. Build: `bash scripts/render-build.sh`. Start: `bash scripts/render-native-start.sh`
3. Health check: `/api/health`
4. Env: `PYTHONPATH=backend`, `CORS_ORIGINS=*`, `INTERNAL_API_URL=http://127.0.0.1:8000`

The start script runs FastAPI on localhost:8000 and Next.js on `$PORT`, so Render exposes one public URL. `render.yaml` is the Blueprint source. Docker alternative: root `Dockerfile`.

### Vercel (UI)

```bash
cd frontend
npx vercel --yes
```

Set `INTERNAL_API_URL` to the Render API origin. Rewrites proxy `/api/*` to the backend.

### Railway (API + web)

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Connect the GitHub repo in the Railway dashboard so every push to `main` deploys automatically.

### GitHub Actions

`.github/workflows/ci.yml` runs pytest + TypeScript on every push/PR.

`.github/workflows/deploy.yml` runs on `main`. Optional secrets:

- `RENDER_DEPLOY_HOOK` — Render deploy hook URL
- `RAILWAY_TOKEN` — Railway API token

Connecting the GitHub app on Render/Railway/Vercel is enough for automatic deploys without extra secrets.

## Evaluation walkthrough

1. Open the dashboard (no login)
2. Click **Load sample datasets**
3. Watch pipeline stages on Overview
4. Open Datasets to review AI field mappings
5. Search `john.carter@example.com`, `9876543210`, or `jcarter`
6. Inspect the master entity card, hop graph, and source attribution table
