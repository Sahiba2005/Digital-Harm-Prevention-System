"""
DHPS Fake News Detection API
Loads trained model from model.json (no .pkl files).
POST /predict  { "news": "<text>" }  ->  { "prediction": "FAKE|REAL", "confidence": 0-100 }
"""

import re
import json
import math
import numpy as np
from flask import Flask, request, jsonify

try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

MODEL_FILE = "model.json"

app = Flask(__name__)
if HAS_CORS:
    CORS(app)
else:
    @app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        return response

# ---- LOAD MODEL ---------------------------------------------------------------
print(f"Loading model from {MODEL_FILE} ...")
with open(MODEL_FILE, "r", encoding="utf-8") as f:
    MODEL_DATA = json.load(f)

META       = MODEL_DATA["meta"]
VEC_DATA   = MODEL_DATA["vectorizer"]
MODEL_TYPE = MODEL_DATA["model"]["model_type"]

print(f"  Model      : {META['best_model']}")
print(f"  Accuracy   : {META['accuracy']*100:.2f}%")
print(f"  F1-Score   : {META['f1_score']*100:.2f}%")
print(f"  Vocab size : {META['vocab_size']:,}")

# ---- VECTORIZER ---------------------------------------------------------------
VOCAB      = VEC_DATA["vocabulary"]
IDF        = np.array(VEC_DATA["idf"])
STOP_WORDS = set(VEC_DATA["stop_words"]) if VEC_DATA["stop_words"] else set()
NGRAM_MIN, NGRAM_MAX = VEC_DATA["ngram_range"]
SUBLINEAR  = VEC_DATA["sublinear_tf"]

def clean(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def get_ngrams(tokens, n_min, n_max):
    grams = []
    for n in range(n_min, n_max + 1):
        for i in range(len(tokens) - n + 1):
            grams.append(" ".join(tokens[i: i + n]))
    return grams

def tfidf_transform(text):
    tokens = [t for t in clean(text).split() if t not in STOP_WORDS]
    ngrams = get_ngrams(tokens, NGRAM_MIN, NGRAM_MAX)
    tf_raw = {}
    for g in ngrams:
        if g in VOCAB:
            tf_raw[VOCAB[g]] = tf_raw.get(VOCAB[g], 0) + 1
    if not tf_raw:
        return np.zeros(len(IDF))
    vec = np.zeros(len(IDF))
    for idx, count in tf_raw.items():
        tf = (1 + math.log(count)) if SUBLINEAR else count
        vec[idx] = tf * IDF[idx]
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec

def score_to_confidence(raw_score, word_count):
    """
    Convert raw decision function score to a meaningful confidence percentage.
    - Uses tanh scaling so even small scores map to decent confidence
    - Boosts confidence for longer texts (more evidence)
    - Short texts (< 5 words) are capped at 80% max confidence
    """
    abs_score = abs(raw_score)

    # tanh gives a smooth 0-1 curve; scale factor 1.5 makes it rise faster
    base_conf = math.tanh(abs_score * 1.5)

    # Word count bonus: longer text = more signal = higher confidence ceiling
    if word_count >= 50:
        ceiling = 0.97
    elif word_count >= 20:
        ceiling = 0.92
    elif word_count >= 10:
        ceiling = 0.87
    elif word_count >= 5:
        ceiling = 0.82
    else:
        ceiling = 0.75   # very short text — cap at 75%

    # Floor at 55% so it never looks like a coin flip
    floor = 0.55

    confidence = floor + (ceiling - floor) * base_conf
    return int(round(confidence * 100))

# ---- MODEL INFERENCE ----------------------------------------------------------
CLASSES   = MODEL_DATA["model"]["classes"]
LABEL_MAP = META["labels"]

def predict(text):
    vec        = tfidf_transform(text)
    word_count = len(clean(text).split())

    if "Logistic" in MODEL_TYPE or "Passive" in MODEL_TYPE:
        coef      = np.array(MODEL_DATA["model"]["coef"])
        intercept = np.array(MODEL_DATA["model"]["intercept"])

        if coef.shape[0] == 1:
            # Binary classifier: positive score = REAL, negative = FAKE
            raw_score = float(vec @ coef[0] + intercept[0])
            pred_idx  = 1 if raw_score >= 0 else 0
            confidence = score_to_confidence(raw_score, word_count)
        else:
            scores    = coef @ vec + intercept
            pred_idx  = int(np.argmax(scores))
            raw_score = scores[pred_idx] - scores[1 - pred_idx]
            confidence = score_to_confidence(raw_score, word_count)

    elif "Naive" in MODEL_TYPE:
        flp = np.array(MODEL_DATA["model"]["feature_log_prob"])
        clp = np.array(MODEL_DATA["model"]["class_log_prior"])
        tokens = [t for t in clean(text).split() if t not in STOP_WORDS]
        ngrams = get_ngrams(tokens, NGRAM_MIN, NGRAM_MAX)
        count_vec = np.zeros(len(IDF))
        for g in ngrams:
            if g in VOCAB:
                count_vec[VOCAB[g]] += 1
        log_probs  = flp @ count_vec + clp
        pred_idx   = int(np.argmax(log_probs))
        raw_score  = log_probs[pred_idx] - log_probs[1 - pred_idx]
        confidence = score_to_confidence(raw_score, word_count)

    elif "Random" in MODEL_TYPE:
        trees   = MODEL_DATA["model"]["estimators"]
        n_class = len(CLASSES)
        votes   = np.zeros(n_class)
        for tree in trees:
            cl   = tree["children_left"]
            cr   = tree["children_right"]
            feat = tree["feature"]
            thr  = tree["threshold"]
            val  = tree["value"]
            node = 0
            while cl[node] != -1:
                f    = feat[node]
                node = cl[node] if vec[f] <= thr[node] else cr[node]
            node_val = np.array(val[node][0])
            votes[int(np.argmax(node_val))] += 1
        pred_idx   = int(np.argmax(votes))
        vote_ratio = votes[pred_idx] / len(trees)
        raw_score  = math.atanh(min(vote_ratio * 2 - 1, 0.9999))
        confidence = score_to_confidence(raw_score, word_count)

    else:
        raise ValueError(f"Unknown model type: {MODEL_TYPE}")

    label = LABEL_MAP[str(CLASSES[pred_idx])]
    return label, confidence

# ---- ROUTES ------------------------------------------------------------------
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict_route():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json(silent=True)
    if not data or "news" not in data:
        return jsonify({"error": "Missing 'news' field"}), 400
    text = str(data["news"]).strip()
    if not text:
        return jsonify({"error": "Empty text"}), 400
    label, confidence = predict(text)
    return jsonify({"prediction": label, "confidence": confidence})

@app.route("/")
def home():
    return jsonify({
        "status":   "running",
        "model":    META["best_model"],
        "accuracy": f"{META['accuracy']*100:.2f}%",
        "f1_score": f"{META['f1_score']*100:.2f}%",
    })

@app.route("/model-info")
def model_info():
    return jsonify(META)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
