[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20510252&assignment_repo_type=AssignmentRepo)

# Digital Artifacts & Data Mining Project 

### Team 15
- Rylan Millar - 33334400
- Alex Batke - 34354803
- Cole Powrie - 77174209
- Liam Storgaard - 64584279
- Will Tilden - 61350294
- Luis Wen Luo - 10665891

## Overview

This project focuses on analyzing digital work artifacts such as code and documents from a student or early professional’s computer. The goal is to help users understand the projects they've contributed to over the course of their degrees or professional careers, and build a resume by extracting useful insights like skills learned and contribution levels from a given directory.

For this milestone, the system can parse a zipped folder, identify project details, extract key metrics, handle permissions and privacy concerns, and output the results in simple text-based formats. This lays the groundwork for future development of an API and a visual dashboard.


## Diagrams
- [Level 1 data flow diagram](/docs/data%20flow%20diagram/explanation.md)
- [System architecture design](/docs/system%20architecture%20design/explanation.md)


## Running with Docker (API + DB + analysis worker)

This repository ships with a Docker Compose stack for Postgres + migrations + the FastAPI service, plus an optional analysis worker and Ollama.

### Prerequisites
- Docker Engine + Docker Compose v2

### Important info
Service URLs

API base URL: http://localhost:5001

Postgres: postgresql://postgres:postgres@localhost:5432/artifactminer

### Start the core stack (db + migrate + api)
This brings up:
- Postgres on `localhost:5432`
- API on `localhost:5001` (container port 5000)

```bash
docker compose up --build
```

To stop:

```bash
docker compose down
```
To wipe all data (destructive):
```bash
docker compose down -v
```

### Starting the analysis worker (and Ollama)
The worker and Ollama are behind Compose profiles:
- ollama is in profiles external and analysis
- worker is in profile analysis

Run everything (api + db + worker + ollama):
```
docker compose --profile analysis up --build
```


## Testing

```
pip install python-multipart fastapi alembic pypdf
```
If the test database has not been created before:

```bash
export DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/artifactminer_test'
psql 'postgresql://postgres:postgres@localhost:5432/postgres' -c 'CREATE DATABASE artifactminer_test;' || true
alembic upgrade head
```

Then, to test, run from the project root:

```
PYTHONPATH=. pytest
```
