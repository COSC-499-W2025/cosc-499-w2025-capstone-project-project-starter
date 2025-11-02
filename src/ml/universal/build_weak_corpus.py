import os, re, json, random, math
from itertools import islice
from datasets import load_dataset

HF_TOKEN = os.environ.get("HF_TOKEN")
DATASET = "bigcode/the-stack-smol"
SPLIT = "train"
N_SAMPLES = 100_000
SHUFFLE_BUFFER = 10_000
SHARD_SIZE = 10_000
OUT_DIR = "data/shards"
os.makedirs(OUT_DIR, exist_ok=True)

SKILLS = [
    "React","Express","Django","Flask","Spring","Rails","Laravel","DotNet",
    "SQL-DML","SQL-DDL","REST","Testing","CI","Containerization","Concurrency",
    "CryptoSec","DataWrangling","Numerics","ML-PyTorch","ML-TF","ML-Sklearn",
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
    content = (example.get("content") or "")[:80_000]
    path = example.get("path") or ""
    skills = set()
    if re.search(r"(^|/)(tests?|__tests__)/", path): skills.add("Testing")
    if re.search(r"(^|/)(migrations?|schema\.sql)$", path): skills.add("SQL-DDL")
    if "dockerfile" in path.lower(): skills.add("Containerization")
    if re.search(r"(^|/)\.github/workflows/", path) or "Jenkinsfile" in path: skills.add("CI")
    for skill, pat in LFs:
        if pat.search(content):
            skills.add(skill)
    return sorted(list(skills))

def main():
    ds = load_dataset(DATASET, split=SPLIT, streaming=True, token=HF_TOKEN)
    ds = ds.shuffle(seed=0, buffer_size=SHUFFLE_BUFFER)
    it = islice(ds, N_SAMPLES)

    shard_idx, count = 1, 0
    f = open(os.path.join(OUT_DIR, f"weaklabels-{shard_idx:05d}.jsonl"), "w", encoding="utf-8")
    for ex in it:
        item = {
            "path": ex.get("path"),
            "repo_name": ex.get("repo_name"),
            "ext": ex.get("ext"),
            "size": ex.get("size"),
            "content": ex.get("content"),
            "labels": weak_labels(ex),
        }
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
        count += 1
        if count % SHARD_SIZE == 0:
            f.close()
            shard_idx += 1
            f = open(os.path.join(OUT_DIR, f"weaklabels-{shard_idx:05d}.jsonl"), "w", encoding="utf-8")
    f.close()

    # Persist metadata needed later
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/skills.json", "w") as g:
        json.dump(SKILLS, g)
    with open("artifacts/regex_lfs.json", "w") as g:
        json.dump({name: pat.pattern for name, pat in LFs}, g)

if __name__ == "__main__":
    main()
