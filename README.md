[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20510252&assignment_repo_type=AssignmentRepo)

# Digital Artifacts and Data Mining Project

## Team 15
- Rylan Millar - 33334400
- Alex Batke - 34354803
- Cole Powrie - 77174209
- Liam Storgaard - 64584279
- Will Tilden - 61350294
- Luis Wen Luo - 10665891

## Current Project State
As of Milestone 2, the project is a full-stack system for ingesting zipped project artifacts, extracting contributor and skill signals, and generating portfolio and resume outputs.

Implemented components in this repository:
- FastAPI backend (`src/api`) with authentication, consent management, ingest, reporting, ranking, chronology, image handling, and generation APIs.
- Async analysis worker (`src/worker`) for parser, git metrics, local ML, and consent-gated external LLM analysis.
- PostgreSQL schema + Alembic migrations (`src/db/migrations`).
- React frontend (`frontend`) for sign-in/register, project upload, project views, top projects, skill timeline, and resume generation.
- CLI API client (`src/main.py`) for local demos and manual API workflows.

## Key Capabilities
- User registration/login with bearer session tokens.
- Privacy consent controls (`data_access`, `external_services`).
- ZIP ingest with deduplicated blob storage and incremental snapshots.
- Automatic analysis job queueing (`parser`, `git_metrics`, `local_ml`, `external_llm` depending on mode/consent).
- Project reporting, ranking, comparison, chronology, and identity auto-linking.
- Resume and portfolio showcase generation, editing, retrieval, PDF export, and deletion.
- Project image upload/retrieval endpoints.
- Safe deletion with blob garbage collection.

## Quick Start (Docker)
Prerequisites:
- Docker Engine
- Docker Compose v2

Start core services (DB + migrations + API + frontend):
```bash
docker compose up --build
```

Start with analysis worker + Ollama profile:
```bash
docker compose --profile analysis up --build
```

Service URLs (default):
- API: `http://localhost:5001`
- Frontend: `http://localhost:3000`
- Postgres: `postgresql://postgres:postgres@localhost:5432/artifactminer`

Stop services:
```bash
docker compose down
```

Stop and wipe volumes (destructive):
```bash
docker compose down -v
```

## Local Development (Without Docker)
Full setup details are documented here:
- [Development Setup](docs/setup/development.md)

Quick minimum steps:
1. Set `DATABASE_URL`.
2. Run migrations: `alembic upgrade head`.
3. Start API: `uvicorn src.api.app:app --host 0.0.0.0 --port 5001 --reload`.
4. Optionally start worker: `python -m src.worker.poller`.
5. Optionally start frontend in `frontend`: `npm start`.

## Testing
Project tests target PostgreSQL and the FastAPI app.

See full instructions:
- [Development Setup](docs/setup/development.md)

From repo root:
```bash
PYTHONPATH=. pytest
```

## Documentation Index
Core technical docs:
- [API Reference](docs/api/README_API.md)
- [Architecture and Data Flow](docs/architecture/current-state.md)
- [Development Setup](docs/setup/development.md)
- [Frontend Guide](docs/frontend/README.md)
- [ML Pipeline Notes](docs/ml/README.md)
- [CLI Usage](docs/cli/README.md)

Course/project docs:
- [Project Proposal](docs/proposal/project_proposal.md)
- [Team Contract](docs/contract/contract.md)
- [Meeting Minutes](docs/minutes/meeting1.md)
- [PR Template](docs/templates/pr.md)
- [Team Log Template](docs/templates/team_logs.md)
- [System Architecture Diagram Explanation](docs/system%20architecture%20design/explanation.md)
- [System Architecture Diagram (SVG)](docs/system%20architecture%20design/system_architecture_design.svg)
- [Data Flow Diagram Explanation](docs/data%20flow%20diagram/explanation.md)
- [Data Flow Diagram (SVG)](docs/data%20flow%20diagram/level1_DFD.svg)
- [Design Prototype Notes](docs/design/prototype.md)
