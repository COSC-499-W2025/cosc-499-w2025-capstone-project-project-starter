# Test Data for Milestone #2

This folder contains zipped test data files required for Milestone #2.

## Same project – two snapshots (incremental / duplicate handling)

- **code_collab_proj_early.zip** – Snapshot of a collaborative code project at an earlier point in time.
  - Structure: `./code_collab_proj/app/`, `./code_collab_proj/test/`, `./code_collab_proj/doc/`
- **code_collab_proj_late.zip** – Same project at a later point in time with additional/modified files.
  - Use with **POST /api/projects/{id}/merge** to add incremental content; duplicate paths are skipped.

## Multiple projects (individual and collaborative, code and non-code)

- **multi_project.zip** – One zip containing multiple projects for portfolio/resume testing.
  - Structure:
    - `./code_indiv_proj/` – Individual code project
    - `./code_collab_proj/` – Collaborative code project
    - `./text_indiv_proj/` – Non-code (text) project
    - `./image_indiv_proj/` – Image/non-code project

## Regenerating the zip files

From the project root:

```bash
python test-data/build_test_data_zips.py
```

This recreates the zip files from the contents in `test-data/sources/`.
