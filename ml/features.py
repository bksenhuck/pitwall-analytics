"""
features.py — Feature engineering for race outcome prediction.

Builds an ML-ready dataset from the raw race results DataFrame produced
by dataset.load_race_results().

Features produced
-----------------
driver_encoded          : label-encoded driver identifier
grid_position           : starting grid position
rolling_avg_finish      : rolling mean finish over last 5 races (per driver)
driver_avg_finish       : expanding mean finish position (per driver, lagged)
circuit_driver_avg      : expanding mean finish at this circuit (per driver, lagged)
circuit_encoded         : label-encoded circuit (location)
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


def build_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, LabelEncoder, LabelEncoder]:
    """
    Engineer features from raw race results.

    Parameters
    ----------
    df : raw DataFrame from dataset.load_race_results()

    Returns
    -------
    X            : feature DataFrame
    y            : target Series (finish position)
    le_driver    : fitted LabelEncoder for driver_number
    le_circuit   : fitted LabelEncoder for location
    """
    df = df.copy()
    df = df.dropna(subset=["position", "grid_position"])

    # Sort so rolling computations are chronological per driver
    df = df.sort_values(["driver_number", "season", "round_number"]).reset_index(
        drop=True
    )

    # Rolling average finish — last 5 races, lagged by 1 (no data leakage)
    df["rolling_avg_finish"] = df.groupby("driver_number")["position"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    )

    # Expanding (career) average — lagged by 1
    df["driver_avg_finish"] = (
        df.groupby("driver_number")["position"]
        .transform(lambda x: x.shift(1).expanding(min_periods=1).mean())
    )

    # Circuit-specific driver average — lagged by 1
    df["circuit_driver_avg"] = (
        df.groupby(["driver_number", "location"])["position"]
        .transform(lambda x: x.shift(1).expanding(min_periods=1).mean())
    )

    # Encode categoricals
    le_driver = LabelEncoder()
    le_circuit = LabelEncoder()
    df["driver_encoded"] = le_driver.fit_transform(df["driver_number"].astype(str))
    df["circuit_encoded"] = le_circuit.fit_transform(df["location"].astype(str))

    feature_cols = [
        "driver_encoded",
        "grid_position",
        "rolling_avg_finish",
        "driver_avg_finish",
        "circuit_driver_avg",
        "circuit_encoded",
    ]

    # Fill NaN introduced by lagged operations with column medians
    df[feature_cols] = df[feature_cols].fillna(df[feature_cols].median())

    X = df[feature_cols]
    y = df["position"]

    return X, y, le_driver, le_circuit


def build_prediction_input(
    drivers: list[str],
    grid_positions: list[int],
    location: str,
    historical_df: pd.DataFrame,
    le_driver: LabelEncoder,
    le_circuit: LabelEncoder,
) -> pd.DataFrame:
    """
    Build a feature row for each driver for an upcoming race.

    Parameters
    ----------
    drivers         : list of driver_number strings
    grid_positions  : corresponding grid positions
    location        : circuit location string
    historical_df   : full historical DataFrame (for rolling stats)
    le_driver       : fitted LabelEncoder (from training)
    le_circuit      : fitted LabelEncoder (from training)

    Returns
    -------
    DataFrame with the same feature columns as build_features()
    """
    rows = []
    for driver, grid in zip(drivers, grid_positions):
        driver_history = historical_df[historical_df["driver_number"] == driver]
        circuit_history = driver_history[driver_history["location"] == location]

        rolling_avg = (
            driver_history["position"].tail(5).mean()
            if not driver_history.empty
            else np.nan
        )
        driver_avg = (
            driver_history["position"].mean()
            if not driver_history.empty
            else np.nan
        )
        circuit_avg = (
            circuit_history["position"].mean()
            if not circuit_history.empty
            else driver_avg
        )

        # Encode with fallback for unseen labels
        try:
            driver_enc = le_driver.transform([str(driver)])[0]
        except ValueError:
            driver_enc = -1

        try:
            circuit_enc = le_circuit.transform([str(location)])[0]
        except ValueError:
            circuit_enc = -1

        rows.append({
            "driver_encoded": driver_enc,
            "grid_position": grid,
            "rolling_avg_finish": rolling_avg,
            "driver_avg_finish": driver_avg,
            "circuit_driver_avg": circuit_avg if not np.isnan(circuit_avg) else driver_avg,
            "circuit_encoded": circuit_enc,
        })

    result = pd.DataFrame(rows)
    result = result.fillna(result.median())
    return result
