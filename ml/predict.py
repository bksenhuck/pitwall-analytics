"""
predict.py — Load trained model and generate predictions for a race.

Raises FileNotFoundError if the model has not been trained yet.
Call `python -m ml.train` first.
"""
import os
import joblib
import numpy as np
import pandas as pd

from ml.dataset import load_race_results
from ml.features import build_prediction_input

MODEL_PATH = os.path.join("models", "finish_position_model.pkl")
ENCODERS_PATH = os.path.join("models", "encoders.pkl")


def _load_artifacts():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found at '{MODEL_PATH}'. Run `python -m ml.train` first."
        )
    model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODERS_PATH)
    return model, encoders["le_driver"], encoders["le_circuit"]


def generate_predictions(
    season: int | None = None,
    event_name: str | None = None,
    location: str | None = None,
) -> pd.DataFrame:
    """
    Generate predicted finishing positions for a given race.

    Pass either `event_name` (as returned by the frontend dropdown) or
    `location` (city name stored in the ML dataset). If neither is given,
    the most recent race in the database is used.

    Returns a DataFrame with columns:
        driver_number, driver_code, predicted_finish, podium_probability
    """
    model, le_driver, le_circuit = _load_artifacts()

    historical_df = load_race_results()
    if historical_df.empty:
        return pd.DataFrame()

    # Resolve the target race
    if season is None or (event_name is None and location is None):
        latest = (
            historical_df
            .sort_values(["season", "round_number"])
            .drop_duplicates(subset=["season", "round_number"], keep="last")
            .iloc[-1]
        )
        season = int(latest["season"])
        location = str(latest["location"])
        event_name = None

    # Filter – prefer event_name, fall back to location
    mask = historical_df["season"] == season
    if event_name is not None:
        race_df = historical_df[mask & (historical_df["event_name"] == event_name)]
        if race_df.empty:
            # try matching location as well in case event_name == location
            race_df = historical_df[mask & (historical_df["location"] == event_name)]
    else:
        race_df = historical_df[mask & (historical_df["location"] == location)]

    if race_df.empty:
        return pd.DataFrame()

    # Resolve location for circuit encoding
    location = str(race_df["location"].iloc[0])

    drivers = race_df["driver_number"].tolist()
    grids = race_df["grid_position"].fillna(20).astype(int).tolist()

    # Build driver_code lookup (number → 3-letter code)
    code_map = {}
    if "driver_code" in race_df.columns:
        code_map = dict(zip(
            race_df["driver_number"].astype(str),
            race_df["driver_code"].fillna(""),
        ))

    X = build_prediction_input(
        drivers=drivers,
        grid_positions=grids,
        location=location,
        historical_df=historical_df,
        le_driver=le_driver,
        le_circuit=le_circuit,
    )

    predicted = model.predict(X.values)

    # Estimate podium probability: fraction of trees predicting ≤ 3
    tree_preds = np.array([tree.predict(X.values) for tree in model.estimators_])
    podium_prob = (tree_preds <= 3).mean(axis=0)

    # Build real position lookup
    pos_map = {}
    if "position" in race_df.columns:
        pos_map = dict(zip(
            race_df["driver_number"].astype(str),
            pd.to_numeric(race_df["position"], errors="coerce"),
        ))

    result = pd.DataFrame({
        "driver_number": [str(d) for d in drivers],
        "driver_code": [code_map.get(str(d), str(d)) for d in drivers],
        "real_position": [pos_map.get(str(d), np.nan) for d in drivers],
        "predicted_finish": predicted,
        "podium_probability": podium_prob,
    })
    result = result.sort_values("real_position").reset_index(drop=True)
    return result
