import json, numpy as np, torch, argparse
from transformers import AutoTokenizer, AutoModel
import joblib

ARTI_DIR = "artifacts"
MODEL_PATH = "models/ovr_logreg.joblib"
TRUNC_CHARS = 2000
MAX_TOK_LEN = 256

def load_encoder():
    with open(f"{ARTI_DIR}/encoder.txt") as f:
        model_id = f.read().strip()
    tok = AutoTokenizer.from_pretrained(model_id)
    enc = AutoModel.from_pretrained(model_id).eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    enc.to(device)
    return tok, enc, device

def embed_texts(texts, tok, enc, device):
    texts = [(t or "")[:TRUNC_CHARS] for t in texts]
    with torch.no_grad():
        toks = tok(texts, truncation=True, padding=True, max_length=MAX_TOK_LEN, return_tensors="pt")
        toks = {k: v.to(device) for k, v in toks.items()}
        out = enc(**toks).last_hidden_state[:, 0, :].detach().cpu().numpy()
    return out.astype(np.float32)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to a code file to classify")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    with open(f"{ARTI_DIR}/label_binarizer.json") as f:
        skills = json.load(f)["classes"]

    tok, enc, device = load_encoder()
    X = embed_texts([text], tok, enc, device)

    clf = joblib.load(MODEL_PATH)
    probs = clf.predict_proba(X)[0]

    preds = [(skills[i], float(probs[i])) for i in range(len(skills)) if probs[i] >= args.threshold]
    preds.sort(key=lambda x: x[1], reverse=True)

    print(json.dumps({"predictions": preds}, indent=2))

if __name__ == "__main__":
    main()
