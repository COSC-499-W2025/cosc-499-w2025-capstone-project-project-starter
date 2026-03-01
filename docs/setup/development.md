# Development Setup

This document covers local and Docker workflows for the current repository.

## Prerequisites
- Python 3.11
- Node.js + npm (for frontend)
- PostgreSQL 16 (local) or Docker
- `alembic` and project Python dependencies installed

## Option A: Docker Compose (Recommended)
From repo root:
```bash
docker compose up --build
```

With worker + Ollama:
```bash
docker compose --profile analysis up --build
```

Default endpoints:
- API: `http://localhost:5001`
- Frontend: `http://localhost:3000`
- Postgres: `localhost:5432` (`artifactminer`)

Stop:
```bash
docker compose down
```

Wipe volumes (destructive):
```bash
docker compose down -v
```

## Option B: Local Run

### 1. Install Python dependencies
API-side minimum:
```bash
pip install -r requirements/api.txt
```

Worker-side (includes API deps):
```bash
pip install -r requirements/worker.txt
```

### 2. Configure environment
Required:
```bash
export DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/artifactminer'
```

Common optional variables:
```bash
export ARTIFACT_MINER_BLOBSTORE='blobstore'
export CORS_ALLOW_ORIGINS='http://localhost:3000'
export AUTH_SESSION_TTL_DAYS='14'
export ARTIFACT_MINER_LOG_LEVEL='INFO'
```

Worker/analysis optional variables:
```bash
export WORKER_POLL_INTERVAL_SECS='2.0'
export OLLAMA_MODEL='mistral'
export OLLAMA_TIMEOUT_SECS='120'
export OLLAMA_MAX_PROMPT_CHARS='24000'
export LOCAL_ML_THRESHOLD='0.5'
export LOCAL_ML_MAX_FILE_CHARS='1000000'
export LOCAL_ML_MAX_CHUNKS_TOTAL='5000'
export LOCAL_ML_EMBED_BATCH='16'
```

### 3. Run migrations
```bash
alembic upgrade head
```

### 4. Start API
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 5001 --reload
```

### 5. Start worker (optional)
```bash
python -m src.worker.poller
```

### 6. Start frontend (optional)
```bash
cd frontend
npm install
npm start
```

Set frontend API target if needed:
```bash
export REACT_APP_API_URL='http://localhost:5001'
```

## Testing
Tests are configured in `pytest.ini` and `tests/conftest.py`.

### 1. Test DB setup
```bash
export DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/artifactminer_test'
psql 'postgresql://postgres:postgres@localhost:5432/postgres' -c 'CREATE DATABASE artifactminer_test;' || true
alembic upgrade head
```

### 2. Run tests
```bash
PYTHONPATH=. pytest
```

## CLI API Client
A local CLI wrapper exists at `src/main.py`.

Examples:
```bash
python src/main.py --api-url http://localhost:5001 health
python src/main.py upload examples.zip --wait
python src/main.py demo example.zip
```

See [CLI Usage](../cli/README.md) for more.

## Troubleshooting
- `RuntimeError: DATABASE_URL is required`:
  - Set `DATABASE_URL` before starting API/worker.
- Upload rejected with `data_access consent not granted`:
  - Call `POST /privacy-consent` with `consent_type=data_access` and `granted=true`.
- Upload in `external`/`both` mode rejected:
  - Grant `external_services` consent first.
- No analyses complete:
  - Ensure worker is running.
- External analysis fails:
  - Worker falls back to `local_ml` if consent is missing or external execution fails.
