from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib

app = Flask(__name__)
CORS(app)

model = joblib.load("fake_news_model.pkl")
vectorizer = joblib.load("vectorizer.pkl")


@app.route("/predict", methods=["POST"])
def predict():

    data = request.get_json()

    text = data["news"]

    vector = vectorizer.transform([text])

    prediction = model.predict(vector)[0]

    score = abs(model.decision_function(vector)[0])

    confidence = min(round(score * 20), 95)

    return jsonify({
        "prediction": prediction,
        "confidence": confidence
    })


@app.route("/")
def home():
    return "DHPS AI Server Running"


if __name__ == "__main__":
    app.run(debug=True)