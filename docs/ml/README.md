# ML Pipeline Notes

This project includes a local weakly-supervised skill classifier used by worker `local_ml` analysis.

## Runtime Inference Path
- Worker entrypoint: `src/worker/executors.py::run_local_ml`
- Uses resources in `src/ml/artifacts/` and model file `src/ml/models/ovr_logreg.joblib`.
- Produces per-snapshot skill detections persisted to:
  - `analyses.output_json` (`analysis_type='local_ml'`)
  - `analysis_skills`
  - `skills`

## Tuning Environment Variables
- `LOCAL_ML_THRESHOLD` (default `0.5`)
- `LOCAL_ML_MAX_FILE_CHARS` (default `1000000`)
- `LOCAL_ML_MAX_CHUNKS_TOTAL` (default `5000`)
- `LOCAL_ML_EMBED_BATCH` (default `16`)

## Training/Artifact Scripts
Source scripts are under `src/ml/`:
- `build_weak_corpus.py`
- `cache_embeddings.py`
- `train_classifier.py`
- `predict.py`

Original module-specific README remains at:
- [`src/ml/README.md`](../../src/ml/README.md)

## Expected Output Shape
Local ML analysis stores records like:
- `skill`
- `max_prob`
- `avg_prob`
- `hits`
- `first_seen_ts`
- `examples[]`

These outputs feed:
- `/snapshots/{snapshot_id}/skills`
- `/projects/{project_id}/report`
- chronology and comparison endpoints
- resume/portfolio generation signals
