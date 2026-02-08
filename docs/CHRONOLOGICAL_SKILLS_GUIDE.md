# Chronological Skills Guide

Shows when each skill was used, ordered by date.

## CLI Usage

```bash
# Text format
./scripts/chronological-skills.sh

# JSON
./scripts/chronological-skills.sh --format json

# CSV
./scripts/chronological-skills.sh --format csv --output skills.csv

# Specific project
./scripts/chronological-skills.sh --project "project-name"
```

## API Usage

```bash
# Start API
./scripts/start-api.sh

# Get skills timeline
curl http://localhost:8000/chronological/skills
curl http://localhost:8000/chronological/skills/1
curl http://localhost:8000/chronological/projects
```

**Interactive Docs:** http://localhost:8000/docs

## Response Format

```json
{
  "total_events": 42,
  "timeline": [
    {
      "file": "MainActivity.java",
      "timestamp": "2024-01-15T10:30:00",
      "category": "code",
      "skills": ["Java", "Android"]
    }
  ]
}
```

## Troubleshooting

**No data:** Run pipeline first
```bash
./scripts/run-pipeline.sh tests/categorize/demo_projects.zip
```

**Docker not running:**
```bash
open -a Docker
```
