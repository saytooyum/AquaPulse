import joblib
import pandas as pd
import math
from pathlib import Path


# Load model once
MODEL_FILE = Path(__file__).resolve().parent / "GEMStat_RandomForest_v2.pkl"
model = joblib.load(MODEL_FILE)


FEATURES = [
    "DO",
    "Temperature",
    "pH",
    "Nitrate",
    "Phosphorus"
]


# Screening thresholds from our existing project methodology.
# Verify these against the actual labeling code before deployment.
DO_MIN = 5.0
NITRATE_MAX = 1.0
PHOSPHORUS_MAX = 0.10


def analyze_indicators(do, temperature, ph, nitrate, phosphorus):
    """
    Screen water-quality measurements for potential stress indicators.

    These rules are a separate screening layer. They do not change
    the Random Forest's prediction.
    """

    indicators = []

    if do < DO_MIN:
        indicators.append({
            "parameter": "Dissolved Oxygen",
            "value": do,
            "status": "Potential stress indicator",
            "message": (
                f"Dissolved Oxygen is below {DO_MIN} mg/L."
            )
        })

    if nitrate >= NITRATE_MAX:
        indicators.append({
            "parameter": "Nitrate",
            "value": nitrate,
            "status": "Potential stress indicator",
            "message": (
                f"Nitrate is at or above {NITRATE_MAX} mg/L."
            )
        })

    if phosphorus >= PHOSPHORUS_MAX:
        indicators.append({
            "parameter": "Phosphorus",
            "value": phosphorus,
            "status": "Potential stress indicator",
            "message": (
                f"Phosphorus is at or above {PHOSPHORUS_MAX} mg/L."
            )
        })

    # Temperature and pH are reported but not threshold-classified
    # until their exact project-specific rules are verified.
    return {
        "screened_indicators": indicators,
        "not_assessed": [
            {
                "parameter": "Temperature",
                "value": temperature,
                "reason": "A verified project-specific threshold is not configured."
            },
            {
                "parameter": "pH",
                "value": ph,
                "reason": "A verified project-specific range is not configured."
            }
        ]
    }


def predict_water_quality(
    do,
    temperature,
    ph,
    nitrate,
    phosphorus
):
    # Validate input measurements
    values = {
        "DO": do,
        "Temperature": temperature,
        "pH": ph,
        "Nitrate": nitrate,
        "Phosphorus": phosphorus
    }

    for name, value in values.items():
        if isinstance(value, bool):
            raise ValueError(f"{name} must be a numeric measurement.")

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a numeric measurement.")

        if not math.isfinite(numeric_value):
            raise ValueError(f"{name} must be a finite number.")

        values[name] = numeric_value

    if values["DO"] < 0:
        raise ValueError("DO cannot be negative.")

    if values["Nitrate"] < 0:
        raise ValueError("Nitrate cannot be negative.")

    if values["Phosphorus"] < 0:
        raise ValueError("Phosphorus cannot be negative.")

    if not 0 <= values["pH"] <= 14:
        raise ValueError("pH must be between 0 and 14.")

    # Prepare input for the trained model
    input_data = pd.DataFrame(
        [[values[feature] for feature in FEATURES]],
        columns=FEATURES
    )

    # Random Forest prediction
    prediction = model.predict(input_data)[0]

    probabilities = model.predict_proba(input_data)[0]
    classes = list(model.classes_)

    if 0 not in classes or 1 not in classes:
        raise RuntimeError(
            "The model must contain classes 0 (At-Risk) and 1 (Healthy)."
        )

    at_risk_probability = float(probabilities[classes.index(0)])
    healthy_probability = float(probabilities[classes.index(1)])

    result = "At-Risk" if prediction == 0 else "Healthy"

    # Independent scientific indicator screening
    analysis = analyze_indicators(
        do=values["DO"],
        temperature=values["Temperature"],
        ph=values["pH"],
        nitrate=values["Nitrate"],
        phosphorus=values["Phosphorus"]
    )

    return {
        "prediction": result,
        "at_risk_probability": round(at_risk_probability, 4),
        "healthy_probability": round(healthy_probability, 4),
        "indicator_analysis": analysis
    }