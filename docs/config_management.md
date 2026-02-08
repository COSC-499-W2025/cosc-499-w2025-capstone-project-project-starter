# Config Management & Consent

This guide shows how to run the pipeline with per-user configuration and toggle LLM consent using the built-in SQLite-backed config manager. The default user id is `root`. Replace `root` with your own user id if needed (in
the document, I am using `testuser` but you can also `root`).

## 0) Rebuild backend image (optional when dependencies change)

```bash
docker compose build backend
docker compose up -d backend
```

## 1) Run pipeline with default consent behavior

If no config exists for your user, you will be prompted once for LLM consent; the choice is stored locally and reused.
The user id being stored for this run is `root`.

```bash
docker-compose run --rm backend python -m src.pipeline.orchestrator tests/categorize/demo_projects.zip
```

## 2) Run pipeline with an explicit user id

Using `--user-id` (or `PIPELINE_USER_ID`) makes consent and the last zip path persist per user.

```bash
docker-compose run --rm backend \
  python -m src.pipeline.orchestrator \
  --user-id testuser \
  tests/categorize/demo_projects.zip
```

## 3) Update stored consent to opt out (LLM disabled)

This sets `llm_consent` to `no` for the given user and zip path.

```bash
docker-compose run --rm backend \
  python -m src.config.config_manager \
  --user-id testuser \
  --update \
  --zip-file tests/categorize/demo_projects.zip \
  --llm-consent no
```

## 4) Run pipeline after opting out

The pipeline will skip the LLM step and use local analyzers only.

```bash
docker-compose run --rm backend \
  python -m src.pipeline.orchestrator \
  --user-id testuser \
  tests/categorize/demo_projects.zip
```

## 5) Update stored consent to opt in (LLM enabled)

Flip `llm_consent` to `yes` so the LLM summarization runs at the end of the pipeline.

```bash
docker-compose run --rm backend \
  python -m src.config.config_manager \
  --user-id testuser \
  --update \
  --zip-file tests/categorize/demo_projects.zip \
  --llm-consent yes
```

## 6) Run pipeline after opting in

The pipeline will include the optional LLM summaries (requires `OPENAI_API_KEY`).

```bash
docker-compose run --rm backend \
  python -m src.pipeline.orchestrator \
  --user-id testuser \
  tests/categorize/demo_projects.zip
```

### Notes

- Consent is stored locally in `data/app.db` via `UserConfigManager`; prompts are skipped once stored. Both LLM consent and data-access consent are persisted per user.
- `--zip-file` updates the last-used zip path for that user but does not move files.
- Use `--llm-consent yes|no` on `--update` to flip your preference without re-prompting.
