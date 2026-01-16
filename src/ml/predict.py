import json, numpy as np, torch, argparse, os
from transformers import AutoTokenizer, AutoModel
import joblib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths relative to predict.py
ARTI_DIR = os.path.join(BASE_DIR, "artifacts")
MODEL_PATH = os.path.join(BASE_DIR, "models", "ovr_logreg.joblib")

TRUNC_CHARS = 2000
MAX_TOK_LEN = 256

_tok = None
_enc = None
_device = None
_clf = None
_skills = None


def load_encoder():
    encoder_path = os.path.join(ARTI_DIR, "encoder.txt")
    with open(encoder_path) as f:
        model_id = f.read().strip()
    tok = AutoTokenizer.from_pretrained(model_id)
    enc = AutoModel.from_pretrained(model_id).eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    enc.to(device)
    return tok, enc, device


def embed_texts(texts, tok, enc, device):
    texts = [(t or "")[:TRUNC_CHARS] for t in texts]
    with torch.no_grad():
        toks = tok(
            texts,
            truncation=True,
            padding=True,
            max_length=MAX_TOK_LEN,
            return_tensors="pt",
        )
        toks = {k: v.to(device) for k, v in toks.items()}
        out = enc(**toks).last_hidden_state[:, 0, :].detach().cpu().numpy()
    return out.astype(np.float32)


def _load_resources():
    global _tok, _enc, _device, _clf, _skills

    if _tok is None or _enc is None or _device is None:
        _tok, _enc, _device = load_encoder()

    if _skills is None:
        lb_path = os.path.join(ARTI_DIR, "label_binarizer.json")
        with open(lb_path) as f:
            _skills = json.load(f)["classes"]

    if _clf is None:
        _clf = joblib.load(MODEL_PATH)

def classify_text(text, threshold=0.5):
    """
    Classify a single text string and return a list of (skill, probability)
    pairs with probability >= threshold, sorted by probability descending.
    """
    _load_resources()

    X = embed_texts([text], _tok, _enc, _device)
    probs = _clf.predict_proba(X)[0]

    preds = [
        (_skills[i], float(probs[i]))
        for i in range(len(_skills))
        if probs[i] >= threshold
    ]
    preds.sort(key=lambda x: x[1], reverse=True)
    return preds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to a code file to classify")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    preds = classify_text(text, threshold=args.threshold)
    print(json.dumps({"predictions": preds}, indent=2))


if __name__ == "__main__":
    main()
