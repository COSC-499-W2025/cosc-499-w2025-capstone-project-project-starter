# API Documentation (Milestone #2)

The backend is a **FastAPI** application. All endpoints below are prefixed with `/api` unless noted. Base URL examples: `http://localhost:8000/api`, or your deployed origin.

Interactive docs: **GET /docs** (Swagger UI), **GET /redoc** (ReDoc). Schema: **GET /openapi.json**.

---

## Projects

### POST /api/projects/upload

Upload a project as a ZIP file. Enables incremental additions later via merge.

- **Request:** `multipart/form-data` with `file` (ZIP). Optional query: `user_name`.
- **Response (200):** `{ "success": true, "message": "...", "data": { "file_id", "filename", "file_count", "files": [...] } }`
- **Response (400):** Non-ZIP file, or duplicate upload (`error_type: "DUPLICATE_UPLOAD"`, `data.existing_file_id`).

### POST /api/projects/{project_id}/merge

Add another zipped folder for the **same** portfolio/resume project (incremental information). Duplicate file paths are detected and only one copy is kept.

- **Request:** `multipart/form-data` with `file` (ZIP). Optional query: `user_name`.
- **Response (200):** `{ "success": true, "message": "...", "data": { "project_id", "new_files_count", "skipped_duplicates", "new_files", "skipped_files" } }`
- **Response (404):** Project not found or access denied.

### GET /api/projects

List projects. Optional query: `user_name` to filter by user.

- **Response (200):** `{ "success": true, "count": N, "projects": [ { "id", "filename", "created_at", "file_count", "status" } ] }`

### GET /api/projects/{project_id}

Get one project by ID. Optional query: `user_name` for ownership scope.

- **Response (200):** `{ "success": true, "project": { "id", "filename", "filepath", "status", "metadata", "created_at" } }`
- **Response (404):** Project not found.

### POST /api/projects/{project_id}/thumbnail

Associate a **portfolio image** for the project (thumbnail for showcase).

- **Request:** `multipart/form-data` with `file` (image). Optional query: `user_name`.
- **Response (200):** `{ "success": true, ... }`
- **Response (400):** Not an image or empty file. **Response (404):** Project not found.

### GET /api/projects/{project_id}/thumbnail

Get the project thumbnail (e.g. as data URL).

- **Response (200):** `{ "success": true, "has_thumbnail": true, "thumbnail_data": "data:image/..." }` or `{ "has_thumbnail": false }`
- **Response (404):** Project not found.

---

## Privacy consent

### POST /api/privacy-consent

Store user privacy consent.

- **Request (JSON):** `{ "consent_given": boolean, "user_name": string (optional) }`
- **Response (200):** `{ "success": true, "message": "...", "consent_given", "user_name", "consent_status" }`
- **Response (400):** No user_name and no logged-in user. **Response (500):** Storage failure.

---

## Skills

### GET /api/skills

Get skills extracted from the user’s projects (e.g. from generated resume data).

- **Query:** `user_name` (optional).
- **Response (200):** `{ "success": true, "skills": [], "categorized_skills": {}, "languages": [], "frameworks": [] }`

---

## Resume

### GET /api/resume/{user_id}

Get the user’s stored resume.

- **Response (200):** `{ "success": true, "resume": { ... } }`
- **Response (404):** Resume not found.

### POST /api/resume/generate

Generate a new resume (project selection, skills, etc.). User can choose which information is represented (e.g. projects selected for resume).

- **Query:** `user_name` (required).
- **Request (JSON):** `{ "top_projects_count": number, "selected_project_ids": [number], "include_skills": boolean, "skills_mode": string }`
- **Response (200):** `{ "success": true, "resume": { ... } }`
- **Response (400):** Missing user_name or generation failed (e.g. no projects).

### POST /api/resume/{user_id}/edit

Customize and save the **wording** of a project used for a résumé item.

- **Request (JSON):** `{ "project_id": number, "wording": string }`
- **Response (200):** `{ "success": true, "message": "Resume updated" }`
- **Response (500):** Update failed.

### Display as résumé item

- **GET /api/resume/preview/{project_id}** – Returns one project formatted as a **résumé item** (textual bullets, role, technologies). Use for preview or “edit wording” flows.

---

## Portfolio

### GET /api/portfolio/{user_id}

Get the user’s portfolio (showcase projects, customizations). Optional query: `top_n`.

- **Response (200):** `{ "success": true, "portfolio": { "projects", "user_name", ... } }`
- **Response (404):** No portfolio / error (e.g. no projects).

### POST /api/portfolio/generate

Generate portfolio data for the user.

- **Query:** `user_name` (required).
- **Request (JSON):** `{ "top_n": number (optional) }`
- **Response (200):** `{ "success": true, "portfolio": { ... } }`
- **Response (400):** Missing user_name or generation error.

### POST /api/portfolio/{user_id}/edit

**Customize and save** information about a **portfolio showcase project** (title, description, key role).

- **Request (JSON):** `{ "project_id": number, "custom_title": string, "custom_description": string, "custom_role": string }`
- **Response (200):** `{ "success": true, "message": "...", "customization": { "project_id", "custom_title", "custom_description", "custom_role" } }`
- **Response (500):** Save failed.

### Display as portfolio showcase

- **GET /api/portfolio/card/{project_id}** – Returns one project as a **portfolio showcase** card (textual info, role, success metrics, image_url if thumbnail set). Use for portfolio display.

### Portfolio custom data (per-project)

- **POST /api/portfolio/{user_id}/custom-data** – Save/update customization (same fields as edit).
- **GET /api/portfolio/{user_id}/custom-data** – List project IDs with customizations.
- **GET /api/portfolio/{user_id}/custom-data/{project_id}** – Get one customization.
- **DELETE /api/portfolio/{user_id}/custom-data/{project_id}** – Clear customization.

---

## Human-in-the-loop features (summary)

| Requirement | How it’s supported |
|-------------|--------------------|
| Incremental information (same project, later zip) | **POST /api/projects/upload** then **POST /api/projects/{id}/merge** with a second ZIP. |
| Duplicate files kept once | Merge skips existing paths; upload rejects identical ZIP content (DUPLICATE_UPLOAD). |
| User chooses what’s represented | **POST /api/resume/generate** with `selected_project_ids` / `top_projects_count`; ranking endpoints; **POST /api/portfolio/{user_id}/edit** and custom-data. |
| Key role in project | **Portfolio:** `custom_role` in **POST /api/portfolio/{user_id}/edit** and custom-data; **Resume:** role in resume item and custom wording. |
| Evidence of success | Portfolio card includes `success_metrics` (from analysis); evidence extractor builds metrics/feedback. |
| Portfolio image per project | **POST /api/projects/{id}/thumbnail**, **GET /api/projects/{id}/thumbnail**; card uses as `image_url`. |
| Customize/save portfolio showcase | **POST /api/portfolio/{user_id}/edit** and **POST /api/portfolio/{user_id}/custom-data**. |
| Customize/save resume wording | **POST /api/resume/{user_id}/edit** and **POST /api/resume/{user_id}/custom-wording**. |
| Display project as portfolio | **GET /api/portfolio/card/{project_id}**. |
| Display project as résumé item | **GET /api/resume/preview/{project_id}**. |

---

## Required vs extra APIs

**Milestone #2 required (11 endpoints) – all implemented:**

| Required | Implemented path |
|---------|------------------|
| POST /projects/upload | **POST /api/projects/upload** |
| POST /privacy-consent | **POST /api/privacy-consent** |
| GET /projects | **GET /api/projects** |
| GET /projects/{id} | **GET /api/projects/{project_id}** |
| GET /skills | **GET /api/skills** |
| GET /resume/{id} | **GET /api/resume/{user_id}** |
| POST /resume/generate | **POST /api/resume/generate** |
| POST /resume/{id}/edit | **POST /api/resume/{user_id}/edit** |
| GET /portfolio/{id} | **GET /api/portfolio/{user_id}** |
| POST /portfolio/generate | **POST /api/portfolio/generate** |
| POST /portfolio/{id}/edit | **POST /api/portfolio/{user_id}/edit** |

**Extra APIs (not in the milestone requirements):**

- **Resume/portfolio display & customization**
  - GET /api/resume/preview/{project_id} – one project as résumé item text
  - GET /api/portfolio/card/{project_id} – one project as portfolio card text
  - GET /api/resume/{user_id}/custom-wording – list projects with custom wording
  - POST /api/resume/{user_id}/custom-wording – save custom wording (alternate to /edit body)
  - DELETE /api/resume/{user_id}/custom-wording/{project_id} – clear custom wording
  - DELETE /api/resume/{user_id} – delete user’s resume
  - POST /api/portfolio/{user_id}/custom-data – save portfolio customization (same as edit)
  - GET /api/portfolio/{user_id}/custom-data – list customized project IDs
  - GET /api/portfolio/{user_id}/custom-data/{project_id} – get one customization
  - DELETE /api/portfolio/{user_id}/custom-data/{project_id} – clear customization
- **Projects (incremental, thumbnails, analysis, ranking)**
  - POST /api/projects/{project_id}/merge – add zip to same project (incremental)
  - POST /api/projects/{project_id}/thumbnail – upload portfolio image
  - GET /api/projects/{project_id}/thumbnail – get thumbnail
  - POST /api/projects/{project_id}/analyze – local analysis
  - POST /api/projects/{project_id}/analyze-gemini – Gemini analysis
  - POST /api/projects/{project_id}/quick-summary – quick AI summary
  - POST /api/projects/rank, /api/projects/rank-top3, /api/projects/rank-gemini – ranking
  - GET /api/projects/rankings – stored rankings
  - DELETE /api/projects/{project_id}/data – delete project data
  - POST /api/preferences – user preferences (e.g. git username)
- **Health, auth, settings**
  - GET /api/health, GET /api/health/db – health checks
  - POST /api/auth/login, /register, /logout – auth
  - GET /api/auth/me – current user
  - GET/POST /api/settings, /api/settings/account, /api/settings/privacy, /api/settings/general – unified settings

All API errors return a consistent shape: `{ "success": false, "error_type": "...", "message": "...", "data": ... }` with appropriate HTTP status codes (400, 403, 404, 422, 500).
