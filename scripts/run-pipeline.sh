#!/bin/bash
# Run the analysis pipeline on a ZIP file

if [ -z "$1" ]; then
    echo "Usage: ./scripts/run-pipeline.sh <path-to-zip-file>"
    echo "Example: ./scripts/run-pipeline.sh tests/categorize/demo_projects.zip"
    exit 1
fi

docker compose run --rm backend python -m src.pipeline.orchestrator "$@"

