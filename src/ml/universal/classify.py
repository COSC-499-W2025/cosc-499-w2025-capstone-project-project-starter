from datasets import load_dataset
import os, re, json, random
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import f1_score
import numpy as np
from itertools import islice

# config params
HF_TOKEN = os.environ.get("HF_TOKEN")  #make sure to accept dataset terms or this won't run
DATASET = "bigcode/the-stack-smol"
SPLIT = "train"
N_SAMPLES = 100_000
BATCH_SIZE = 32
SHUFFLE_BUFFER = 10_000  #streaming shuffle

# Streaming load
ds_stream = load_dataset(DATASET, split=SPLIT, streaming=True, token=HF_TOKEN)
ds_stream = ds_stream.shuffle(seed=0, buffer_size=SHUFFLE_BUFFER)
sample_iter = islice(ds_stream, N_SAMPLES)  # take first N after shuffle

# Skill definitons go here
# Good start for now
SKILLS = [
    "React", "Express", "Django", "Flask", "Spring", "Rails", "Laravel", "DotNet",
    "SQL-DML", "SQL-DDL", "REST", "Testing", "CI", "Containerization", "Concurrency",
    "CryptoSec", "DataWrangling", "Numerics", "ML-PyTorch", "ML-TF", "ML-Sklearn",
]

LFs = [
    ("React",       re.compile(r"\bfrom\s+['\"]react['\"]|\bReact\.")),
    ("Express",     re.compile(r"require\(['\"]express['\"]\)|from\s+['\"]express['\"]")),
    ("Django",      re.compile(r"\bimport\s+django\b|\bfrom\s+django\b")),
    ("Flask",       re.compile(r"\bfrom\s+flask\b|\bimport\s+flask\b")),
    ("Spring",      re.compile(r"\borg\.springframework\b")),
    ("Rails",       re.compile(r"\brequire\s+['\"]rails['\"]|\bActiveRecord\b")),
    ("Laravel",     re.compile(r"\bIlluminate\\|\buse\s+Laravel\\")),
    ("DotNet",      re.compile(r"\busing\s+System\.")),
    ("SQL-DML",     re.compile(r"\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b", re.I)),
    ("SQL-DDL",     re.compile(r"\bCREATE\s+TABLE\b|\bALTER\s+TABLE\b|\bDROP\s+TABLE\b", re.I)),
    ("REST",        re.compile(r"\b(GET|POST|PUT|DELETE)\s+\/[A-Za-z0-9_\-\/]+")),
    ("Testing",     re.compile(r"\bpytest\b|\bjunit\b|\bunittest\b|\bdescribe\(|\bit\(")),
    ("CI",          re.compile(r"\.github\/workflows|Jenkinsfile|\.gitlab-ci\.yml")),
    ("Containerization", re.compile(r"\bFROM\s+[\w\/:\-\.]+(\s+AS\s+\w+)?\b", re.I)),
    ("Concurrency", re.compile(r"\bstd::thread\b|\bsynchronized\b|\bjava\.util\.concurrent\b|\basync\b|\bawait\b")),
    ("CryptoSec",   re.compile(r"\bhashlib\b|\bjavax\.crypto\b|\bOpenSSL\b|\bcrypt\(")),
    ("DataWrangling", re.compile(r"\bpandas\b|\bDataFrame\b")),
    ("Numerics",    re.compile(r"\bnumpy\b|\bnumpy\.|np\.")),
    ("ML-PyTorch",  re.compile(r"\bimport\s+torch\b|\bfrom\s+torch\b")),
    ("ML-TF",       re.compile(r"\bimport\s+tensorflow\b|\bfrom\s+tensorflow\b|\bkeras\b")),
    ("ML-Sklearn",  re.compile(r"\bimport\s+sklearn\b|\bfrom\s+sklearn\b")),
]

def weak_labels(example):
    content = example.get("content") or ""
    content = content[:80_000]  # cap for regex work
    path = example.get("path") or ""
    skills = set()
    # path-based LFs
    if re.search(r"(^|/)(tests?|__tests__)/", path): skills.add("Testing")
    if re.search(r"(^|/)(migrations?|schema\.sql)$", path): skills.add("SQL-DDL")
    if "dockerfile" in path.lower(): skills.add("Containerization")
    if re.search(r"(^|/)\.github/workflows/", path) or "Jenkinsfile" in path: skills.add("CI")
    # content-based LFs
    for skill, pat in LFs:
        if pat.search(content):
            skills.add(skill)
    return list(skills)

# start encoder
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tok = AutoTokenizer.from_pretrained("microsoft/codebert-base")
enc = AutoModel.from_pretrained("microsoft/codebert-base").to(device)
enc.eval()
enc.requires_grad_(False)

def embed_texts(texts):
    # truncate early; keep imports and headers
    texts = [(t or "")[:2000] for t in texts]
    with torch.no_grad():
        toks = tok(texts, truncation=True, padding=True, max_length=256, return_tensors="pt")
        toks = {k: v.to(device) for k, v in toks.items()}
        out = enc(**toks)
        emb = out.last_hidden_state[:, 0, :].detach().cpu().numpy()
    return emb  # (B, H)

# embedding
mlb = MultiLabelBinarizer(classes=SKILLS)
mlb.fit([[]])  # initialize with fixed class order

X_rows = []
Y_rows = []

batch_texts = []
batch_labels = []

for ex in sample_iter:
    labels = weak_labels(ex)
    batch_labels.append(labels)
    batch_texts.append(ex.get("content") or "")

    if len(batch_texts) == BATCH_SIZE:
        emb = embed_texts(batch_texts)              # (B, H)
        Yb = mlb.transform(batch_labels)            # (B, |C|)
        X_rows.append(emb)
        Y_rows.append(Yb)
        batch_texts, batch_labels = [], []

# flush remainder
if batch_texts:
    emb = embed_texts(batch_texts)
    Yb = mlb.transform(batch_labels)
    X_rows.append(emb)
    Y_rows.append(Yb)

X = np.vstack(X_rows)
Y = np.vstack(Y_rows)

# filter to rows w at least 1 silver label
mask = Y.sum(axis=1) > 0
X_train, Y_train = X[mask], Y[mask]

# 1 vs rest classification
clf = LogisticRegression(
    penalty="l2", C=1.0, max_iter=200, solver="saga", n_jobs=-1
)
clf.fit(X_train, Y_train)

