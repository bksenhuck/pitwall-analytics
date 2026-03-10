"""
train.py — Train the finish-position prediction model and save it.

Usage
-----
    python -m ml.train

If the model file already exists it will be retrained and overwritten.
Prints MAE and RMSE on a held-out validation split.
"""
import os
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

from ml.dataset import load_race_results
from ml.features import build_features
from ml.models import create_model

MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "finish_position_model.pkl")
ENCODERS_PATH = os.path.join(MODEL_DIR, "encoders.pkl")


def train():
    print("Loading race results from database...")
    df = load_race_results()

    if df.empty:
        print("No data found. Make sure the season databases exist in data/.")
        return

    print(f"  {len(df)} race result rows loaded from {df['season'].nunique()} season(s).")

    print("Engineering features...")
    X, y, le_driver, le_circuit = build_features(df)
    print(f"  Feature matrix: {X.shape[0]} rows × {X.shape[1]} features")

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    print("Training RandomForestRegressor...")
    model = create_model()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_val)
    mae = mean_absolute_error(y_val, y_pred)
    rmse = root_mean_squared_error(y_val, y_pred)
    print(f"\nValidation metrics")
    print(f"  MAE  : {mae:.3f} positions")
    print(f"  RMSE : {rmse:.3f} positions")

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump({"le_driver": le_driver, "le_circuit": le_circuit}, ENCODERS_PATH)
    print(f"\nModel saved  → {MODEL_PATH}")
    print(f"Encoders saved → {ENCODERS_PATH}")


if __name__ == "__main__":
    train()
