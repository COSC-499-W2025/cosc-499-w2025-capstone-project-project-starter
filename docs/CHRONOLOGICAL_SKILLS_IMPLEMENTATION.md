# Chronological Skills - Implementation

## What Was Added

### CLI Tool
- **File:** `src/insights/chronological_skills_cli.py`
- **Formats:** Text, JSON, CSV
- **Usage:** `python -m src.insights.chronological_skills_cli`

### API Endpoints
- **File:** `src/api/routers/chronological.py`
- `GET /chronological/skills` - Most recent project
- `GET /chronological/skills/{id}` - By project ID
- `GET /chronological/projects` - All projects

### Helper Scripts
- `./scripts/chronological-skills.sh` - View skills timeline
- `./scripts/kill-port.sh` - Kill process on port
- `./scripts/check-ports.sh` - Check port status

## How It Works

1. Pipeline analyzes files and extracts timestamps
2. Detects skills in each file
3. Creates chronological timeline
4. Stores in database under `global_insights.chronological_skills`

## Data Structure

```json
{
  "file": "src/MainActivity.java",
  "timestamp": "2024-01-15T10:30:00",
  "category": "code",
  "skills": ["Java", "Android"],
  "metadata": {}
}
```

## Testing

```bash
# Run pipeline
./scripts/run-pipeline.sh tests/categorize/demo_projects.zip

# Test CLI
./scripts/chronological-skills.sh

# Test API
./scripts/start-api.sh
curl http://localhost:8000/chronological/skills
```
