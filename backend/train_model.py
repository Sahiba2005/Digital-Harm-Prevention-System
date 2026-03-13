"""
DHPS Fake News Detection - Model Trainer
==========================================
Dataset: https://www.kaggle.com/datasets/stevenpeutz/misinformation-fake-news-text-dataset-79k
Files needed in same folder:
  - DataSet_Misinfo_TRUE.csv
  - DataSet_Misinfo_FAKE.csv
  - EXTRA_RussianPropagandaSubset.csv  (optional, auto-detected)
"""

import os
import re
import json
import time
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score,
    recall_score, classification_report, confusion_matrix
)
from sklearn.linear_model import LogisticRegression, PassiveAggressiveClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB

# ── CONFIG ─────────────────────────────────────────────────────────────────────
TRUE_CSV  = "DataSet_Misinfo_TRUE.csv"
FAKE_CSV  = "DataSet_Misinfo_FAKE.csv"
EXTRA_CSV = "EXTRA_RussianPropagandaSubset.csv"   # included if present
MODEL_OUT = "model.json"
TEST_SIZE = 0.20
RANDOM_STATE = 42

# ── HELPERS ────────────────────────────────────────────────────────────────────
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def print_section(title):
    print("\n" + "═" * 60)
    print(f"  {title}")
    print("═" * 60)

def load_csv_flexible(path, label):
    """Load a CSV regardless of column names, return df with 'content' and 'label'."""
    df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8", low_memory=False)
    print(f"  Loaded {path}  →  {len(df):,} rows  |  columns: {list(df.columns)}")

    # Find best text column
    text_col  = None
    title_col = None
    for col in df.columns:
        cl = col.lower()
        if cl in ("text", "body", "content", "article"):
            text_col = col
        if cl in ("title", "headline", "head"):
            title_col = col

    if text_col is None:
        # fallback: use the longest string column
        str_cols = df.select_dtypes(include="object").columns.tolist()
        if not str_cols:
            raise ValueError(f"No usable text column found in {path}")
        text_col = max(str_cols, key=lambda c: df[c].fillna("").str.len().mean())
        print(f"  ⚠  No standard text column — using '{text_col}' as fallback")

    if title_col:
        df["content"] = df[title_col].fillna("") + " " + df[text_col].fillna("")
    else:
        df["content"] = df[text_col].fillna("")

    df["label"] = label
    return df[["content", "label"]]

# ── 1. LOAD DATA ───────────────────────────────────────────────────────────────
print_section("1. LOADING DATASET")

for f in [TRUE_CSV, FAKE_CSV]:
    if not os.path.exists(f):
        raise FileNotFoundError(
            f"Missing: {f}\n"
            f"Place DataSet_Misinfo_TRUE.csv and DataSet_Misinfo_FAKE.csv "
            f"in the same folder as this script."
        )

real_df  = load_csv_flexible(TRUE_CSV,  label=1)   # 1 = REAL
fake_df  = load_csv_flexible(FAKE_CSV,  label=0)   # 0 = FAKE

frames = [real_df, fake_df]

# Include Russian propaganda subset as additional FAKE data if present
if os.path.exists(EXTRA_CSV):
    extra_df = load_csv_flexible(EXTRA_CSV, label=0)
    frames.append(extra_df)
    print(f"  ✔  Extra propaganda subset included ({len(extra_df):,} rows)")
else:
    print(f"  –  {EXTRA_CSV} not found, skipping")

data = pd.concat(frames, ignore_index=True)
data = data.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

print(f"\n  REAL articles : {(data['label']==1).sum():,}")
print(f"  FAKE articles : {(data['label']==0).sum():,}")
print(f"  Total         : {len(data):,}")

# ── 2. PREPROCESS ──────────────────────────────────────────────────────────────
print_section("2. PREPROCESSING")

data["content"] = data["content"].apply(clean_text)
data = data[data["content"].str.strip().str.len() > 10].reset_index(drop=True)

print(f"  Samples after cleaning : {len(data):,}")

X = data["content"].values
y = data["label"].values

# ── 3. VECTORIZE ───────────────────────────────────────────────────────────────
print_section("3. TF-IDF VECTORIZATION")

vectorizer = TfidfVectorizer(
    stop_words="english",
    max_df=0.85,
    min_df=3,
    max_features=80000,
    ngram_range=(1, 2),
    sublinear_tf=True
)

X_vec = vectorizer.fit_transform(X)
print(f"  Vocabulary size : {len(vectorizer.vocabulary_):,}")
print(f"  Feature matrix  : {X_vec.shape}")

X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
)
print(f"  Train : {X_train.shape[0]:,}  |  Test : {X_test.shape[0]:,}")

# ── 4. TRAIN & EVALUATE ────────────────────────────────────────────────────────
print_section("4. TRAINING CANDIDATE MODELS")

candidates = {
    "Logistic Regression": LogisticRegression(
        max_iter=1000, C=5.0, solver="lbfgs", random_state=RANDOM_STATE
    ),
    "Passive Aggressive": PassiveAggressiveClassifier(
        max_iter=100, C=0.5, random_state=RANDOM_STATE
    ),
    "Naive Bayes": MultinomialNB(alpha=0.1),
    "Random Forest": RandomForestClassifier(
        n_estimators=200, max_depth=30, n_jobs=-1, random_state=RANDOM_STATE
    ),
}

results = {}

for name, clf in candidates.items():
    print(f"\n  ▸ {name}")
    t0 = time.time()
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc  = accuracy_score(y_test, y_pred)
    f1   = f1_score(y_test, y_pred, average="weighted")
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec  = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    elapsed = time.time() - t0
    results[name] = {"clf": clf, "acc": acc, "f1": f1, "prec": prec, "rec": rec, "time": elapsed}
    print(f"    Accuracy  : {acc*100:.2f}%")
    print(f"    F1-Score  : {f1*100:.2f}%")
    print(f"    Precision : {prec*100:.2f}%")
    print(f"    Recall    : {rec*100:.2f}%")
    print(f"    Time      : {elapsed:.1f}s")

# ── 5. SELECT BEST ─────────────────────────────────────────────────────────────
print_section("5. MODEL COMPARISON")

print(f"\n  {'Model':<28} {'Accuracy':>10} {'F1':>10} {'Precision':>10} {'Recall':>10}")
print(f"  {'-'*68}")
for name, r in results.items():
    print(f"  {name:<28} {r['acc']*100:>9.2f}% {r['f1']*100:>9.2f}% {r['prec']*100:>9.2f}% {r['rec']*100:>9.2f}%")

best_name = max(results, key=lambda k: results[k]["f1"])
best      = results[best_name]
best_clf  = best["clf"]

print(f"\n  ✔  BEST MODEL : {best_name}")
print(f"     F1-Score   : {best['f1']*100:.2f}%")
print(f"     Accuracy   : {best['acc']*100:.2f}%")

y_pred = best_clf.predict(X_test)
print(f"\n  Classification Report ({best_name})")
print(classification_report(y_test, y_pred, target_names=["FAKE", "REAL"], digits=4))

cm = confusion_matrix(y_test, y_pred)
print(f"  Confusion Matrix")
print(f"                Pred FAKE  Pred REAL")
print(f"  Actual FAKE   {cm[0,0]:>9,}  {cm[0,1]:>9,}")
print(f"  Actual REAL   {cm[1,0]:>9,}  {cm[1,1]:>9,}")

# ── 6. SERIALIZE & SAVE ────────────────────────────────────────────────────────
print_section("6. SAVING MODEL TO JSON")

def serialize_model(clf, model_name):
    d = {"model_type": model_name}
    if "Logistic" in model_name or "Passive" in model_name:
        d["coef"]      = clf.coef_.tolist()
        d["intercept"] = clf.intercept_.tolist()
        d["classes"]   = clf.classes_.tolist()
    elif "Naive" in model_name:
        d["feature_log_prob"] = clf.feature_log_prob_.tolist()
        d["class_log_prior"]  = clf.class_log_prior_.tolist()
        d["classes"]          = clf.classes_.tolist()
    elif "Random" in model_name:
        trees = []
        for est in clf.estimators_:
            t = est.tree_
            trees.append({
                "children_left":  t.children_left.tolist(),
                "children_right": t.children_right.tolist(),
                "feature":        t.feature.tolist(),
                "threshold":      t.threshold.tolist(),
                "value":          t.value.tolist(),
                "n_node_samples": t.n_node_samples.tolist(),
            })
        d["estimators"] = trees
        d["classes"]    = clf.classes_.tolist()
        d["n_features"] = clf.n_features_in_
    return d

def serialize_vectorizer(vec):
    # Compatible with all sklearn versions
    sw = vec.stop_words
    if isinstance(sw, str):
        sw = []   # "english" string — the actual set isn't stored; app.py handles it
    elif isinstance(sw, (set, frozenset)):
        sw = list(sw)
    else:
        sw = []
    return {
        "vocabulary":   {k: int(v) for k, v in vec.vocabulary_.items()},
        "idf":          vec.idf_.tolist(),
        "stop_words":   sw,
        "max_df":       vec.max_df,
        "min_df":       vec.min_df,
        "max_features": vec.max_features,
        "ngram_range":  list(vec.ngram_range),
        "sublinear_tf": vec.sublinear_tf,
    }

output = {
    "meta": {
        "best_model":    best_name,
        "accuracy":      round(best["acc"], 6),
        "f1_score":      round(best["f1"], 6),
        "precision":     round(best["prec"], 6),
        "recall":        round(best["rec"], 6),
        "train_samples": int(X_train.shape[0]),
        "test_samples":  int(X_test.shape[0]),
        "vocab_size":    len(vectorizer.vocabulary_),
        "labels":        {"0": "FAKE", "1": "REAL"},
    },
    "vectorizer": serialize_vectorizer(vectorizer),
    "model":      serialize_model(best_clf, best_name),
}

print(f"  Serializing to {MODEL_OUT} ...")
with open(MODEL_OUT, "w", encoding="utf-8") as f:
    json.dump(output, f, separators=(",", ":"))

size_mb = os.path.getsize(MODEL_OUT) / (1024 * 1024)
print(f"  ✔  Saved → {MODEL_OUT}  ({size_mb:.1f} MB)")
print(f"\n  Best model : {best_name}")
print(f"  F1-Score   : {best['f1']*100:.2f}%")
print(f"  Accuracy   : {best['acc']*100:.2f}%")
print(f"\n  Training complete. Run:  python3 app.py")
