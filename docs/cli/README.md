# CLI Usage (`src/main.py`)

The repository includes a CLI wrapper for common API workflows.

## Basic Usage
```bash
python src/main.py --api-url http://localhost:5001 <command> [subcommand] [options]
```

State file default:
- `.artifactminer_state.json`

## Common Commands
Health:
```bash
python src/main.py health
```

Create data access consent:
```bash
python src/main.py consent data_access true
```

Upload zip and wait for parser/local ML:
```bash
python src/main.py upload tests/data/code_collab_proj_v1.zip --wait
```

List projects:
```bash
python src/main.py projects list --user-id <USER_ID>
```

Generate resume and save PDF:
```bash
python src/main.py resume generate <PROJECT_ID>
python src/main.py resume pdf <RESUME_ID> --output resume.pdf
```

One-command demo flow:
```bash
python src/main.py demo tests/data/code_collab_proj_v1.zip --resume-pdf-out demo_resume.pdf
```

## Coverage
The CLI wraps most major endpoint groups:
- consent
- user config
- identity rules/auto-link
- upload
- snapshot analyses/skills/external
- project list/report/update/contributors
- portfolio get/top/generate/chronological
- resume generate/get/pdf
- safe deletions
- project image upload
