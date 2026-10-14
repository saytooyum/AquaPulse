"""Traditional Flask server for the OneAquaHealth web interface.

Run with: py server.py
Then open: http://127.0.0.1:5000
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

from predict_water_quality import FEATURES, model, predict_water_quality


ROOT = Path(__file__).parent
DATA = pd.read_csv(ROOT / "GEMStat_RF_Final.csv")
HISTORY_PATH = ROOT / "GEMStat_Predictions.csv"
TEST_PREDICTIONS_PATH = ROOT / "GEMStat_Test_Predictions_v2.csv"

app = Flask(__name__)


@app.get("/")
def home():
    """Serve the user interface."""
    overview = {
        "stations": int(DATA["GEMS Station Number"].nunique()),
        "samples": int(len(DATA)),
        "healthy_share": round(float(DATA["Label"].mean() * 100)),
        "checks": int(len(pd.read_csv(HISTORY_PATH))) if HISTORY_PATH.exists() else 0,
    }
    return render_template("index.html", overview=overview)


@app.post("/api/predict")
def predict():
    """Receive measurements from JavaScript and return a model prediction."""
    try:
        values = {name: float(request.json[name]) for name in FEATURES}
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Please enter valid numeric values for all five measurements."), 400

    try:
        output = predict_water_quality(
            values["DO"],
            values["Temperature"],
            values["pH"],
            values["Nitrate"],
            values["Phosphorus"],
    )
    except ValueError as error:
        return jsonify(error=str(error)), 400
    predicted_label = 1 if output["prediction"] == "Healthy" else 0
    result = {
        "prediction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **values,
        "predicted_label": predicted_label,
        "status": output["prediction"],
        "at_risk_probability": round(
        output["at_risk_probability"] * 100, 1
        ),
        "healthy_probability": round(
        output["healthy_probability"] * 100, 1
        ),
        "indicator_analysis": output["indicator_analysis"],
    }

    record = pd.DataFrame([{
        "Prediction_Time": result["prediction_time"], **values,
        "Predicted_Label": predicted_label,
        "Predicted_Status": result["status"],
        "At_Risk_Probability": output["at_risk_probability"],
        "Healthy_Probability": output["healthy_probability"],
    }])
    record.to_csv(HISTORY_PATH, mode="a", header=not HISTORY_PATH.exists(), index=False)

    return jsonify(result)


@app.get("/api/insights")
def insights():
    """Supply dashboard data to the browser."""
    importance = dict(zip(FEATURES, [round(float(x), 3) for x in model.feature_importances_]))
    distribution = DATA["Label"].map({0: "At-Risk", 1: "Healthy"}).value_counts().to_dict()
    model_check = None
    if TEST_PREDICTIONS_PATH.exists():
        table = pd.read_csv(TEST_PREDICTIONS_PATH)
        matches = table["Label"] == table["Predicted_Label"]
        model_check = {
            "samples": int(len(table)),
            "accuracy": round(float(matches.mean() * 100), 1),
        }
    return jsonify(
        feature_importance=importance,
        health_distribution=distribution,
        model_check=model_check,
    )


if __name__ == "__main__":
    app.run(debug=True)
