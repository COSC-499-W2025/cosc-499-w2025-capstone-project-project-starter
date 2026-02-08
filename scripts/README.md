# Quick Command Scripts

Short, easy-to-use commands for common operations.

## Setup

Make scripts executable:
```bash
chmod +x scripts/*.sh
```

## Available Scripts

### Pipeline Operations

**Run Analysis Pipeline**
```bash
./scripts/run-pipeline.sh tests/categorize/demo_projects.zip
```

### Retrieval Operations

**Get Chronological Skills (Text)**
```bash
./scripts/chronological-skills.sh
```

**Get Chronological Skills (JSON)**
```bash
./scripts/chronological-skills.sh --format json
```

**Get Chronological Skills (CSV)**
```bash
./scripts/chronological-skills.sh --format csv --output skills.csv
```

**List All Projects**
```bash
./scripts/list-projects.sh
```

**View Project Insights**
```bash
./scripts/view-project.sh
```

### API Operations

**Start API Server**
```bash
./scripts/start-api.sh
```

**Test API Health**
```bash
curl http://localhost:8000/health
```

### Troubleshooting

**Check What's Running on Ports**
```bash
./scripts/check-ports.sh
```

**Kill Process on Specific Port**
```bash
./scripts/kill-port.sh 8000
```

**Kill Process on Default API Port (8000)**
```bash
./scripts/kill-port.sh
```

## Docker Commands (if scripts don't work)

All scripts are wrappers around Docker commands. You can run them directly:

```bash
# Chronological skills
docker compose run --rm backend python -m src.insights.chronological_skills_cli

# With options
docker compose run --rm backend python -m src.insights.chronological_skills_cli --format json
docker compose run --rm backend python -m src.insights.chronological_skills_cli --format csv --output skills.csv
```

