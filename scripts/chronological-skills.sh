#!/bin/bash
# Short command to retrieve chronological skills

docker compose run --rm backend python -m src.insights.chronological_skills_cli "$@"

