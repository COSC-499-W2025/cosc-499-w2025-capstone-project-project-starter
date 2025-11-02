import os, json, glob, numpy as np, torch
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm
import orjson

SHARD_GLOB = "data/shards/weaklabels-*.jsonl"
EMB_DIR = "data/embeds"
MODEL_ID = "microsoft/codebert-base"
BATCH_SIZE = 32
MAX_TOK_LEN = 256
TRUNC_CHARS = 2000  # match training

os.makedirs(EMB_DIR, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tok = AutoTokenizer.from_pretrained(MODEL_ID)
enc = AutoModel.from_pretrained(MODEL_ID).to(device).eval()

def embed_texts(texts):
    texts = [(t or "")[:TRUNC_CHARS] for t in texts]
    with torch.no_grad():
        toks = tok(texts, truncation=True, padding=True, max_length=MAX_TOK_LEN, return_tensors="pt")
        toks = {k: v.to(device) for k, v in toks.items()}
        out = enc(**toks).last_hidden_state[:, 0, :].detach().cpu().numpy()
    return out.astype(np.float32)

def iter_jsonl(path):
    with open(path, "rb") as f:
        for line in f:
            yield orjson.loads(line)

def main():
    with open("artifacts/skills.json") as f:
        skills = json.load(f)
    with open("artifacts/encoder.txt", "w") as f:
        f.write(MODEL_ID)

    for shard_path in sorted(glob.glob(SHARD_GLOB)):
        base = os.path.basename(shard_path).replace("weaklabels-", "").replace(".jsonl", "")
        out_npz = os.path.join(EMB_DIR, f"embed-{base}.npz")
        out_idx = os.path.join(EMB_DIR, f"embed-{base}.index.jsonl")
        if os.path.exists(out_npz) and os.path.exists(out_idx):
            continue

        batch = []
        embs = []
        labels_idx = []
        metas = []

        for ex in iter_jsonl(shard_path):
            batch.append(ex.get("content"))
            labels_idx.append([skills.index(s) for s in ex.get("labels", [])])
            metas.append({"path": ex.get("path"), "ext": ex.get("ext"), "labels": ex.get("labels", [])})
            if len(batch) == BATCH_SIZE:
                embs.append(embed_texts(batch))
                batch = []

        if batch:
            embs.append(embed_texts(batch))

        X = np.vstack(embs) if embs else np.zeros((0, 768), dtype=np.float32)

        # Sanity checks
        assert len(labels_idx) == X.shape[0], f"Label/embedding count mismatch: {len(labels_idx)} vs {X.shape[0]}"
        assert len(metas) == X.shape[0], f"Meta/embedding count mismatch: {len(metas)} vs {X.shape[0]}"

        # Save: embeddings as float32, ragged labels as object array
        np.savez_compressed(out_npz, X=X, y=np.array(labels_idx, dtype=object))
        with open(out_idx, "w", encoding="utf-8") as f:
            for m in metas:
                f.write(json.dumps(m) + "\n")

if __name__ == "__main__":
    main()
