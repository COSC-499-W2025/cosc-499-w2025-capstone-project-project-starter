# Quick Commands

## Setup (One Time)
```bash
chmod +x scripts/*.sh
docker compose build backend
```

## Common Commands
```bash
# Run pipeline
./scripts/run-pipeline.sh tests/categorize/demo_projects.zip

# View chronological skills
./scripts/chronological-skills.sh

# Export to JSON
./scripts/chronological-skills.sh --format json --output skills.json

# List projects
./scripts/list-projects.sh

# Start API
./scripts/start-api.sh
```

## API Endpoints
```bash
curl http://localhost:8000/chronological/skills
curl http://localhost:8000/chronological/projects
curl http://localhost:8000/projects
```

**API Docs:** http://localhost:8000/docs

## Troubleshooting
```bash
# Docker not running
open -a Docker

# Port in use
./scripts/kill-port.sh 8000

# Check ports
./scripts/check-ports.sh
```
