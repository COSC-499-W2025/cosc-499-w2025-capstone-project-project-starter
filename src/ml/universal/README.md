# Code-to-Skills Weak Supervision Pipeline

This module builds and trains a weakly supervised multi-label classifier that assigns "skills" (such as Flask, SQL, React) to code snippets from the **BigCode/The Stack** dataset using regex-based labeling functions and CodeBERT embeddings. We use the `the-stack-smol` since the original one is several terabytes and would take ages. 

---

## Requirements

- **Python < 3.14** - DO NOT USE 3.14 IT WILL NOT RUN
- GPU optional but recommended for embedding speed
- Use a venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Order
Run the scripts in the following order:
1. `build_weak_corpus.py` - streams from The Stack to generate a weakly labeled corpus from regex LFs. Produces weaklabels JSONL, skills.json (ordered skill list), regex_lfs.json (LF regexes).
2. `cache_embeddings.py` - embeds each JSONL shard once with CodeBERT and stores features/label indices. Produces embed shards, arrays: X ∈ ℝ[n_i×768] and y = list[list[int]] of label indices, and corresponding metadata per row.
3. `train_classifier.py` - trains a multi-label one-vs-rest logistic regression on cached embeddings and persists it. Consumes the embedded files and skills.json to generate a .joblib model file.
4. `predict.py --file path/to/codefile.py --threshold 0.5` - Classifies new code snippets using the persisted model from the previous step. Prints predictions to stdout.