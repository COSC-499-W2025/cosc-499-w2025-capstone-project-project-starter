import os, json, glob, numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.multiclass import OneVsRestClassifier
import joblib

EMB_GLOB = "data/embeds/embed-*.npz"
ARTI_DIR = "artifacts"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

def load_embeds():
    Xs, Ys = [], []
    for path in sorted(glob.glob(EMB_GLOB)):
        npz = np.load(path, allow_pickle=True)
        X = npz["X"]
        y_idx = npz["y"].tolist()  # list[list[int]]
        Xs.append(X)
        Ys.extend(y_idx)
    X = np.vstack(Xs)
    return X, Ys

def main():
    with open(os.path.join(ARTI_DIR, "skills.json")) as f:
        skills = json.load(f)

    X, y_idx = load_embeds()
    mlb = MultiLabelBinarizer(classes=skills)
    Y = mlb.fit_transform([[skills[i] for i in indices] for indices in y_idx])

    mask = Y.sum(axis=1) > 0
    X_train, Y_train = X[mask], Y[mask]

    clf = OneVsRestClassifier(
        LogisticRegression(penalty="l2", C=1.0, max_iter=200, solver="saga", n_jobs=-1)
    )
    clf.fit(X_train, Y_train)

    joblib.dump(clf, os.path.join(MODEL_DIR, "ovr_logreg.joblib"))
    with open(os.path.join(ARTI_DIR, "label_binarizer.json"), "w") as f:
        json.dump({"classes": mlb.classes_.tolist()}, f)

    print("Saved:", os.path.join(MODEL_DIR, "ovr_logreg.joblib"))

if __name__ == "__main__":
    main()
