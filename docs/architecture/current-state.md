# Current Architecture and Data Flow

This document describes the current implemented architecture (API + DB + worker + frontend).

## Service Topology
- `frontend` (React, port `3000`): browser UI for auth, upload, project views, timeline, and resume actions.
- `api` (FastAPI, port `5000` inside container, mapped to `5001`): REST endpoints for auth, consent, ingest, reports, generation, and media retrieval.
- `db` (PostgreSQL 16): system of record for users, portfolios, projects, snapshots, analyses, and generated artifacts.
- `worker` (Python poller): async execution of queued analyses in `analyses` table.
- `ollama` (optional profile): external LLM provider used by worker when consent allows.

## Ingestion Pipeline
1. Client uploads `.zip` to `POST /projects/upload`.
2. API validates extension and consent (`data_access`).
3. ZIP entries are normalized and unsafe paths are skipped.
4. Files are deduplicated into `file_blobs` using SHA-256.
5. `snapshot_files` links snapshot-relative paths to blob records.
6. API queues analysis jobs in `analyses` based on `analysis_mode` and consent.

## Analysis Types
- `parser`
  - File/language/activity statistics.
  - Produces counts, top languages, text chunk totals.

- `git_metrics`
  - Reconstructs snapshot into temp workspace.
  - Finds git repos and commit contributions per author.
  - Updates `contributors`, `project_contributors`, `contribution_events`.
  - Refreshes project `collaboration_type`.

- `local_ml`
  - Runs local weakly-supervised multi-label skill detection.
  - Persists selected skill outputs into `analysis_skills` + `skills`.

- `external_llm`
  - Builds prompt from parser/git/local_ml outputs (not raw source blobs).
  - Runs Ollama model and stores structured summary payload.
  - Fallback behavior to local ML exists if external path cannot run.

## Worker Execution Model
- Polls `analyses` rows with `status='pending'`.
- Claims one job using `FOR UPDATE SKIP LOCKED` semantics.
- Marks job `running`, executes handler, writes completion output.
- On failure marks `failed` with error payload.

## Core Data Model (Key Tables)
- Identity and auth:
  - `users`, `auth_accounts`, `auth_sessions`
- Privacy and configuration:
  - `privacy_consents`, `user_config`
- Portfolio graph:
  - `portfolios`, `projects`, `snapshots`
- Content-addressed storage:
  - `file_blobs`, `snapshot_files`
- Analysis and skill indexing:
  - `analyses`, `skills`, `analysis_skills`
- Collaboration:
  - `contributors`, `project_contributors`, `contribution_events`
- Generated artifacts:
  - `resume_items`, `portfolio_showcases`

## Ranking and Chronology Behavior
User-adjustable controls are stored under `user_config.config_json`:
- `ranking`: auto/weighted/manual ordering behavior.
- `chronology`: project order/date and skill first-seen overrides.
- `comparison`: default attributes for `/projects/compare`.
- `highlights` and `showcase`: skill/project selections for generated outputs.

## Consent-Gated External Behavior
- External analysis execution is allowed only when latest `external_services` consent is granted.
- Ingest in external modes (`external`, `both`) is blocked without consent.
- Explicit external analysis requests return local fallback when consent is missing.

## Safe Deletion Model
Delete endpoints (`snapshot`, `project`, `showcase`) use GC helpers that:
- remove DB rows first,
- only remove blobs if they are unreferenced by both `snapshot_files` and `portfolio_showcases`.

This preserves shared blobs and prevents accidental data loss for other snapshots/projects.

## Related Diagrams
- [System Architecture Explanation](../system%20architecture%20design/explanation.md)
- [System Architecture SVG](../system%20architecture%20design/system_architecture_design.svg)
- [Data Flow Explanation](../data%20flow%20diagram/explanation.md)
- [Data Flow SVG](../data%20flow%20diagram/level1_DFD.svg)
