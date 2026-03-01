# Artifact Miner API Reference

This reference reflects the current implementation in `src/api/app.py`.

Base URL (default local):
```bash
export API="http://localhost:5001"
```

## Auth and Authorization Model
- Auth uses bearer tokens from `POST /auth/register` or `POST /auth/login`.
- Token-required endpoints:
  - `GET /auth/me`
  - `POST /auth/logout`
  - `DELETE /projects/{project_id}`
- Some endpoints accept optional bearer auth; if a token is present, ownership checks are enforced.
- Many read/write endpoints are currently not token-protected in code. Use network controls if deploying outside local/dev contexts.

Example header:
```bash
-H "Authorization: Bearer <TOKEN>"
```

## Consent Model
- `data_access` consent is required for ZIP ingest.
- `external_services` consent is required for ingest modes that queue external analysis (`external` or `both`) and for external analysis execution.
- If external analysis is requested without external consent, the API falls back to `local_ml` behavior.

## Common End-to-End Flow
1. Register/login.
2. Upload ZIP via `/projects/upload`.
3. Poll `/snapshots/{snapshot_id}/analyses`.
4. Fetch report `/projects/{project_id}/report`.
5. Generate outputs (`/resume/generate`, `/portfolio/generate`).

## Endpoint Catalog

### Health and Debug
- `GET /health`
  - Checks DB connectivity.
  - Response: `{"ok": true}`.

- `PUT /__debug/echo-upload`
  - Multipart test endpoint.
  - Form field: `file`.
  - Response includes filename, content type, byte size, SHA-256.

### Privacy and Auth
- `POST /privacy-consent`
  - Body:
    - `user_id` (optional; if omitted, a new user is created)
    - `consent_type` (`data_access` or `external_services`)
    - `granted` (boolean)
    - `version` (int, default `1`)
  - Also ensures a `user_config` row exists.

- `POST /auth/register`
  - Body:
    - `email`
    - `password` (min 8 chars)
    - `display_name` (optional)
    - `consent_data_access` (must be `true`)
  - Creates user, default portfolio, consent, auth account, and session.

- `POST /auth/login`
  - Body: `email`, `password`.
  - Returns new bearer session token.

- `GET /auth/me`
  - Bearer required.
  - Returns authenticated user payload.

- `POST /auth/logout`
  - Bearer required.
  - Revokes current session token.

### User Config
- `GET /users/{user_id}/config`
- `PUT /users/{user_id}/config`
  - Body: `{"config": {...}}` (full replacement).
- `PATCH /users/{user_id}/config`
  - Body: partial JSON object (deep merge semantics).

Default config shape:
```json
{
  "identity": {
    "match_emails": [],
    "match_names": [],
    "project_contributor_map": {}
  },
  "ranking": {
    "mode": "auto",
    "weights": {
      "user_commits": 1.0,
      "other_commits": 0.1,
      "contributor_count": 0.0
    },
    "allow_no_user_score": false,
    "manual_project_order": [],
    "manual_ranks": {}
  },
  "chronology": {
    "project_order": [],
    "project_dates": {},
    "skill_first_seen": {},
    "skill_order": []
  },
  "highlights": {
    "skills": []
  },
  "showcase": {
    "selected_project_ids": []
  },
  "comparison": {
    "attributes": []
  }
}
```

Resume PDF filters are read from `config.resume_filters` (optional):
```json
{
  "show_summary": true,
  "show_bullets": true,
  "max_bullets": 6,
  "show_metadata": true,
  "show_project_profile": true,
  "show_metrics": true,
  "show_tech_stack": true,
  "show_evidence": true
}
```

### Ingest and Snapshot Analysis
- `POST /projects/upload`
  - Multipart form fields:
    - `file` (`.zip`, required)
    - `user_id` (optional)
    - `portfolio_id` (optional)
    - `project_name` (optional)
    - `snapshot_label` (optional)
    - `analysis_mode` (optional; `auto` | `local` | `external` | `both`, default `auto`)
  - `analysis_mode` behavior:
    - `local`: queue `parser`, `git_metrics`, `local_ml`
    - `external`: queue `parser`, `git_metrics`, `external_llm` (requires external consent)
    - `both`: queue all four (requires external consent)
    - `auto`: queue external only when latest external consent is granted; otherwise queue local only
  - Returns:
    - `user_id`
    - `portfolio_id`
    - `created[]` and `skipped[]` entries with `project_id`, `project_name`, `snapshot_id`, `zip_sha256`

- `GET /snapshots/{snapshot_id}/analyses`
  - Lists analyses for snapshot with status/order.
  - Includes projected `error` field from `output_json.error`.

- `GET /snapshots/{snapshot_id}/skills?limit=20`
  - `limit` range: `1..200`.
  - Returns top skills from the latest completed `local_ml` analysis.

- `POST /snapshots/{snapshot_id}/external-analysis`
  - Creates/returns pending `external_llm` job if external consent granted.
  - Otherwise creates/returns `local_ml` fallback job.

- `GET /snapshots/{snapshot_id}/external-analysis`
  - Returns latest analysis selected by consent policy:
    - external consent granted -> latest `external_llm`
    - otherwise -> latest `local_ml`

### Skills Catalog
- `GET /skills`
- `GET /skills?category=<category>`

### Project Endpoints
- `GET /projects`
  - Query:
    - `portfolio_id` (optional)
    - `user_id` (optional)
  - Rules:
    - Without token: must provide either `portfolio_id` or `user_id`.
    - With token: `user_id` is forced to authenticated user; if omitted, default portfolio from token context is used.
  - Returns ranked project list with metrics and latest snapshot metadata.

- `GET /projects/compare?project_ids=<id>&project_ids=<id>&attributes=...`
  - `project_ids` required (repeated or comma-separated).
  - `attributes` optional (repeated or comma-separated).
  - Attribute precedence:
    1. explicit `attributes` query
    2. `user_config.comparison.attributes`
    3. API default set
  - All projects must belong to the same portfolio.

- `GET /projects/{project_id}`
  - Returns project metadata, aggregated metrics, `latest_snapshot`, and `evidence`.

- `PATCH /projects/{project_id}`
  - Partial update fields:
    - `display_name`
    - `user_role`
    - `evidence_json` or `evidence` (mutually exclusive)
    - `metrics`, `feedback`, `evaluation` (merged into evidence object)
  - Empty patch returns `400`.

- `DELETE /projects/{project_id}`
  - Bearer required.
  - Validates project belongs to authenticated user.
  - Performs cascading safe delete + blob GC.

- `GET /projects/{project_id}/report`
  - Query:
    - `include_raw_analyses` (default `false`)
    - `include_framework_detection` (default `true`)

- `GET /projects/{project_id}/contributors`
  - Returns contributor list with commit totals and `is_user` flag.

- `POST /projects/{project_id}/contributors/{contributor_id}/set-user`
  - Body:
    - `is_user` (default `true`)
    - `unset_others` (default `true`)
    - `persist_to_config` (default `true`)

- `POST /projects/{project_id}/refresh-collaboration`
  - Recomputes and persists `collaboration_type` from contributor count.

- `GET /projects/{project_id}/latest-resume`
  - Returns latest generated resume item for project.

### Project Image Endpoints
- `PUT /projects/{project_id}/image`
  - Multipart form field: `file`.
  - `project_id` must be a UUID path value.
  - Upserts file blob + project showcase thumbnail reference.

- `GET /projects/{project_id}/image/raw`
  - Returns binary image payload.

- `GET /projects/{project_id}/image/meta`
  - Returns image metadata (project id, blob sha, mime type).

- `GET /projects/{project_id}/image`
  - Returns base64 JSON form:
    - `project_id`
    - `thumbnail_blob_sha256`
    - `mime_type`
    - `data_base64`

- `DELETE /projects/{project_id}/image`
  - Clears thumbnail reference on showcase row.

### Portfolio Endpoints
- `GET /portfolio/{portfolio_id}`
  - Returns portfolio row.
  - If bearer is provided, ownership is enforced.

- `GET /portfolio/{portfolio_id}/top-projects?limit=5`
  - `limit` range: `1..50`.
  - Returns ranked project summary list.

- `POST /portfolio/generate`
  - Body:
    - `portfolio_id` (required)
    - `limit` (default `5`, range `1..50`)
    - `persist` (default `true`)
  - Generates top-project artifacts and optionally persists showcase rows.

- `GET /portfolio/{portfolio_id}/generated?limit=50`
  - Returns persisted `portfolio_showcases` artifacts.
  - `limit` range: `1..200`.

- `POST /portfolio/{showcase_id}/edit`
  - Path value is showcase ID (despite `/portfolio/` prefix naming).
  - Body:
    - `title` (optional)
    - `summary_text` (optional)

- `DELETE /portfolio/showcases/{showcase_id}`
  - Deletes showcase artifact and GC's unreferenced thumbnail blob.

### Resume Endpoints
- `POST /resume/generate`
  - Body:
    - `project_id`
    - `prefer_external_bullets` (optional, default `true`)

- `GET /resume/{resume_id}`
  - Returns stored resume artifact with content JSON and thumbnail metadata.

- `POST /resume/{resume_id}/edit`
  - Body:
    - `summary_text` (optional)
    - `resume_bullets` (optional string array)

- `GET /resume/{resume_id}/pdf`
  - Returns PDF bytes.
  - Reads display/toggle filters from owning user's `user_config.resume_filters`.

- `DELETE /resume/{resume_id}`
  - Deletes stored resume artifact.

### Identity and Linking
- `POST /users/{user_id}/identity/rules`
  - Body:
    - `match_emails` (array)
    - `match_names` (array)

- `POST /users/{user_id}/identity/auto-link`
  - Body:
    - `portfolio_id` (optional; if omitted, scans all user portfolios)
    - `dry_run` (default `false`)
    - `persist_project_map` (default `true`)

### Chronology Endpoints
- `GET /portfolio/{portfolio_id}/projects/chronological?direction=asc&limit=200`
  - `direction`: `asc` or `desc`
  - `limit`: `1..2000`
  - Applies chronology overrides from `user_config.chronology`.

- `GET /portfolio/{portfolio_id}/skills/chronological?direction=asc&limit=500`
  - `direction`: `asc` or `desc`
  - `limit`: `1..5000`
  - Uses local ML outputs (or fallback skill rows) and chronology overrides.

### Deletion and GC Endpoints
- `DELETE /snapshots/{snapshot_id}`
  - Cascades related rows and garbage-collects unreferenced blobs.

- `DELETE /analyses/{analysis_id}`
  - Deletes one analysis row.

### Legacy Git Utility Endpoints
These are utility routes for zipped git repositories:
- `POST /extract-commits/`
- `POST /extract-commit-counts/`
- `POST /give-users-roles/`

Each expects multipart `file` upload and returns commit-derived data.

## Quick Curl Examples

Register:
```bash
curl -sS -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123","display_name":"You","consent_data_access":true}'
```

Upload ZIP:
```bash
curl -sS -X POST "$API/projects/upload" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@./project.zip" \
  -F "project_name=my-project" \
  -F "analysis_mode=local"
```

Get ranked projects for authenticated user:
```bash
curl -sS "$API/projects" -H "Authorization: Bearer <TOKEN>"
```

Generate resume + download PDF:
```bash
curl -sS -X POST "$API/resume/generate" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<PROJECT_ID>","prefer_external_bullets":true}'

curl -L -o resume.pdf "$API/resume/<RESUME_ID>/pdf"
```

## Notes
- For full integration examples, see `src/main.py` (CLI wrapper around these endpoints).
- `README_API.md` at repo root is retained as a pointer; canonical API docs are here.
