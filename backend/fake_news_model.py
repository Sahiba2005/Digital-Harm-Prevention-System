import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
import joblib

# Load datasets
fake = pd.read_csv("Fake.csv")
real = pd.read_csv("True.csv")

fake["label"] = "FAKE"
real["label"] = "REAL"

data = pd.concat([fake, real])

# Combine title and text
data["content"] = data["title"] + " " + data["text"]

texts = data["content"]
labels = data["label"]

vectorizer = TfidfVectorizer(stop_words="english", max_df=0.7)

X = vectorizer.fit_transform(texts)

model = PassiveAggressiveClassifier(max_iter=50)
model.fit(X, labels)

joblib.dump(model, "fake_news_model.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")

print("Model trained successfully")