# DHPS Fake News Detection — Backend

## Files needed in the backend/ folder
| File | Description |
|------|-------------|
| `train_model.py` | Train model, compare 4 algorithms, save best to `model.json` |
| `app.py` | Flask API — loads `model.json`, serves `/predict` |
| `DataSet_Misinfo_TRUE.csv` | Real news (from Kaggle dataset) |
| `DataSet_Misinfo_FAKE.csv` | Fake news (from Kaggle dataset) |
| `EXTRA_RussianPropagandaSubset.csv` | Optional extra fake data (auto-included if present) |

## Dataset
https://www.kaggle.com/datasets/stevenpeutz/misinformation-fake-news-text-dataset-79k

## Setup
```bash
pip3 install flask scikit-learn pandas numpy
```

## Step 1 — Train
```bash
cd backend
python3 train_model.py
```
Trains 4 models, picks best by F1, saves to `model.json`.

## Step 2 — Start API
```bash
python3 app.py
```
Runs at http://127.0.0.1:5000

## API
### POST /predict
```json
{ "news": "your headline or article text" }
```
Response:
```json
{ "prediction": "FAKE", "confidence": 87 }
```
### GET /model-info
Returns accuracy, F1, model name, vocab size.
