# System Demo Walkthrough (≈10 minutes)

End-to-end checklist to demo the pipeline: install, run without LLM, run with LLM, retrieve both runs, and clean up. All commands are copy/paste ready from repo root.

## 0) Install & prerequisites

- Ensure Docker is running.
- Build and start backend once:
  ```bash
  docker compose build backend
  docker compose up -d backend
  ```
- Default DB path is `data/app.db`; insights are stored in grouped tables (`ingest`, `projects`/`project_info`, `files`/`file_info`, `portfolio_insights`, `resume_bullets`, `ranking`, `chronology`) and reconstructed on read. `ProjectInsightsStore.load_zip_report()` can rebuild a full report payload. `INSIGHTS_ENCRYPTION_KEY` applies only to legacy blobs and is not used for new rows.
- Data access consent is prompted once per user/ZIP and stored (like LLM consent). If the user declines, the pipeline exits immediately with no output on subsequent runs too.

## 1) Consent + baseline run (no LLM)

This run satisfies: consent prompt, zip parsing, wrong-format guard, alternative (local-only) analysis, config storage, project/type detection, metrics, skills, ranking, timeline, DB persistence.

1. **Try wrong format (expect error)**

   ```bash
   docker compose run --rm backend python -m src.pipeline.orchestrator README.md
   ```

   - Confirms requirement #3 (non-zip rejected).
   - First prompt: **Data access consent** (answer once; stored).
   - When prompted for LLM consent, answer **n** (requirements #1, #4, #5).
   - User consent choice is stored in user config for reuse (#6).

2. **Run proper ZIP, decline LLM (local-only analysis)**

   ```bash
   docker compose run --rm backend python -m src.pipeline.orchestrator tests/categorize/demo_projects.zip
   ```

   - The run will: parse the ZIP (#2), separate projects (#7), detect languages/frameworks (#8), compute contributions (git) (#9), extract metrics (#10), extract skills (#11), output per-project info (#12), rank projects (#16), summarize top ranked (#17), build chronological projects/skills (#19, #20), and persist to DB (#13).

## 2) Second run with LLM enabled (stored consent for user `root`)

Pre-store LLM consent for user `root`, then run with that user so the prompt is skipped and consent is reused.

```bash
# Store consent = yes for user root (pointing at a different ZIP to get a new hash)
docker compose run --rm backend python -m src.config.config_manager --user-id root --update --zip-file tests/categorize/demo_project_2.zip --llm-consent yes

# Run pipeline using stored consent
docker compose run --rm backend python -m src.pipeline.orchestrator --user-id root tests/categorize/demo_projects_2.zip
```

- This uses stored consent (requirements #1, #4, #5) and persists a second set of insights (different `zip_hash` unless contents unchanged) including portfolio/resume items.

## 3) List stored runs (zip hashes and project names)

```bash
docker compose run --rm -T backend python - <<'PY'
from pathlib import Path
from src.insights.storage import ProjectInsightsStore

store = ProjectInsightsStore(db_path="data/app.db")
for row in store.list_recent_zipfiles(limit=20):
    name = Path(row["zip_path"]).name
    print(f"{row['zip_hash']}  {name}  projects={row['total_projects']}")
PY
```

## 4) Retrieve non-LLM run

**Quick-grab commands (non-LLM run):**

- Portfolio only:

  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=2)[-1]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  print(json.dumps(payload.get("portfolio_item"), indent=2, sort_keys=True))
  PY
  ```

  - retrieve previously generated portfolio information (#14)

- Resume bullets only:

  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=2)[-1]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  print(json.dumps(payload.get("resume_item", {}).get("bullets", []), indent=2, sort_keys=True))
  PY
  ```

  - retrieve previously generated résumé item (#15)

- Advanced skills extraction + chronological timeline (global insights):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=2)[-1]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  extras = payload.get("global_insights", {})
  skill_analysis = payload.get("analysis_results", {}).get("code", {}).get("skill_analysis", {})
  print(json.dumps({"advanced_skill_analysis": skill_analysis, "chronological_skills": extras.get("chronological_skills")}, indent=2, sort_keys=True))
  PY
  ```
- Project ranking & summaries (global insights):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=2)[-1]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  ranking = payload.get("global_insights", {}).get("project_ranking")
  print(json.dumps(ranking, indent=2, sort_keys=True))
  PY
  ```
- Whole analysis payload (everything stored for that project):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=2)[-1]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  print(json.dumps(payload, indent=2, sort_keys=True))
  PY
  ```

- Whole report payload for the zip (grouped tables only):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=2)[-1]["zip_hash"]
  report = s.load_zip_report(zh)
  print(json.dumps(report, indent=2, sort_keys=True))
  PY
  ```

## 5) Retrieve LLM run

**Quick-grab commands (LLM run):**

- Portfolio only:
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=1)[0]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  print(json.dumps(payload.get("portfolio_item"), indent=2, sort_keys=True))
  PY
  ```
- Resume bullets only:
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=1)[0]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  print(json.dumps(payload.get("resume_item", {}).get("bullets", []), indent=2, sort_keys=True))
  PY
  ```
- Advanced skills extraction + chronological timeline (global insights):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=1)[0]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  extras = payload.get("global_insights", {})
  skill_analysis = payload.get("analysis_results", {}).get("code", {}).get("skill_analysis", {})
  print(json.dumps({"advanced_skill_analysis": skill_analysis, "chronological_skills": extras.get("chronological_skills")}, indent=2, sort_keys=True))
  PY
  ```
- Project ranking & summaries (global insights):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=1)[0]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  ranking = payload.get("global_insights", {}).get("project_ranking")
  print(json.dumps(ranking, indent=2, sort_keys=True))
  PY
  ```
- Whole analysis payload (everything stored for that project):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  import json
  s = ProjectInsightsStore(db_path="data/app.db")
  zh = s.list_recent_zipfiles(limit=1)[0]["zip_hash"]
  proj = [p for p in s.list_projects_for_zip(zh) if p != "_misc_files"][0]
  payload = s.load_project_insight(zh, proj)
  print(json.dumps(payload, indent=2, sort_keys=True))
  PY
  ```

## 6) Retrieve via example CLI (full report, grouped read)

```bash
docker compose run --rm backend python -m src.insights.example_retrieval --db-path data/app.db
```

- Shows per-project outputs (#12), ranking (#16), top summaries (#17), timelines (#19, #20).
- Portfolio/resume items are loaded from grouped tables (`portfolio_insights`, `resume_bullets`).
- For a more readable, report-like view in the terminal, pipe through `less`:
  ```bash
  docker compose run --rm backend python -m src.insights.example_retrieval --db-path data/app.db | less -R
  ```
  (`-R` preserves simple formatting/indentation; use `q` to quit the pager.)

## 7) Delete insights safely

Choose either per-zip or all. Deleting a zip only removes that run; other runs remain (requirement #18 about not affecting shared files across reports).

- **Delete one run by zip_hash** (replace `<PUT_HASH_HERE>` with a hash from section 3's command used to list stored runs):
  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  store = ProjectInsightsStore(db_path="data/app.db")
  target = "<PUT_HASH_HERE>"
  print(store.delete_zip(target))
  PY
  ```
- **Delete all insights**:

  ```bash
  docker compose run --rm -T backend python - <<'PY'
  from src.insights.storage import ProjectInsightsStore
  store = ProjectInsightsStore(db_path="data/app.db")
  print(store.delete_all())
  PY
  ```

- **Delete all user configs**:
  ```bash
  docker compose run --rm -T backend python -c "import sqlite3,sys; db='data/app.db';
  conn=sqlite3.connect(db); conn.execute(\"DELETE FROM user_configurations\"); conn.commit();
  print('Deleted rows:', conn.execute('select changes()').fetchone()[0])"
  ```

## 8) Run all tests

```
docker compose run --rm backend pytest -q
```

## 9) Quick notes for the recording

- Total time should stay under 10 minutes if you follow the order above.
- Call out that data access consent is stored per user/ZIP; saying **n** stops the pipeline immediately.
- Highlight prompts for consent (LLM) and the fallback local analysis when declined.
- Show the wrong-format error step to prove validation.
- Point out collaborative vs individual (git contributor counts) and language/framework detection in pipeline output.
- Mention that portfolio and resume items, metrics, rankings, timelines, and skills are persisted and can be retrieved later.
