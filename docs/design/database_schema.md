# User Configuration Database Schema

## Overview
The `UserConfigManager` located in `src/config/config_manager.py` stores CLI-submitted upload information and consent flags in a local SQLite database. The database path is fixed to `sqlite:///data/app.db` (resolved to `data/app.db`). All user-facing helpers (`create_config`, `update_config`, `load_config`, and `save_config_to_db`) go through this schema, so keeping it well documented ensures consistent persistence logic across the project. Tests may override the path by passing `db_path` directly to `UserConfigManager`.

## Table Definition
The schema is initialized on demand via `UserConfigManager.init_db()`. It creates a single normalized table named `user_configurations`.

```sql
CREATE TABLE IF NOT EXISTS user_configurations (
    user_id TEXT PRIMARY KEY,
    zip_file TEXT NOT NULL,
    llm_consent INTEGER NOT NULL,
    llm_consent_asked INTEGER NOT NULL DEFAULT 0,
    data_access_consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
```

### Column Details
| Column      | Type   | Nullable | Constraints / Semantics |
|-------------|--------|----------|-------------------------|
| `user_id`   | `TEXT` | No       | Serves as the primary key; maps 1:1 to the CLI `--user-id` argument. |
| `zip_file`  | `TEXT` | No       | Absolute or relative path to the uploaded ZIP archive for the user. |
| `llm_consent` | `INTEGER` | No | Stores `1` for consent and `0` otherwise. The manager converts Python booleans to ints when persisting and back to booleans when loading. |
| `llm_consent_asked` | `INTEGER` | No | Tracks whether LLM consent has been collected (1) or not (0) so we only prompt once. |
| `data_access_consent` | `INTEGER` | No | Stores `1` for data-access consent and `0` otherwise; we prompt once and reuse. |
| `created_at` | `TEXT` | No | ISO-8601 timestamp (`datetime.now(timezone.utc).isoformat()`) recorded once at creation. |
| `updated_at` | `TEXT` | Yes | ISO-8601 timestamp captured whenever `update_config` runs; remains `NULL` until the first update. |

### Additional Notes
- There are no foreign keys because the table is the authoritative source for user configuration metadata.
- `user_id` uniqueness means multiple uploads for the same user overwrite the existing record instead of creating duplicates.
- The schema purposefully stores timestamps as text to avoid SQLite time zone ambiguity while keeping them human readable.

## Data Lifecycle & Access Patterns
1. **Creation** – `create_config` ensures the user ID does not already exist, assigns a `created_at` timestamp, and persists the initial record.
2. **Updates** – `update_config` patches provided fields, leaves unspecified columns untouched, and stamps `updated_at` with the current UTC timestamp.
3. **Upserts** – `_persist_config` is shared by create/update paths and uses `INSERT ... ON CONFLICT(user_id) DO UPDATE` to guarantee idempotent writes.
4. **Reads** – `load_config` queries a single row by `user_id`, casting the `llm_consent` integer back into a boolean before returning a `UserConfig` dataclass instance.

## Example Record
```json
{
  "user_id": "sample-user",
  "zip_file": "/uploads/sample-user/data.zip",
  "llm_consent": true,
  "created_at": "2024-08-01T12:34:56.123456+00:00",
  "updated_at": "2024-08-15T09:20:10.654321+00:00"
}
```

This document should be kept up to date whenever the `user_configurations` table changes so other teams (data ingestion, privacy/compliance, etc.) can rely on a single description of the persisted state.

---

# Grouped Insights Storage Schema (Implemented)

## Overview
This replaces the encrypted `zipfile` blob storage with grouped tables for ingest, projects, files, and presentation insights. The goal is to keep all analysis output queryable while supporting future upgrades (incremental ingest, file de-duplication, presentation customization) without reworking storage again. This schema is implemented in `src/insights/storage.py` migrations (schema version 5) and used by pipeline persistence + retrieval.

## Schema Migrations
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
```

## Ingest (replaces `zipfile`)
```sql
CREATE TABLE IF NOT EXISTS ingest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL CHECK (source_type IN ('zip', 'dir')),
    source_path TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    file_count INTEGER NOT NULL DEFAULT 0,
    total_uncompressed_bytes INTEGER NOT NULL DEFAULT 0,
    total_compressed_bytes INTEGER NOT NULL DEFAULT 0,
    run_type TEXT NOT NULL CHECK (run_type IN ('full', 'incremental')),
    parent_run_id INTEGER,
    pipeline_version TEXT,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('running', 'completed', 'failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(parent_run_id) REFERENCES ingest(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_ingest_source_hash ON ingest(source_hash);
CREATE INDEX IF NOT EXISTS idx_ingest_source_run ON ingest(source_hash, id);
```

## Projects & Project Info
```sql
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_hash TEXT NOT NULL,
    project_key TEXT NOT NULL,
    project_name TEXT NOT NULL,
    slug TEXT NOT NULL,
    root_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source_hash, project_key)
);
CREATE INDEX IF NOT EXISTS idx_projects_source ON projects(source_hash);

CREATE TABLE IF NOT EXISTS project_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    ingest_id INTEGER NOT NULL,
    project_path TEXT,
    is_git_repo INTEGER NOT NULL DEFAULT 0,
    total_files INTEGER NOT NULL DEFAULT 0,
    total_lines INTEGER NOT NULL DEFAULT 0,
    total_commits INTEGER NOT NULL DEFAULT 0,
    total_contributors INTEGER NOT NULL DEFAULT 0,
    activity_code INTEGER NOT NULL DEFAULT 0,
    activity_test INTEGER NOT NULL DEFAULT 0,
    activity_doc INTEGER NOT NULL DEFAULT 0,
    duration_start TEXT,
    duration_end TEXT,
    duration_days INTEGER NOT NULL DEFAULT 0,
    doc_files INTEGER NOT NULL DEFAULT 0,
    doc_words INTEGER NOT NULL DEFAULT 0,
    image_files INTEGER NOT NULL DEFAULT 0,
    video_files INTEGER NOT NULL DEFAULT 0,
    test_files INTEGER NOT NULL DEFAULT 0,
    has_documentation INTEGER NOT NULL DEFAULT 0 CHECK (has_documentation IN (0, 1)),
    has_tests INTEGER NOT NULL DEFAULT 0 CHECK (has_tests IN (0, 1)),
    has_images INTEGER NOT NULL DEFAULT 0 CHECK (has_images IN (0, 1)),
    has_videos INTEGER NOT NULL DEFAULT 0 CHECK (has_videos IN (0, 1)),
    languages_json TEXT,
    frameworks_json TEXT,
    skills_json TEXT,
    keyword_tags_json TEXT,
    contributors_json TEXT,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(ingest_id) REFERENCES ingest(id) ON DELETE CASCADE,
    UNIQUE(project_id, ingest_id)
);
CREATE INDEX IF NOT EXISTS idx_project_info_ingest ON project_info(ingest_id);
```

## Files & File Info
```sql
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    extension TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, relative_path),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS file_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    project_info_id INTEGER NOT NULL,
    content_hash TEXT,
    content_size_bytes INTEGER NOT NULL DEFAULT 0,
    content_mime_type TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    modified_at TEXT,
    is_binary INTEGER NOT NULL DEFAULT 0 CHECK (is_binary IN (0, 1)),
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    language TEXT,
    category TEXT CHECK (category IN ('code', 'documentation', 'images', 'video', 'other')),
    metrics_json TEXT,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY(project_info_id) REFERENCES project_info(id) ON DELETE CASCADE,
    UNIQUE(file_id, project_info_id)
);
CREATE INDEX IF NOT EXISTS idx_file_info_project ON file_info(project_info_id);
CREATE INDEX IF NOT EXISTS idx_file_info_content ON file_info(content_hash);
```

## Portfolio Insights & Resume Bullets
```sql
CREATE TABLE IF NOT EXISTS portfolio_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_info_id INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    pipeline_version TEXT,
    tagline TEXT,
    description TEXT,
    project_type TEXT,
    complexity TEXT,
    is_collaborative INTEGER NOT NULL DEFAULT 0 CHECK (is_collaborative IN (0, 1)),
    summary TEXT,
    key_features_json TEXT,
    FOREIGN KEY(project_info_id) REFERENCES project_info(id) ON DELETE CASCADE,
    UNIQUE(project_info_id)
);

CREATE TABLE IF NOT EXISTS resume_bullets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_insight_id INTEGER NOT NULL,
    bullet_text TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_selected INTEGER NOT NULL DEFAULT 1 CHECK (is_selected IN (0, 1)),
    source TEXT NOT NULL DEFAULT 'generated' CHECK (source IN ('generated', 'manual')),
    FOREIGN KEY(portfolio_insight_id) REFERENCES portfolio_insights(id) ON DELETE CASCADE,
    UNIQUE(portfolio_insight_id, display_order)
);
```

## Tags & Skill Evidence
```sql
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_type TEXT NOT NULL CHECK (tag_type IN ('language', 'framework', 'skill', 'design_pattern', 'keyword', 'tool')),
    name TEXT NOT NULL,
    category TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(tag_type, name)
);

CREATE TABLE IF NOT EXISTS skill_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_info_id INTEGER NOT NULL,
    file_info_id INTEGER,
    tag_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL,
    location TEXT,
    reasoning TEXT,
    confidence REAL,
    FOREIGN KEY(project_info_id) REFERENCES project_info(id) ON DELETE CASCADE,
    FOREIGN KEY(file_info_id) REFERENCES file_info(id) ON DELETE SET NULL,
    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE RESTRICT
);
```

## Ranking & Chronology (global insights)
```sql
CREATE TABLE IF NOT EXISTS ranking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingest_id INTEGER NOT NULL,
    criteria TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ranking_json TEXT NOT NULL,
    FOREIGN KEY(ingest_id) REFERENCES ingest(id) ON DELETE CASCADE,
    UNIQUE(ingest_id)
);

CREATE TABLE IF NOT EXISTS chronology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingest_id INTEGER NOT NULL,
    chronology_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(ingest_id) REFERENCES ingest(id) ON DELETE CASCADE,
    UNIQUE(ingest_id)
);
```

## Thumbnails, Presentation, Profile
```sql
CREATE TABLE IF NOT EXISTS thumbnails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_info_id INTEGER,
    file_info_id INTEGER,
    role TEXT NOT NULL CHECK (role IN ('project', 'portfolio', 'resume', 'file')),
    image_path TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    mime_type TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_info_id) REFERENCES project_info(id) ON DELETE CASCADE,
    FOREIGN KEY(file_info_id) REFERENCES file_info(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS presentation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    profile_type TEXT NOT NULL CHECK (profile_type IN ('portfolio', 'resume')),
    profile_name TEXT NOT NULL,
    controls_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user_configurations(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presentation_id INTEGER NOT NULL,
    selections_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(presentation_id) REFERENCES presentation(id) ON DELETE CASCADE
);
```

## Deletion Audit & Legacy Zipfile
```sql
CREATE TABLE IF NOT EXISTS deletion_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    scope TEXT NOT NULL,
    details TEXT,
    deleted_projects INTEGER NOT NULL DEFAULT 0,
    deleted_zips INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
```

The legacy `zipfile` table (encrypted blobs) remains for backward compatibility; new codepaths do not write to it.

## Field Mapping (current analysis output -> grouped storage)
| Analysis Output | Source Fields | Tables / Columns | Notes (FKs) |
| --- | --- | --- | --- |
| ZIP metadata | `zip_metadata.*` | `ingest.file_count`, `ingest.total_uncompressed_bytes`, `ingest.total_compressed_bytes` | `ingest.source_hash` groups runs |
| Project identity | `project_name`, `project_path`, `is_git_repo` | `projects.project_name`, `projects.project_key`, `project_info.project_path`, `project_info.is_git_repo` | `project_info.project_id -> projects.id` |
| File inventory | `categorized_contents.*` | `files.relative_path`, `file_info.category`, `file_info.language` | `file_info.project_info_id -> project_info.id` |
| File content hashes | `file_info[].sha256`, `file_info[].size` | `file_info.content_hash`, `file_info.content_size_bytes` | indexed for future dedupe |
| Code metrics | `analysis_results.code.metrics.*` | `project_info.total_files`, `project_info.total_lines`, `project_info.test_files` | stored per run |
| Git metrics & duration | `git_analysis.*` | `project_info.total_commits`, `project_info.total_contributors`, `project_info.duration_*`, `project_info.activity_*` | contributors in JSON |
| Contributors | `git_analysis.contributors[]` | `project_info.contributors_json` | stored as JSON array |
| Portfolio item core | `portfolio_item.tagline/description/project_type/complexity` | `portfolio_insights.*` | `portfolio_insights.project_info_id -> project_info.id` |
| Portfolio key features | `portfolio_item.key_features[]` | `portfolio_insights.key_features_json` | JSON list |
| Resume bullets | `resume_item.bullets[]` | `resume_bullets.*` | `resume_bullets.portfolio_insight_id -> portfolio_insights.id` |
| Languages/frameworks/skills | `project_metrics.languages/frameworks/skills` | `project_info.languages_json/frameworks_json/skills_json` + `tags` | catalog kept in `tags` |
| Skill evidence | `analysis_results.code.skill_analysis.evidence[]` | `skill_evidence.*` | `skill_evidence.file_info_id -> file_info.id` |
| Keywords | `text_analyzer.top_keywords` | `project_info.keyword_tags_json` + `tags` | keyword tags stored in JSON |
| Text/image/video metrics | `text_analyzer` / `image_analyzer` / `video_analyzer` | `file_info.metrics_json` | metrics stored as JSON list |
| Ranking & summaries | `project_ranking` | `ranking.ranking_json` | stored as one JSON blob per ingest |
| Chronological timeline | `chronological_skills` | `chronology.chronology_json` | stored as one JSON blob per ingest |
| Thumbnails | image selection for UI | `thumbnails.*` | `thumbnails.project_info_id -> project_info.id` |
| Portfolio/resume ordering & overrides | user profile selections | `presentation.controls_json`, `profile.selections_json` | supports selection, ordering, overrides |

This schema keeps the pipeline output queryable without storing opaque blobs, while preserving a clear path for incremental ingestion, file dedupe, and per-profile presentation customization.
