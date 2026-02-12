# Common actions with the API

The following assumes you use:

```bash
export API="http://localhost:5001"
```

## Authentication (frontend login flow)
Create an account (also grants `data_access` consent and creates a default portfolio):

```bash
curl -sS -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123","display_name":"You","consent_data_access":true}'
```

Log in:

```bash
curl -sS -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}'
```

Use the returned bearer token:

```bash
curl -sS "$API/auth/me" -H "Authorization: Bearer <TOKEN>"
curl -sS "$API/projects" -H "Authorization: Bearer <TOKEN>"
```

## Milestone 1: consent, ingest, reports, skills, ranking, deletion, chronology
1) Provide consent (and create a user)

You must create a user via consent submission. This also ensures a user_config row exists.

Create a new user and grant data access consent:

```bash
curl -sS "$API/privacy-consent" \
  -H "Content-Type: application/json" \
  -d '{"consent_type":"data_access","granted":true,"version":1}'
```

Optionally grant external-services consent (required for external analysis paths):

```bash
curl -sS "$API/privacy-consent" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<USER_ID>","consent_type":"external_services","granted":true,"version":1}'
```

2) Upload a zip (ingest projects/snapshots)

Uploads a zip containing one or more projects; creates/updates portfolio + projects + snapshots; stores files into the blobstore with dedupe.

Upload (server will create a default portfolio if needed):

```bash
curl -sS "$API/projects/upload" \
  -F "file=@./test-data.zip" \
  -F "user_id=<USER_ID>"
```

Target an existing portfolio explicitly:

```bash
curl -sS "$API/projects/upload" \
  -F "file=@./test-data.zip" \
  -F "user_id=<USER_ID>" \
  -F "portfolio_id=<PORTFOLIO_ID>" \
  -F "snapshot_label=initial_import"
```

Notes:
- The upload must be a .zip file; non-zip yields HTTP 400.
- The response includes user_id, portfolio_id, and a list of created/skipped projects.

3) Retrieve a portfolio

```bash
curl -sS "$API/portfolio/<PORTFOLIO_ID>"
```

4) List projects (rank-aware list)

`GET /projects` requires either portfolio_id or user_id.
If you pass user_id, it will attempt to use that user's default portfolio (name='default').

List by portfolio:

```bash
curl -sS "$API/projects?portfolio_id=<PORTFOLIO_ID>"
```

List by user:

```bash
curl -sS "$API/projects?user_id=<USER_ID>"
```

This list includes derived contribution metrics and a rank score (when the user identity has been linked to a contributor).

5) Project report (single project)
```bash
curl -sS "$API/projects/<PROJECT_ID>/report"
```

Optional flags:

```bash
curl -sS "$API/projects/<PROJECT_ID>/report?include_raw_analyses=false&include_framework_detection=true"
```

6) List project contributors, set “which contributor is me" - Git projects only

List contributors (and observed commit totals):

```bash
curl -sS "$API/projects/<PROJECT_ID>/contributors"
```

Mark a contributor as the user for that project (sets project_contributors.is_user, and can persist mapping into user_config):

```bash
curl -sS "$API/projects/<PROJECT_ID>/contributors/<CONTRIBUTOR_ID>/set-user" \
  -H "Content-Type: application/json" \
  -d '{"is_user":true,"unset_others":true,"persist_to_config":true}'
```

Recompute and persist collaboration type (individual vs collaborative) based on contributor count:

```bash
curl -sS -X POST "$API/projects/<PROJECT_ID>/refresh-collaboration"
```

7) Configure identity rules

Store identity match rules in user_config to support auto-linking:

```bash
curl -sS -X POST "$API/users/<USER_ID>/identity/rules" \
  -H "Content-Type: application/json" \
  -d '{"match_emails":["you@example.com"],"match_names":["Your Name"]}'
```

Auto-link contributors across a portfolio (or all portfolios). Use dry_run=true to preview:

```bash
curl -sS -X POST "$API/users/<USER_ID>/identity/auto-link" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id":"<PORTFOLIO_ID>","dry_run":false,"persist_project_map":true}'
```

8) Snapshot analyses and skills

List analyses for a snapshot:

```bash
curl -sS "$API/snapshots/<SNAPSHOT_ID>/analyses"
```

List top skills for a snapshot (from latest completed local_ml):

```bash
curl -sS "$API/snapshots/<SNAPSHOT_ID>/skills?limit=20"
```

List all unique skills across the entire platform (global catalog)

```bash
curl -sS "$API/skills"
```

List global skills filtered by category (e.g., 'backend', 'frontend')

```bash
curl -sS "$API/skills?category=backend"
```

9) External analysis request + retrieval (consent-gated)

Request external analysis (or fall back to local_ml if external consent not granted):

```bash
curl -sS -X POST "$API/snapshots/<SNAPSHOT_ID>/external-analysis"
```

Fetch the latest analysis output selected by the consent logic:

```bash
curl -sS "$API/snapshots/<SNAPSHOT_ID>/external-analysis"
```

10) Portfolio top-ranked projects (summary view)

Returns a ranked list with best-effort summaries (derived from latest parser/local_ml outputs per project):

```bash
curl -sS "$API/portfolio/<PORTFOLIO_ID>/top-projects?limit=5"
```
11) Chronological lists (portfolio-level)

Chronological list of projects (distinct from the ranked /projects list):

```bash
curl -sS "$API/portfolio/<PORTFOLIO_ID>/projects/chronological?direction=asc&limit=200"
```

Chronological list of skills exercised across the portfolio:

```bash
curl -sS "$API/portfolio/<PORTFOLIO_ID>/skills/chronological?direction=asc&limit=500"
```

12) Safe deletion (insights + snapshots) with garbage collection

Delete a snapshot and cascade-delete derived rows; unreferenced blobs are garbage-collected (shared blobs remain if referenced elsewhere):

```bash
curl -sS -X DELETE "$API/snapshots/<SNAPSHOT_ID>"
```

Delete a specific analysis by ID:

```bash
curl -sS -X DELETE "$API/analyses/<ANALYSIS_ID>"
```

13) Retrieve project metadata and metrics

Fetch a single project's core details, including aggregated contribution metrics (total commits vs user commits) and the latest snapshot timestamp:

```bash
curl -sS "$API/projects/<PROJECT_ID>"
```

## Milestone 1/2 bridge: generated artifacts (resume items + portfolio showcases)

1) Generate a resume item (stored artifact)
```bash
curl -sS -X POST "$API/resume/generate" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<PROJECT_ID>","prefer_external_bullets":true}'
```

Retrieve a previously generated resume item:

```bash
curl -sS "$API/resume/<RESUME_ID>"
```

Download as a PDF:

```bash
curl -L -o "resume-<RESUME_ID>.pdf" "$API/resume/<RESUME_ID>/pdf"
```

Delete a resume item:

```bash
curl -sS -X DELETE "$API/resume/<RESUME_ID>"
```

2) Generate portfolio “showcase” artifacts (stored summaries)

Generate (and optionally persist) top-ranked portfolio summaries:

```bash
curl -sS -X POST "$API/portfolio/generate" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id":"<PORTFOLIO_ID>","limit":5,"persist":true}'
```

List previously generated portfolio showcase artifacts:

```bash
curl -sS "$API/portfolio/<PORTFOLIO_ID>/generated?limit=50"
```

Delete a portfolio showcase artifact:

```bash
curl -sS -X DELETE "$API/portfolio/showcases/<SHOWCASE_ID>"
```

## User configuration settings

Read config:

```bash
curl -sS "$API/users/<USER_ID>/config"
```

Replace config (PUT):

```bash
curl -sS -X PUT "$API/users/<USER_ID>/config" \
  -H "Content-Type: application/json" \
  -d '{"config":{"identity":{"match_emails":["you@example.com"]}}}'
```

Merge patch config (PATCH):

```bash
curl -sS -X PATCH "$API/users/<USER_ID>/config" \
  -H "Content-Type: application/json" \
  -d '{"identity":{"match_names":["Your Name"]}}'
```
